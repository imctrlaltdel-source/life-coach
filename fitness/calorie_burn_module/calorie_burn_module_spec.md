# Calorie-Burn Progression Module — integration spec for the existing life-coach system

This is a module to merge into the plan you already have for this user, not a
replacement for it. It covers one specific track: a progressive, injury-safe
calorie-burn program using running, walking, and bodyweight calisthenics, no
equipment, alternate-day cadence, targeting ~3x baseline kcal/min output by
~6 months (90 sessions). Realistic-target note: 3x is achievable; the user's
first ask (23x/day) was not, and was rejected on physiological grounds before
this module was built — do not let a future request push the target back up
without re-deriving it from actual physiology.

Two files ship with this spec: `schema.sql` (run once) and `sessions_seed.json`
(seed data — insert `sessions_plan` rows and the single `plan_config` row on
first load).

## A. Merge rules
- Do not duplicate or conflict with workouts already scheduled elsewhere in
  the existing plan. If the existing plan already has something in a given
  slot, this module's next session shifts to the next open alternate-day slot
  — progression is tracked by `session_index`, not calendar date, specifically
  so it tolerates being pushed around by the rest of the plan.
- This module owns: warmup/main-set/cooldown prescription, HR cap, kcal/min
  target, and progression logic for this specific track. It does not own diet,
  sleep, or any other program the existing plan already manages — surface data
  to those tracks (e.g. calories burned) but don't let this module overwrite
  their logic.

## B. Non-negotiable quality bar
Every time this module is invoked, you must actually query the DB and compute,
not describe generically. Concretely, on every relevant turn:
1. Read `cb_plan_config.current_session_index` and the corresponding row in
   `cb_sessions_plan` — that is the session to prescribe, not whatever seems
   plausible.
2. If workout data was just supplied, insert it into `cb_workout_logs` in full
   (see Section C) before computing anything else.
3. Recompute `baseline_kcal_per_min`, current multiplier, and projected target
   date (Section E) from the actual rows in the DB — show the numbers, don't
   assert a vibe ("you're making great progress" without a number attached is
   not an acceptable response from this module).
4. Never silently skip the gating rule (Section D) to make a plan look more
   impressive — an unearned progression is exactly the injury path this
   module exists to prevent.

## C. Persistence (every input, no exceptions)
- On first load: execute `schema.sql`, then insert `plan_config` and all 90
  `sessions_plan` rows from `sessions_seed.json`.
- Every time the user supplies watch data for a workout (HR, calories,
  duration, RPE, sleep, resting HR, or anything else), insert one row into
  `cb_workout_logs`, storing the *entire raw payload* verbatim in
  `raw_watch_payload` in addition to the parsed columns — never discard fields
  you don't currently use, since future recomputation may need them.
- After every write to any `cb_*` table, if you have GitHub write access,
  commit a JSON snapshot of the four tables to a path such as
  `fitness/calorie_burn_module/state_<UTC-timestamp>.json` in the user's repo,
  as a durable, versioned backup independent of the DB. This is a mirror, not
  a replacement for the DB as source of truth — always read from the DB.

## D. Alternate-day cadence + travel/disruption readjustment
Target cadence is training every other calendar day (~3-4 sessions/week).
Progression is indexed by `session_index` (position in the 90-session arc),
never by calendar day — this is what makes it robust to travel.

On each new logged session, compute `gap_days` = days since
`last_completed_date`. Apply:

| gap_days | action |
|---|---|
| 0-3 (normal) | Prescribe next `session_index` as-is. |
| 4-7 | Prescribe next `session_index`, but cap it at the prescription from 2 sessions earlier (mild step-back) rather than the seed value. |
| 8-14 | Step back one full block (5 sessions) in progression level before resuming forward. |
| >14 | Treat as detraining: resume at 60% of the current block's run/round numbers (recompute from the formulas in `gen_plan_v2.py` logic, block-scaled by 0.6), ramping back to full current-block prescription over the next 3 sessions. Log this as a `cb_disruption_events` row with `reason='travel'` (or ask the user which). |

Never resume a >7 day gap at full previously-earned intensity — that's the
single highest-risk moment in this whole program for both the knees and the
heart, specifically because motivation to "make up for lost time" is highest
exactly when tolerance is lowest.

## E. Post-party makeup session
Trigger: user reports a day of heavy eating/drinking and wants to compensate.
This is a one-off metabolic evening-out, not a punishment loop — do not
suggest doing this after every normal indulgence; if the user starts asking
for this more than ~1x every couple of weeks, flag it to them rather than
just complying.

Compute:
```
trailing_avg_kcal = AVG(calories_burned) over the last 7 rows in cb_workout_logs
target_makeup_kcal = 3 * trailing_avg_kcal
```
Do **not** hit this target by raising the HR cap or intensity above what the
current block already prescribes — 3x-ing intensity in one session is an
injury and cardiac-risk shortcut, not a fitness gain. Instead, hit it by
extending duration, dominated by low-impact steady walking:
```
remaining_kcal = target_makeup_kcal - normal_session_kcal (that slot's target)
walk_kcal_per_min = derive from the user's own logged walk-heavy sessions
                    (fallback: 5 kcal/min if none logged yet)
extra_walk_minutes = remaining_kcal / walk_kcal_per_min
```
Cap `extra_walk_minutes` at 90; if the computed value exceeds that, split it
across two bouts the same day (e.g. one after the normal session, one later)
rather than one continuous 2+ hour session. Log the event in
`cb_party_events`, and update `achieved_kcal` once the actual data comes back
in `cb_workout_logs`.

## F. Live-data adaptive progression + ETA projection
On every new `cb_workout_logs` row:
1. If `baseline_kcal_per_min` in `cb_plan_config` is still null, set it once
   3 sessions are logged: `AVG(calories_burned / duration_min)` over the
   first 3 rows.
2. `current_multiplier = trailing_7_session_avg(calories_burned/duration_min) / baseline_kcal_per_min`.
3. Gating check before prescribing the next session: if
   `resting_hr_that_morning` is >7bpm above the trailing 7-day average, OR
   `sleep_score` is in the bottom quartile of the last 14 entries, OR
   `rpe_1_to_10` was ≥8 while `avg_hr` was below the session's HR cap (a sign
   of accumulating fatigue outrunning cardiac output) — do not advance
   `session_index`'s underlying block progression; mark the next occurrence
   of that slot as `status='repeated'` and reuse the prior session's
   prescription instead of the seed's next-step-up value.
4. ETA projection ("when do I hit 3x"):
   ```
   multiplier_now = current_multiplier (step 2)
   multiplier_10_sessions_ago = same calc using the 7-session window ending 10 sessions earlier
   per_session_growth = (multiplier_now - multiplier_10_sessions_ago) / 10
   sessions_remaining = (target_multiplier - multiplier_now) / per_session_growth   [if per_session_growth <= 0, report "not currently trending toward target" rather than a fake date]
   avg_days_between_sessions = AVG(date diff) over the trailing 10 logged sessions
   eta_date = last_completed_date + sessions_remaining * avg_days_between_sessions
   ```
   Store `eta_date` in `cb_plan_config.projected_target_date` and report it
   plainly whenever asked ("at your current rate, ~X sessions / ~Y weeks
   away"), including the caveat that it's a linear extrapolation.

## G. Files
- `schema.sql` — run once against the existing DB (tables prefixed `cb_`).
- `sessions_seed.json` — `plan_config` singleton + all 90 `sessions_plan`
  rows, generated from the block-based formulas (run/walk seconds, rounds,
  calisthenics reps, deload blocks at 4/8/12/16, Combined-circuit introduced
  at block 6). `sessions_seed.csv` is the same data for human review.

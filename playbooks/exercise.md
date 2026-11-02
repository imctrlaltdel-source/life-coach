# Exercise playbook — "what should I do at the gym?"

> Moved out of CLAUDE.md on 2026-11-02 so the always-loaded file stays short. Text is the original, with PJ's decisions of 2026-11-02 applied (height 165 cm, BMR 1,625, week Sunday to Saturday, protein 75 g/day, dinner carbs up to 12 g, Termux retired). Read this only when the topic comes up.

### Dynamic Exercise Recommendation — MANDATORY PROCESS

**EVERY TIME PJ ASKS WHAT TO DO AT GYM / FOR EXERCISE, run ALL 7 steps below before recommending anything. No shortcuts.**

---

**STEP 0 — run `date` first.** Know the exact day and time before anything else.

**STEP 1 — Query DB for last 7 days.**
Run `python3 scripts/coach_ctx.py --days 7` — extracts from `events` table:
- Which PPL session was done each day (Push A, Pull A, Legs, Push B, Pull B)
- Which muscle groups were actually hit (not just planned — what was in the screenshot)
- Any sessions skipped or missed
- Any injuries, soreness, or fatigue mentioned
- What cardio was done (run distance, HR, swim)
- Recovery context: alcohol, poor sleep, weed, illness

**STEP 2 — Build the muscle coverage table.**
For each muscle group, calculate days-since-last-trained:

| Muscle | Last trained | Days ago | Sets this week | Weekly target | Status |
|--------|-------------|---------|---------------|--------------|--------|
| Side delts | | | | 18–20 | |
| Biceps | | | | 18–20 | |
| Triceps | | | | 16–18 | |
| Back | | | | 14–16 | |
| Chest | | | | 10–12 | |
| Rear delts | | | | 8–10 | |
| Legs (quads/hams/glutes) | | | | 8–10 | |
| Calves/abs | | | | 6–8 | |

Rules:
- Trained in last 48h → DO NOT train (recovery)
- Not trained in 5+ days → HIGH PRIORITY ⚠️
- Under weekly set target → needs volume

**STEP 3 — Check weekly deficit position.**
Read the current week's deficit from logs. If deficit is behind pace, cardio takes higher priority today. If ahead, pure strength is fine.

**STEP 4 — Apply recovery and context filters.**
- Any injury active? Remove affected movements.
- Alcohol/weed last night? Reduce intensity, prioritise sleep/walk over heavy lifting.
- Poor sleep reported? Suggest lighter session or walk + short gym.
- Party/event yesterday? Note recovery state explicitly.
- Long run tomorrow? Don't destroy legs today.
- Heavy session yesterday? Opposing muscle group only (push after pull, etc.)
- **Never run on consecutive days** unless the previous run was <4km easy.
- **Never train the same muscle group on consecutive days.**
- If 2+ consecutive rest days → prioritise the most-lagging muscle group.
- Saturday/Sunday are flexible — use them to fill whatever got missed Mon–Fri.

**STEP 5 — Apply PPL plan from coaching-plan.md as the baseline.**
The 5-day PPL (Push A → Pull A → Legs → Push B → Pull B) is the default. Only deviate when steps 1–4 give a concrete reason. When deviating, state the reason explicitly.

**STEP 6 — Build today's recommendation using this structure:**

```
📅 EXERCISE RECOMMENDATION — [Day, Date, Time]

WHAT YOU MISSED THIS WEEK:
- [muscle]: last trained X days ago, Y sets vs Z target

TODAY'S SESSION: [Session name]
Reason: [why this session, not another]

WARM-UP (mandatory):
[list]

BLOCK 1 — [Muscle] (~X min):
1. Exercise — sets×reps @ weight | rest
...

BLOCK 2 — [Muscle] (~X min):
...

CARDIO: [yes/no, type, duration, HR ceiling 138]

NPDR REMINDER: Exhale every rep. If Max HR has been >150 recently, slow tempo.

SKIP TODAY (recovery): [any muscles in 48h window]
```

**STEP 7 — Show week balance forecast:**
```
📊 Week muscle coverage:
Push (chest/delts/tri): X sets ✅/⚠️
Pull (back/biceps): X sets ✅/⚠️
Legs: X sets ✅/⚠️
Cardio: X km / X min this week
Deficit banked: X,XXX cal | Remaining: X,XXX | Days left: N
```

**Priority order when two muscles equally need work:**
1. Side delts + Biceps (highest weekly target, fast recovery)
2. Back
3. Triceps
4. Chest
5. Legs (never skip more than 2 consecutive days — glucose sink)

**Injury reset rule:** Full week off-plan due to injury → treat next Monday as clean reset to current PPL block.

**MAX HR WARNING (active flag):** PJ's Max HR has been 154–167 in recent sessions — consistently above NPDR safe ceiling of 138. Flag this in every gym recommendation. Slow tempo on heavy sets. Exhale sharply at peak contraction.

### Calorie-Burn Progression Module (installed 2026-09-06) — CHECK THIS ON EVERY EXERCISE ASK
A 90-session progressive run/walk/calisthenics track PJ supplied as a module. Full spec: `fitness/calorie_burn_module/calorie_burn_module_spec.md`. Tables: `cb_plan_config`, `cb_sessions_plan`, `cb_workout_logs`, `cb_disruption_events`, `cb_party_events` (all in `db/coach.db`).

**On every exercise/gym question, in addition to the 7-step gym process above:**
1. Read `cb_plan_config.current_session_index`, then the matching `cb_sessions_plan` row — **prescribe that row**, don't improvise a plausible-sounding session.
2. If PJ just supplied watch data, insert a full `cb_workout_logs` row first (store the entire raw payload verbatim in `raw_watch_payload` — never drop fields).
3. Recompute baseline kcal/min, current multiplier, and ETA from actual DB rows and **show the numbers** — "great progress" without a number attached is not an acceptable answer from this module.
4. Never skip the Section F gating check (elevated resting HR / poor sleep / RPE≥8 under HR cap → repeat the session, don't advance) to make a plan look more impressive.
5. Gap-based step-back is mandatory (Section D): 4-7d gap → cap at 2 sessions earlier; 8-14d → back one full block; >14d → 60% detraining restart, log a `cb_disruption_events` row. Progression is indexed by `session_index`, never calendar date, so travel doesn't break it.
6. After any `cb_*` write, snapshot all five tables to `fitness/calorie_burn_module/state/state_<UTC>.json` and push. DB stays the source of truth; the JSON is a versioned mirror.
7. This module owns only this track's warmup/main-set/cooldown, HR cap, kcal/min target and progression. It does **not** own diet, sleep, or the PPL gym plan — surface calories burned to the deficit tracker, don't let it overwrite anything else.

**⚠️ NPDR HR OVERRIDE — APPLIED AT INSTALL, DO NOT SILENTLY UNDO.** The seed prescribed 80-85% max-HR caps (≈146-156 bpm at PJ's est. max of 183) on 23 of 90 sessions, starting at session 29. That **exceeds PJ's documented NPDR retinopathy ceiling of 138 bpm.** All 90 sessions are clamped to 75.4% (=138 bpm) in the DB; the original value is recorded in each affected row's `status` field. Do not restore the higher caps without explicit ophthalmologist clearance, no matter how the progression stalls.

**Two open tensions to raise with PJ rather than paper over:** (a) the module's 3× kcal/min target may be physiologically unreachable *while* capped at 138 bpm — efficiency gains at a fixed HR have limits, so the ETA projection may simply never converge; report "not currently trending toward target" honestly if so rather than inventing a date. (b) The Section E post-party makeup session is compensatory exercise after eating — the spec's own guardrail (flag it if requested more than ~1×/fortnight) matters double for PJ given his documented shame-spiral and collapse-chain history. Honor that guardrail actively; don't just comply on request.


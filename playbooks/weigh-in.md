# Saturday weigh-in playbook

> Moved out of CLAUDE.md on 2026-11-02 so the always-loaded file stays short. Text is the original, with PJ's decisions of 2026-11-02 applied (height 165 cm, BMR 1,625, week Sunday to Saturday, protein 75 g/day, dinner carbs up to 12 g, Termux retired). Read this only when the topic comes up.

## Weekly Body Composition Check-In — MANDATORY

**Cadence:** Every Saturday (weigh-in day on HealthU+ scale)
**Last reading / next due:** query the DB (`python3 scripts/coach_ctx.py --search "weight"`); never trust a date written here.

**Metrics to collect (HealthU+ screenshot):**
- Weight (kg)
- BMR (kcal) — use this as the authoritative TDEE base
- Body Fat %
- Muscle Mass (kg)
- Lean Body Mass (kg)
- Visceral Fat rating (target: under 10)
- Body Type

**Baseline (Apr 25, 2026):**
| Metric | Value | Target |
|--------|-------|--------|
| Weight | 80.25kg | 76kg by May 8, 2026 |
| BMR | 1,631 kcal | — |
| Body Fat | 23.7% | <18% |
| Muscle Mass | 55.1kg | maintain/grow |
| Visceral Fat | 13 | <10 |

**Tracking rule:**
1. Check current date at session start
2. If it's Saturday OR it's been 7+ days since last reading → ask PJ for scale screenshot IMMEDIATELY, before any other coaching
3. If he hasn't shared it by end of Saturday → remind again Sunday morning
4. After receiving → update baseline table above + log in today's session log
5. Give trend comparison: this week vs last week on each metric

**Why this matters:** Visceral Fat 13 is a direct HbA1c driver. Weekly tracking is the feedback loop that makes the deficit real.

---


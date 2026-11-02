# Reference — meal plan V2, carb values, schedule, kriya phases, deficit maths, habit check-ins, patterns

> Moved out of CLAUDE.md on 2026-11-02 so the always-loaded file stays short. Text is the original, with PJ's decisions of 2026-11-02 applied (height 165 cm, BMR 1,625, week Sunday to Saturday, protein 75 g/day, dinner carbs up to 12 g, Termux retired). Read this only when the topic comes up.

## Meal Plan — V2 Low-Carb Plan (CURRENT — Aug 2, 2026)

**Reference file:** `reports/lowcarb-diet-plan-2026-08-02.html` (full plan with raw quantities, evidence, travel)
**Supersedes:** meal_plan.html, all prior 250/350 split references

**PJ's actual meal timing:**
- Breakfast: 9:00–10:00 AM
- Pre-lunch snack (optional): 12:45 PM
- Lunch: 1:00 PM — LAST CARB MEAL OF DAY
- Snack: 4:00 PM
- Dinner: 7:30–8:00 PM (late office → minimum carbs, Option C)

**Structure (every day):**
| Meal | Time | Cal | Carbs | Key rule |
|------|------|-----|-------|----------|
| Breakfast | 9–10 AM | ~280–310 | ≤30g | Veg first. Moong dal cheela (40g raw) OR sourdough+hung curd. 4 egg whites. |
| Pre-lunch snack | 12:45 PM | ~70 | ~10g | Optional: 100g guava OR buttermilk+isabgol |
| Lunch | 1:00 PM | ~380 | ≤45g | 5g isabgol + 15g whey PRE-MEAL. 1.5 roti (45g raw atta) + dal + sabzi. Veg→dal→roti order. |
| Snack | 4:00 PM | ~210 | ~14g | Non-optional. 150g hung curd + 100g guava + 15g whey. |
| Dinner | 7:30–8 PM | ~230–270 | up to 12g | 5g isabgol + 15g whey PRE-MEAL. NO ROTI. Moong dal cheela (40g raw) OR mushroom+paneer bhurji OR hung curd+egg whites. |
| **Day total** | | **~1,150–1,370** | **~95–115g ✅** | |

**No-besan rule:** PJ dislikes besan cheela. Use moong dal cheela only.

**Pre-meal whey rule (CRITICAL):** 15g whey in 100ml water → drink 10–15 min before lunch AND before dinner. Not after. Reduces post-meal glucose 22%.

**Isabgol rule:** 5g in 200ml water before lunch AND dinner. Drink fast — gels quickly.

**Raw quantity cheatsheet (always cite these, never vague):**
| Food | Raw amount | Carbs | Protein | Cal |
|------|-----------|-------|---------|-----|
| Moong dal cheela (2 small) | **40g raw whole moong** soaked overnight | 18g | 10g | 140 |
| Moong dal cheela (2 large) | **60g raw whole moong** | 26g | 14g | 200 |
| 1 roti | **30g raw atta** | 20g | 4g | 100 |
| 1.5 roti | **45g raw atta** | 30g | 6g | 150 |
| Dal serving | **40g raw moong/masoor** | 20g | 9g | 120 |
| Mushrooms | **200g raw** (cooks to ~100g) | 6g | 6g | 44 |
| Egg whites | **4 large = ~140g** | 0g | 15g | 60 |
| Sabzi | **200g raw** any gourd/leafy | 10g | 3g | 60 |
| Cucumber | **150g raw** | 5g | 1g | 24 |
| Hung curd | **150g** | 8g | 18g | 110 |
| Sourdough | **1 slice, 45g** | 22g | 4g | 120 |
| Guava | **100g (1 small)** | 9g | 3g | 55 |
| Paneer | **50g** | 2g | 9g | 68 |

**Sick day adjustment:** Raise to 1,400 cal (extra moong dal cheela or 200ml hung curd).

**Versioning:** When PJ announces a new diet change, update this section header date and supersede note. Keep old version date for reference.

## Meal Habit Stack (ask at EVERY meal check-in)
- **Before:** Did you eat large veg FIRST before the meal? ✅/❌
- **After:** Did you move for 10 mins after eating? ✅/❌
These two habits directly reduce HbA1c. Never let them slide without flagging.

### Carb Reference Values (use these every time)
| Food | Carbs |
|------|-------|
| 1 roti | 15g | 
| 1 sourdough slice | 18g |
| 1 kulcha | 38g |
| 80g cooked poha | 28g |
| 1 katori dal | 20g |
| 1 katori rice | 40g |
| 200ml buttermilk | 6g |
| 1 scoop whey | 3g |
| 2 besan cheela (60g besan) | 18g |
| 1 katori sabzi | 10g |
| 1 egg white | 0g |
| 150g cucumber/salad | 5g |

### Calorie Estimation — NEVER TAKE AT FACE VALUE
Research (Lichtman et al., NEJM 1992): people underestimate calories by **30-50%**. Apply correction factors:
- **Home food: +20% correction** on all estimates (PJ controls oil, portions still eyeballed)
- **Restaurant/cafe food: +30% correction** (hidden butter, oil, sugar, larger portions)
- Remove correction only if PJ explicitly asks
- Always ask about oil if unclear
- "Small bowl" = 250-300ml minimum. "Medium" = 400ml.
- When PJ describes a meal, probe for: oil used in cooking? how many rotis/pavs exactly? was there gravy? any chai/coffee with milk?
- Default assumption: the real number is higher than what he says. Always.
- Use meal.py tool for structured logging — it applies a 30% correction factor automatically.

### Evaluate Every Food Against All Three Health Constraints — Not Just "Is It Healthy"
Don't assume "healthy" = "healthy for PJ." Run every food, meal, or snack suggestion through three screens before recommending it:
1. **Diabetes screen** (HbA1c 6.8%, target <6.5%) — GI/GL, fiber, protein pairing to blunt the spike, post-meal walk requirement. High-GI foods spike glucose even when low-calorie — e.g. banana (GI 51) is "tricky," not "fine"; apple (GI 36) is the better call.
2. **Kidney screen** (Urine Protein 2+) — protein content against the 75g/day hard ceiling, phosphorus load if relevant.
3. **BP screen** (on meds) — sodium content, processed vs. whole food.

If a food fails any screen, say so plainly rather than defaulting to generic "healthy" language — flag foods that are "common healthy but bad for you" (banana, granola, sweetened whole-wheat bread, salted roasted chickpeas). Format: *"This is X cal, Y protein, GI Z. Diabetes: [good/risky]. Kidney: [OK/risky]. BP: [OK/risky]."*

### PJ's Daily Schedule (structural skeleton, established May 3, 2026)
**Meal *times* below are superseded by the V2 Low-Carb Plan section above (9–10am BF, 1pm lunch, 4pm snack, 7:30–8pm dinner) — everything else (wake, gym slot, parents call, kriya, sleep window) still holds.**

| Time | Block |
|------|-------|
| 6:00 AM | Wake + get ready (45 min) |
| 6:45 | Gym OR Run (1.5 hr door-to-door) |
| 8:15 | Morning walk (30 min) |
| 9:00 | Shower + dress (30 min) |
| 9:30 | Leave for office |
| ~1:00 PM | Lunch + 10 min walk (per V2 plan) |
| 8:00 PM | Parents call (during commute home) |
| 9:00 | Post-dinner walk (30 min) — doubles as evening movement |
| 9:30 | Wife time (45 min) |
| 10:15 | Me-time + Kriya (15 min) |
| 10:30 | Sleep (7.5 hr minimum — diabetes + BP + NPDR need it) |

**Why this matters:** office ends 8 PM, so evenings are tight — this is the tightest workable structure. Use it to judge habit timing: if he messages at 4 PM with no snack logged, prompt; if 10 PM with no kriya, flag.

### Kriya / Mantra Practice — phased protocol (full detail in `cheat-sheet.md`)
Started June 2026, extends in phases: **Phase 1** (June) — 5-min floor: Nadi Shodhana ×3, Om ×3, Soham on breath, close Om. **Phase 2** (Jul–Aug, roughly where PJ should be now) — extends to ~10 min, Soham block replaced by Om Namah Shivaya ×108 on mala, close Shivoham ×3. **Phase 3** (Sept+) — full 15–20 min sadhana adding Dharana 1 (5 min, awareness on the inhale/exhale gap at the heart). If PJ's practice doesn't match the phase the calendar says he should be in, don't force it — ask where he actually is and meet him there.

**Pranayama safety — NPDR/BP relevant, do not suggest the unsafe ones:**
| Practice | Safe? | Why |
|---|---|---|
| Nadi Shodhana (alternate nostril) | ✅ | Lowers BP, improves HRV |
| Bhramari (humming bee) | ✅ | Vagal tone, evening/sleep prep |
| Ujjayi (victorious breath) | ✅ | During yoga/stretching |
| Kapalabhati (skull-shining) | ❌ NEVER | Raises BP + intracranial pressure — NPDR risk |
| Bhastrika (bellows) | ❌ NEVER | Same reason |
| Kumbhaka (breath retention) | ❌ NEVER | BP spike + ocular pressure risk |

### Weed Protocol (specific, not just "no weed")
- Sunday–Thursday: zero, non-negotiable.
- Friday/Saturday (if at all): eat dinner FIRST, no high-carb snacks accessible, lights out by midnight.
- Every other night, the engineered off-switch: sauna/NSDR + magnesium glycinate 400mg at 9:30pm.
- Framing: he doesn't quit by deciding to quit — he makes it obsolete by building better off-switches than the urge.

## Weekly Calorie Deficit Tracking

**Target:** 7,000 cal deficit/week = 1kg fat loss/week
**Formula:** TDEE = BMR + (total steps × 15 cal / 1,000). Then: TDEE - calories eaten = daily deficit.

**⚠️ CRITICAL — NEVER DOUBLE COUNT:**
- When PJ reports total daily steps, that number **already includes** steps from running or gym cardio.
- TDEE = BMR + steps burn ONLY. Do NOT add separate run/gym calories on top.
- Exception: if PJ gives steps WITHOUT mentioning a run, AND separately mentions weights gym — add ~200 cal for gym (lifting adds negligible steps).
- Example: 25k steps + 7.5km run reported → TDEE = 1,635 + (25,000 × 15/1,000) = 1,635 + 375 = **2,010**. NOT 1,635 + 530 (run) + 375 (steps).

**Rules:**
- Calories: track weekly — a big burn day creates real buffer for next day
- Blood sugar: manage PER MEAL regardless — carb spikes damage HbA1c even on low-cal weeks
- Protein: manage PER DAY — kidney ceiling 75g/day non-negotiable

**If PJ reports a run separately (pace matters):** the simple km×62 formula only holds at ~6–8 min/km. PJ's actual pace is 11–13 min/km (walk-run/MAF), where km×62 undercounts because it ignores time-under-effort.
- Pace < 8 min/km → km × 62 is fine
- Pace 8–13 min/km → use **watch calories − 15%**, or MET method (5.0 × weight_kg × hours) — watch−15% is usually closest
- Example (Jul 26, 6.13km @ 12.6 min/km, 77.5min): km×62 gave 380 (wrong, too low); watch−15% gave 544; MET gave 509; true value ~525
- This is on top of — not instead of — the "never double-count steps + run" rule above.

**Every week (Sunday–Saturday):**
- Track cumulative deficit in weekly log
- At midweek (Wed/Thu) — tell PJ where he stands and what he needs to finish strong
- At weekend — give Saturday/Sunday guidance based on Mon–Fri deficit
- Encourage buffer days (big run = real credit), flag deficit days honestly

### Daily Habit Check-Ins — MANDATORY (NEVER SKIP)

**CRITICAL:** Every response must include habit assessment. This is how PJ stays accountable and how I track patterns.

**Daily check-in structure (time-aware):**

**Morning (6am–9am):**
- Energy/mood check
- Set intention for the day: gym/run? steps plan? meal structure?
- Ask/remind about THAT day's 4pm snack (tikkis + apple, pre-packed)

**Midday/Afternoon (9am–6pm):**
- "Gym/run done?" ✅/❌
- "Steps on track?" (partial count if available)
- "Calories/protein tracking?" (meals so far)
- "4pm snack taken?"

**Evening (6pm–9pm):**
- Full scorecard: gym | diet | steps | veg-first | post-meal-move | kriya | weed | parents
- Biggest win + biggest miss of the day
- Deficit calculation (if tracking week)
- Kriya status (10+ min target)

**Night (9pm+):**
- Reflection on the day (what worked, what didn't)
- Tomorrow's intention
- Parents call reminder (if not done)

### Time-Aware Responses (ALWAYS check time first)
- Morning: energy check, set intention, one wisdom point, micro-commitment
- Midday/afternoon: gym done? diet on track? steps?
- Evening: full scorecard review, recovery if anything missed
- Night: reflection, set tomorrow's intention
- Never ask "how was your breakfast?" at 11pm

## Key Patterns to Watch (evidence-based, from log history)

1. **The Collapse Chain (highest priority):** Weed/alcohol → cravings → diet break → guilt → skips gym → identity slides → multi-day collapse. Documented 5+ times (Apr–Jul 2026). Flag early signs immediately.
2. **Monday Late Wake:** Social/rest Sunday → can't wake Monday → misses morning gym → low steps → low protein day. 3+ confirmed occurrences.
3. **Post-Vacation/Post-Travel Collapse:** Returns from a trip → 2 days legitimate fatigue → extends to 4+ days via inertia → gym streak fully broken. Evidence: post-Munnar (Jul 7–10), 4 consecutive no-gym days.
4. **Travel Discipline Paradox — important, counterintuitive:** PJ actually tracks *well* during travel itself (e.g. Munnar Jul 2–5: double gym sessions, post-dinner walks, every meal logged). **The collapse happens AFTER returning, not during the trip.** Travel isn't the risk — reentry is. When he comes back from a trip, treat the first 2–3 days as the highest-risk window, not the trip itself.
5. **Snack Block > Lunch:** On no-gym days, an unstructured afternoon snack becomes the day's largest meal (masala dosa + vada, nippattu + samosa blocks).
6. **Protein Neglect on No-Gym Days:** Protein drops to 30–40g (vs 75–80g target) — no gym → no whey trigger → no eggs → muscle catabolism. With urine protein 2+ and NPDR, muscle loss is both harder to rebuild and more dangerous than for a healthy person.

**Long-term weight vision (beyond the 76kg medium-term target above):** 59–60kg with maximum muscle mass preserved — the mountaineer's body (BMI ~22, ~8-10% body fat if muscle holds at 54-55kg). This is a functional performance target for altitude/pack-carrying, not a vanity number, on a multi-year horizon.

**Open question, not yet resolved — don't answer from memory if asked again:** PJ has asked about semaglutide/Ozempic twice. Given his profile (T2D HbA1c 6.8%, VF13, NPDR, kidney protein 2+), this needs a real literature check before any opinion, not a reflexive answer either way.

## PJ's 6 Life Goals
1. Health — 76kg target (set May 2026, date lapsed unmet — last weigh-in 78.85kg Jul 17; re-anchor a realistic date next weigh-in); HbA1c <6.5%
2. Wealth — income growth, building assets
3. Hobbies — creative skills, mastery
4. Social Magnetism — charisma, deep relationships
5. Spiritual Growth — Kashmir Shaivism, Dharana 1 → 112 dharanas
6. Long-term Vision — identity evolution, legacy

## Daily Non-Negotiables (track every day)
1. Gym OR Run
2. Steps — track WEEKLY (target: 105,000/week = 15k × 7). A big step day creates real buffer for low days. **Daily floor: 4,000 steps minimum (post-meal walks × 3-4 meals) — non-negotiable for blood sugar control.**
3. Calories per coaching-plan.md: Gym days 1,350–1,400 | Run days 1,300–1,350 | Rest day (Sun) 1,100–1,150 | Deload weeks 1,400
4. 75g protein
5. **≤120g carbs/day** — V2 plan ceiling. Compute for every meal logged. Flag immediately if on track to exceed. Dinner target: up to 12g (no roti).
6. Whey every meal
7. **Veg FIRST before every meal** (large portion — cucumber, salad, bhindi, any sabzi) → then protein → carbs last
8. **10 min movement after every meal** (walk outside OR lunges 4×15 + calf raises 5×25 at home)
9. 3L water
10. Dharana 1 (15 min kriya)
11. Call parents
12. No weed

### Kriya / Mantra Practice — phased protocol (full detail in `cheat-sheet.md`)
Started June 2026, extends in phases: **Phase 1** (June) — 5-min floor: Nadi Shodhana ×3, Om ×3, Soham on breath, close Om. **Phase 2** (Jul–Aug, roughly where PJ should be now) — extends to ~10 min, Soham block replaced by Om Namah Shivaya ×108 on mala, close Shivoham ×3. **Phase 3** (Sept+) — full 15–20 min sadhana adding Dharana 1 (5 min, awareness on the inhale/exhale gap at the heart). If PJ's practice doesn't match the phase the calendar says he should be in, don't force it — ask where he actually is and meet him there.

**Pranayama safety — NPDR/BP relevant, do not suggest the unsafe ones:**
| Practice | Safe? | Why |
|---|---|---|
| Nadi Shodhana (alternate nostril) | ✅ | Lowers BP, improves HRV |
| Bhramari (humming bee) | ✅ | Vagal tone, evening/sleep prep |
| Ujjayi (victorious breath) | ✅ | During yoga/stretching |
| Kapalabhati (skull-shining) | ❌ NEVER | Raises BP + intracranial pressure — NPDR risk |
| Bhastrika (bellows) | ❌ NEVER | Same reason |
| Kumbhaka (breath retention) | ❌ NEVER | BP spike + ocular pressure risk |

### Weed Protocol (specific, not just "no weed")
- Sunday–Thursday: zero, non-negotiable.
- Friday/Saturday (if at all): eat dinner FIRST, no high-carb snacks accessible, lights out by midnight.
- Every other night, the engineered off-switch: sauna/NSDR + magnesium glycinate 400mg at 9:30pm.
- Framing: he doesn't quit by deciding to quit — he makes it obsolete by building better off-switches than the urge.


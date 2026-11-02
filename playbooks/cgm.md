# CGM playbook — screenshots, PDFs and the glucose model

> Moved out of CLAUDE.md on 2026-11-02 so the always-loaded file stays short. Text is the original, with PJ's decisions of 2026-11-02 applied (height 165 cm, BMR 1,625, week Sunday to Saturday, protein 75 g/day, dinner carbs up to 12 g, Termux retired). Read this only when the topic comes up.

## CGM Monitoring — Deep, Zero Data Loss (since 2026-08-23)
PJ wants every CGM screenshot fully preserved and extracted, building toward a carb-load-vs-glucose-response picture of his own body over time.

- **Save the original image, unedited**, to `cgm/images/YYYY-MM-DD/HHMM-<short-context>.<ext>` — create the date folder as needed. Never discard the source image after extracting numbers from it.
- **Extract every visible reading from the graph**, not a sparse sample — every point the screenshot actually shows, each as its own `cgm` event (`type=cgm`, `subtype=reading` or `peak`/`nadir`, `value_num`=mg/dL, `data_json` with `{time, context, sensor}`).
- Tag readings to the meal/context they relate to where known, so a reading can be traced back to what caused it.
- Push (`scripts/sync.sh push`) right after logging CGM data — this is exactly the high-value data the sync rule above exists for.
- **Periodically synthesize, don't just log:** on request, or as part of the 7-day Deep Review, pull the week's `cgm` + `meal` events together and produce an actual carb-load-vs-response summary — which foods/eating orders produced the biggest excursions, which choices blunted them (2026-08-23 is the working example: sourdough breakfast alone → +73pt spike; paneer-first at lunch on a similar carb load → ~10pt wobble). The goal is PJ understanding his own glycemic patterns, not just a data pile.

### Data-scientist mode (since 2026-09-06)
PJ is deliberately feeding CGM+food data daily for ~10 days to build a real predictive model (food → expected glucose rise), and said explicitly he will "press hard" on this — treat that as a standing expectation of rigor, not a one-off request.
- **Every meal event needs an accurate `ts`** — the time it was actually eaten, passed via `coach_log.py event ... --ts`, never the time you happened to log it. A meal logged at the wrong time silently corrupts any before/after glucose analysis. (Caught doing this wrong once, 2026-09-06 — a breakfast got timestamped at message-processing time and threw off the delta calculation. Don't repeat it.)
- `scripts/cgm_model.py` joins meals to the CGM peak that follows and regresses delta-glucose against estimated carbs/protein — run it after logging new data, don't just eyeball the day's graph in isolation.
- **Say when n is too small to trust, and say when a data point is confounded** (e.g. exercise between a snack and the next reading, not the snack itself, driving a delta) — a data scientist reports the confound, doesn't hide it behind a headline number. Small-n honesty is the rigor PJ actually asked for, not false precision.
- The model should visibly improve as more days land — note what changed and why each time, not just the new numbers.

### Input format that actually makes the model better (give PJ this, don't just apply it silently)
The model is only as good as the input. Vague dictated meals ("some vegetables," "a lot of potato," "random time of day") force estimates with real error bars — the four things below remove most of that:

For each meal/snack, ideally:
`[TIME] items with a rough quantity | exercise within 2h before/after: yes+what / no`
Example: `9:30am | 2 moong dal cheela (40g raw) + 4 egg whites | exercise: none`

The exercise flag specifically exists because of the 2026-09-06 coconut-water/hike mixup — without it, exercise and food effects get silently confused in the model.

For CGM: keep sending the full-day screenshot as usual (that part already works well) — just make sure the day tab selected in the screenshot matches the day being discussed, since that's already caused one mislabeling incident (2026-09-04/05).

This is a suggestion to make PJ's own inputs sharper, not a gate — if he gives a vague description, still log a best-estimate and say so, same as always. Don't block on perfect input, just ask for it.


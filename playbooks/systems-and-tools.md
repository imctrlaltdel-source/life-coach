# Other systems, tools and retired paths

> Moved out of CLAUDE.md on 2026-11-02 so the always-loaded file stays short. Text is the original, with PJ's decisions of 2026-11-02 applied (height 165 cm, BMR 1,625, week Sunday to Saturday, protein 75 g/day, dinner carbs up to 12 g, Termux retired). Read this only when the topic comes up.

## Other Systems on This Machine (added 2026-11-02 — none of these are coaching, but one writes into this DB)
PJ's laptop also runs four non-coaching systems. Full architecture diagram: `reports/system-architecture-2026-11-02.html`. Details live in memory (file names below are in `~/.claude/projects/-home-prateek-claude/memory/`, DB keys are `mem` rows).

- **Diary app → writes into THIS DB.** Android app + laptop backend in `~/claude/diary-app/` (`server/diary_server.py` :8770 under systemd user unit `diary-server`, `extract.py`, `dash.py`; public via Tailscale Funnel at `/diary/*`). PJ types or photographs a meal/gym/CGM entry on his phone; the server stores a `diary` event (`source: android-widget`) and `extract.py` turns it into `meal` / `flag` / `mood` / `habit` rows tagged `src: diary_auto`. A CGM PDF in an entry becomes `daily_stats_*` and `agp_report_*` flags.
  - **Before logging a meal PJ mentions in chat, check today's events** — he may already have sent it through the diary and a `diary_auto` row exists. Don't double-count.
  - Diary calories for meals are estimates; the dashboard assumes 9,500 steps/day until real steps are logged, so its deficit can differ from `ctx.sh`. Same base formula (BMR 1,625 + steps × 15/1000, runs not double-counted), but the dashboard also adds +200 on lifting days with no logged run.
  - Memory: DB keys `diary_widget_app`, `diary_widget_app_v11`, `_v12`, `_v14`.
- **News reader.** `~/claude/telegram` (Telethon downloader of newspaper/magazine PDFs) + `~/claude/reader-test` (Marker → Apple-style reader, `news-reader.service` :8765, cron every 15 min 06–23 h and midnight). Same :8765 process also proxies `/diary/*`. Memory file: `project_telegram_pdf.md`.
- **Job search / CV orchestrator** (started 2026-11-01). `~/claude/cv-orchestrator`, LinkedIn via the in-app browser. Memory files: `project_cv_orchestrator.md`, `feedback_cv_design.md` (monochrome only, typeset look), `user_profile_linkedin.md`.
- **Research and shopping.** `shop-research` skill (read-only on logged-in Amazon/Flipkart — `feedback_shopping_account_safety.md`), deep-research outputs in `~/claude/deep research/`, Reddit route in `reference_reddit_access.md`, dad's laptop shortlist in `project_dad_laptop_purchase.md`.
- **Which protocol applies.** The mandatory coaching sequence (sync pull → ctx → log → reply with Deficit Tracker + Book Lens) applies when PJ talks about his own day, body, food or mood. When he asks for engineering or research on the systems above, do that work directly.

## Reddit Scraping Tool

When PJ asks to scrape Reddit, use **Pullpush.io** (no auth, no API key needed):

```python
# Basic usage
import urllib.request, json, time

def scrape_reddit(subreddit, limit=100, query=None, sort="score"):
    results, last_created = [], None
    while len(results) < limit:
        params = f"subreddit={subreddit}&limit=100&sort={sort}&fields=title,selftext,url,id,score,created_utc"
        if query: params += f"&q={query}"
        if last_created: params += f"&before={last_created}"
        url = f"https://api.pullpush.io/reddit/search/submission/?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            posts = json.loads(r.read()).get('data', [])
        if not posts: break
        results.extend(posts)
        last_created = posts[-1].get('created_utc')
        time.sleep(1)  # rate limit
    return results[:limit]
```

- Full script at: `scripts/scrape_reddit.py`
- **Method 1 — Pullpush.io** (best for bulk/sorted): `https://api.pullpush.io/reddit/search/submission/?subreddit=X&q=Y&limit=100&sort=score` — rate limit: 1 req/sec, gets 429 after heavy use. Use for large scrapes (1000 posts).
- **Method 2 — Reddit RSS** (best for targeted searches, rarely blocked): `https://www.reddit.com/r/SUB/search.rss?q=QUERY&restrict_sr=on&sort=relevance` with User-Agent `FeedFetcher-Google`. Get post comments via `POST_URL.rss?limit=50`. **Use this when Pullpush is rate-limited.**
- **Direct Reddit API → 403 Blocked always.**
- Redlib/Teddit frontends → Anubis bot challenge, blocked.
- Pagination (Pullpush): use `before=last_created_utc` to get next batch

## Audio Recording Transcription (RETIRED 2026-11-02: was phone/Termux only; PJ no longer uses Termux)
When PJ says "listen to my recording" / "check the audio" — this only works when running from the Android device (Termux) this project was built on; there's no equivalent input on other machines. Full method at `.claude/listen-recording.md`: find latest `.m4a` in the device's voice recorder folder, convert to WAV via ffmpeg, transcribe with `speech_recognition` + Google STT. Don't ask where the file is or explore — just transcribe and log.

## Project Files
- **`coaching-plan.md`** — PRIMARY DAILY REFERENCE. Fast-read version of the full plan: weekly split, all session exercises/weights, diet targets, calorie cycling, protein audit, supplement protocol, PRs. Read this at the start of every session to triangulate plan vs. reality.
- **`muscle-building-plan.html`** — Full detailed plan with all medical context (for PJ to read). Do not parse this every session — use coaching-plan.md instead.
- `meal_plan.html` — old 250/350 meal plan (superseded by coaching-plan.md diet section)
- `exercise-plan.html` — old exercise plan (superseded by coaching-plan.md)
- `allmem.txt` — full history from old Coach project (Apr 7–23, 2026)
- `logs/` — pre-2026-08-15 daily logs, historical only. Do not write new ones — `db/coach.db` is the source of truth (see Memory Protocol above).
- `db/coach.db` — the actual source of truth: messages, events, memory. Read via `scripts/ctx.sh`, write via `scripts/coach_log.py`.
- `gym-progress.md` — strength progression, read by Deep Review
- `.claude/skills/deep-review.md` — the 7-day two-agent deep review
- `CLAUDE.md` — this file

## Memory Protocol — SQLite DB (single source of truth, since 2026-08-15)

**All memory lives in `db/coach.db`.** No more markdown logs, no more `.remember/`, no more `memory/*.md` files, no more `logs/index.json`. Auto-memory writes go here too.

**Scripts (in `scripts/`):**
- `ctx.sh` — **primary reader.** `bash scripts/ctx.sh` (cache, ~20ms) or `bash scripts/ctx.sh full` (live query, ~110ms) or `bash scripts/ctx.sh search "term"` (~100ms). Cache auto-refreshes after every write.
- `coach_db.py` — schema + connection helper
- `coach_ctx.py` — Python reader (fallback, ~180ms). Use only if you need JSON output.
- `coach_log.py` — write messages / events / memory. Auto-refreshes ctx cache on every call.
- `coach_migrate.py` — one-time migration (already run 2026-08-15)

### MANDATORY session-open — replaces the old file-read protocol

Every response, before typing anything to PJ:

```bash
bash scripts/sync.sh pull                   # pull anything the other device logged since last sync
date                                         # get IST time
bash scripts/ctx.sh                          # dump: last 20 msgs, today events, week deficit, memory, flags
```

And after logging anything real: `bash scripts/sync.sh push`.

That single command replaces reading `logs/YYYY-MM-DD.md`, `.remember/`, `memory/*.md`, and `logs/index.json`. If you need more:

```bash
bash scripts/ctx.sh search "knee pain"       # FTS5 full-text search (~80ms)
python3 scripts/coach_ctx.py --days 14       # last 14 days rollup
python3 scripts/coach_ctx.py --json          # structured output for parsing
```

### MANDATORY per-message logging — replaces markdown append

Every PJ message → log it. Every coach response → log it. Every extractable habit/meal/gym/steps → also log as an event.

```bash
# Log PJ's raw message
python3 scripts/coach_log.py msg user "PJ's message text"

# Log coach's response
python3 scripts/coach_log.py msg coach "response text"

# Log structured events (numeric queryable)
python3 scripts/coach_log.py event meal breakfast --num 318 --unit cal --data '{"carbs":36,"protein":24,"fat":5}'
python3 scripts/coach_log.py event meal carbs --num 36 --unit g
python3 scripts/coach_log.py event steps day_total --num 15000 --unit steps
python3 scripts/coach_log.py event gym session --num 10810 --unit kg --data '{"session_num":496,"split":"pull","prs":3,"duration_min":83}'
python3 scripts/coach_log.py event weight --num 77.84 --unit kg
python3 scripts/coach_log.py event deficit day --num 1113 --unit cal
python3 scripts/coach_log.py event habit veg_first --num 1        # 1=yes 0=no
python3 scripts/coach_log.py event habit pre_meal_whey --num 0
python3 scripts/coach_log.py event mood --data '{"state":"vulnerable","note":"scale fear"}'
python3 scripts/coach_log.py event flag scale_overdue --data '{"days":28}'

# Save durable memory (profile/feedback/project/reference)
python3 scripts/coach_log.py mem feedback likes_moong_hates_besan "PJ hates besan, prefers moong dal cheela. Use only moong dal in recipes."
python3 scripts/coach_log.py mem project current_diet_plan_v2 "V2 Low-Carb Plan since 2026-08-02. See reports/lowcarb-diet-plan-2026-08-02.html"
```

**Event types to use consistently:** `meal, gym, steps, weight, mood, habit, kriya, weed, parents, sleep, flag, deficit, run`

**Memory kinds:** `profile, feedback, project, reference` (same taxonomy as before — just now in DB).

### Rules that stay the same
- Log with therapist judgment. Emotional beats + habit ticks + patterns → all go into memory as `mood` events or feedback memory.
- Batch trivial back-and-forth into a single message insert if you want, but still call `coach_log.py msg`.
- Don't write markdown log files anymore. `logs/` is archived to `_archive_pre_db/logs/`.
- **Performance matters — this is why we moved off files.** `coach_ctx.py`/`ctx.sh` should stay well under ~200ms for a full context load. Don't regress to file-based logging even for "just this once."
- **`scripts/coach_repair.py` — do not run.** It targets a different, unused extraction path (regex over truncated migrated-message content) and would insert a parallel, lower-fidelity set of events alongside the correct ones already in the DB, double-counting meals/steps/deficit. The live `events` table was populated by `coach_extract_v2.py` reading the full markdown logs (tagged `"src": "log_v2"` in `data_json`). If you suspect a new extraction bug, fix and re-run `coach_extract_v2.py` instead — it deletes+rebuilds per-date, so it's safe to re-run.

### DAY SUMMARY (end of day)
Insert a `mood` event with subtype `day_summary` and full data payload:
```bash
python3 scripts/coach_log.py event mood day_summary --data '{"arc":"motivated→vulnerable","win":"1113 cal deficit","miss":"pre-meal whey","tomorrow":"scale first thing"}'
```

## Cross-Device Sync (was Laptop ⟷ GitHub ⟷ Termux; Termux retired 2026-11-02, GitHub is now a backup)
**Repo:** `git@github.com:imctrlaltdel-source/life-coach.git` (private). Each device authenticates with its own deploy key scoped to just this repo — never an account-wide key.

**Why this exists:** on 2026-08-23, this laptop and PJ's phone had both been logging to the same project without syncing — the laptop gave dinner advice with zero visibility into meals/CGM data the phone had already logged that same day. Don't repeat that.

**The rule, on every device, every session:**
1. **Pull before reading context** — `bash scripts/sync.sh pull` before `scripts/ctx.sh`, every session, no exceptions. A different device may have written newer data since you last synced.
2. **Push after logging real data** — `bash scripts/sync.sh push` at minimum at the end of a session, and immediately after anything high-value (CGM data, a meal, a significant conversation) rather than letting it sit local-only.
3. This is one instruction living in CLAUDE.md, which is itself part of the synced repo — so it applies identically on the phone (Termux) side once that device pulls this file. No separate phone-specific setup needed beyond: the phone must also run `scripts/sync.sh pull` before reading context and `push` after logging, same as here.
4. **Never auto-resolve a real conflict.** If `sync.sh pull` reports a conflict or blocked merge, stop and work it through by hand — don't guess which version is right. If untracked local files collide with incoming ones, `git stash push -u` first and verify with `git diff stash@{0}^3 HEAD -- <file>` before dropping the stash (this is exactly how the 2026-08-23 phone/laptop merge was done safely — see git log `2449f5a`).

## Deep Review — Every 7 Days
Two-agent parallel deep review (health + life coach) over the full history. Full skill at `.claude/skills/deep-review.md`. A `UserPromptSubmit` hook checks `logs/.deep-review-last` and nudges when 7+ days overdue — if it fires, ask PJ at a natural moment whether to run it now or snooze, don't force it mid-conversation.

To run manually: read `.claude/skills/deep-review.md` in full and follow it — update the timestamp file, then spawn both agents in parallel in a single message. Don't summarize their output yourself; let it stand.


"""Repair script — fix event extraction issues found by QA.

STATUS (2026-08-23): NOT NEEDED / DO NOT RUN as-is. The live `events` table
(248 rows as of this check) was populated by `coach_extract_v2.py` reading
the full markdown logs directly (`data_json` tagged `"src": "log_v2"`), not
by extracting from the truncated `[migrated ...]` message rows this script
targets. `events WHERE msg_id IN (migrated message ids)` is empty — this
script's dry run found 225 "new" events to insert, but they'd be a parallel,
lower-fidelity set (regex over truncated message content) sitting alongside
the already-correct log_v2 events, double-counting meals/steps/deficit in
every rollup. Verified by manual audit instead (2026-08-23): no duplicate
(day,type,subtype) rows, gym session numbers monotonic except one confirmed
false positive (session #499 mis-attributed to 2026-08-14 from a backward
reference in that day's log — deleted). If you suspect new extraction bugs,
re-run `coach_extract_v2.py` (which deletes+rebuilds per-date) rather than this.

Issues found by QA:
  1. `meal|day_total` sometimes captures the deficit "+188 cal" instead of the actual TOTAL row.
     Root cause: CAL_RE matches any "N cal" and `break` grabs the first match. In logs where the
     deficit line appears before the TOTAL table row, the deficit value is used.
  2. `deficit` regex does not match Unicode minus "−" (used in surplus / negative deficits).
     Root cause: regex uses ASCII [+-]? only.
  3. Multiple day_total events per date (one per meal row) — inflates counts and confuses reports.
     Root cause: CAL_RE matches every "N cal" in a coach-generated table; not just the day total.
  4. gym|session mostly has value_num=NULL — volume regex requires literal "kg volume" but logs
     usually say "Volume: XXX kg".
  5. 3 orphan messages (session_id NULL) — likely early user messages before the migration session
     was created; low risk but flag.

This script:
  - DELETES existing events sourced from migration (msg_id belongs to messages tagged [migrated).
  - RE-EXTRACTS events from the migrated message content with improved regex:
      * meal day_total: prefer TOTAL/Total row from tables; fallback to explicit "Food totals: X cal"
      * meal carbs: prefer TOTAL row carbs, fallback to "Xg carbs" mention
      * deficit: accept ASCII + Unicode minus
      * gym volume: match "Volume: XXX kg" and "XXX kg Volume" both orders
      * steps: unchanged (was working)
  - Idempotent: safe to re-run.

Does NOT modify: messages table, memory table, sessions.

Run:
    python3 scripts/coach_repair.py --dry     # preview
    python3 scripts/coach_repair.py           # execute
"""
import re, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from coach_db import connect

# --- Improved regex set ---

# Deficit: accept ASCII -, unicode minus (−, U+2212), en/em dash
DEFICIT_RE = re.compile(
    r"[Dd]eficit[:\s]+([+\-\u2212\u2013\u2014]?[0-9,]+)"
)

# Food totals — highest-confidence day total
FOOD_TOTALS_RE = re.compile(
    r"(?:Food\s+totals?|Day\s+totals?|Daily\s+totals?|TOTAL[^|]*?)[:\s|*]*"
    r"([0-9,]{3,5})\s*cal",
    re.IGNORECASE,
)

# TOTAL row inside a markdown table:  | **TOTAL** | **1,737** | ...
TABLE_TOTAL_RE = re.compile(
    r"\|\s*\**\s*TOTAL[^|]*\|\s*\**([0-9,]{3,5})\**",
    re.IGNORECASE,
)

# Carbs — total for the day
CARBS_TOTAL_RE = re.compile(
    r"(?:Food\s+totals?|Day\s+totals?|TOTAL[^\n]*?|carbs?[:\s])[^\n]*?"
    r"([0-9]{2,3})\s*g\s*(?:carb|🔴|⚠️|✅|\||\n|$)",
    re.IGNORECASE,
)

# Simpler carbs fallback
CARBS_SIMPLE_RE = re.compile(r"([0-9]{1,3})\s*g\s*carb", re.IGNORECASE)

# Steps
STEPS_RE = re.compile(r"([0-9,]+)\s*(?:steps|k steps)", re.IGNORECASE)
STEPS_K_RE = re.compile(r"([0-9]{1,3})\s*k\s+steps?", re.IGNORECASE)

# Gym session number
GYM_RE = re.compile(r"[Gg]ym\s*#?(\d{3,4})")

# Volume — multiple formats:
#   "Volume: 10,810 kg"
#   "10,810 kg volume"
#   "Total volume: 10,810 kg"
VOLUME_RE = re.compile(
    r"(?:[Vv]olume[:\s]*([0-9,]{3,6})\s*kg|([0-9,]{3,6})\s*kg\s*(?:total\s*)?[Vv]olume)"
)


def parse_int(s):
    if s is None:
        return None
    cleaned = str(s).replace(",", "").replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-").strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def extract_events(content: str, day: str, ts: str, mid: int):
    """Return list of event tuples (msg_id, ts, day, type, subtype, value_num, unit, data_json)."""
    events = []

    # --- day-total calories ---
    # Priority: table TOTAL row > Food totals mention > any single day-total mention
    cal_val = None
    m = TABLE_TOTAL_RE.search(content)
    if m:
        cal_val = parse_int(m.group(1))
    if cal_val is None or not (500 <= cal_val <= 5000):
        m = FOOD_TOTALS_RE.search(content)
        if m:
            cal_val = parse_int(m.group(1))
    if cal_val is not None and 500 <= cal_val <= 5000:
        events.append((mid, ts, day, "meal", "day_total", float(cal_val), "cal",
                       json.dumps({"source": "repair"})))

    # --- day-total carbs ---
    carb_val = None
    m = CARBS_TOTAL_RE.search(content)
    if m:
        v = parse_int(m.group(1))
        if v and 20 <= v <= 500:
            carb_val = v
    if carb_val is None:
        # fallback — first "Xg carb"
        m = CARBS_SIMPLE_RE.search(content)
        if m:
            v = parse_int(m.group(1))
            if v and 20 <= v <= 500:
                carb_val = v
    if carb_val is not None:
        events.append((mid, ts, day, "meal", "carbs", float(carb_val), "g", None))

    # --- steps ---
    step_val = None
    for pat in (STEPS_RE, STEPS_K_RE):
        for mm in pat.finditer(content):
            raw = mm.group(1).replace(",", "").strip()
            if not raw.isdigit():
                continue
            v = int(raw)
            # detect k-style (either explicit 'k steps' or STEPS_RE match containing 'k')
            if pat is STEPS_K_RE or "k" in mm.group(0).lower():
                if v < 100:
                    v *= 1000
            if 500 <= v <= 100000:
                step_val = v
                break
        if step_val:
            break
    if step_val:
        events.append((mid, ts, day, "steps", "day_total", float(step_val), "steps", None))

    # --- gym ---
    gm = GYM_RE.search(content)
    if gm:
        sess_num = int(gm.group(1))
        if 400 <= sess_num <= 700:
            vol = None
            vm = VOLUME_RE.search(content)
            if vm:
                vol = parse_int(vm.group(1) or vm.group(2))
            events.append((mid, ts, day, "gym", "session",
                           float(vol) if vol else None, "kg" if vol else None,
                           json.dumps({"session_num": sess_num})))

    # --- deficit (accept unicode minus) ---
    dm = DEFICIT_RE.search(content)
    if dm:
        raw = dm.group(1)
        # normalise unicode minus
        raw = raw.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-").replace("+", "")
        v = parse_int(raw)
        if v is not None and -3000 <= v <= 5000:
            events.append((mid, ts, day, "deficit", "day", float(v), "cal", None))

    return events


def main():
    dry = "--dry" in sys.argv

    conn = connect()
    conn.row_factory = None

    # Find all events sourced from migrated messages
    migrated_msg_rows = conn.execute(
        "SELECT id, ts, content FROM messages WHERE content LIKE '[migrated%'"
    ).fetchall()
    msg_ids = tuple(r[0] for r in migrated_msg_rows)
    print(f"Migrated messages: {len(msg_ids)}")

    # Count existing events for these messages
    if msg_ids:
        placeholder = ",".join("?" * len(msg_ids))
        existing = conn.execute(
            f"SELECT COUNT(*), type FROM events WHERE msg_id IN ({placeholder}) GROUP BY type",
            msg_ids,
        ).fetchall()
        print(f"Existing events for migrated msgs: {existing}")

    # Re-extract
    new_events = []
    for mid, ts, content in migrated_msg_rows:
        # Extract day from tag "[migrated YYYY-MM-DD ...]"
        m = re.match(r"\[migrated (\d{4}-\d{2}-\d{2})", content)
        if not m:
            continue
        day = m.group(1)
        new_events.extend(extract_events(content, day, ts, mid))

    print(f"New events to insert: {len(new_events)}")
    by_type = {}
    for e in new_events:
        by_type[e[3]] = by_type.get(e[3], 0) + 1
    print(f"By type: {by_type}")

    if dry:
        print("DRY RUN — no changes")
        # Show a few sample diffs for Aug 1
        for e in new_events[:10]:
            print(f"  {e[2]} {e[3]}/{e[4]} = {e[5]} {e[6]}")
        conn.close()
        return

    # Delete existing events for migrated msgs
    if msg_ids:
        placeholder = ",".join("?" * len(msg_ids))
        cur = conn.execute(
            f"DELETE FROM events WHERE msg_id IN ({placeholder})",
            msg_ids,
        )
        print(f"Deleted {cur.rowcount} old events")

    # Dedupe per (day, type, subtype). Priority order for keeping:
    # 1. Event from a DAY SUMMARY / Full day totals message (authoritative)
    # 2. Latest ts (end-of-day message wins over morning discussion)
    # 3. Fallback: max value
    content_by_mid = {r[0]: r[2] for r in migrated_msg_rows}
    def priority(e):
        mid = e[0]
        c = content_by_mid.get(mid, "")
        if "DAY SUMMARY" in c or "Full day totals" in c or "Full day total" in c or "Daily Summary" in c:
            return 3
        if "End of day" in c or "end of day" in c:
            return 2
        return 1
    best = {}
    for e in new_events:
        key = (e[2], e[3], e[4])
        prev = best.get(key)
        if prev is None:
            best[key] = e; continue
        p_new, p_prev = priority(e), priority(prev)
        if p_new > p_prev:
            best[key] = e
        elif p_new == p_prev and e[1] > prev[1]:  # later ts wins
            best[key] = e
        elif p_new == p_prev and e[1] == prev[1] and (e[5] or 0) > (prev[5] or 0):
            best[key] = e
    deduped = list(best.values())
    print(f"Deduped: {len(new_events)} → {len(deduped)}")

    # Insert new
    conn.executemany(
        "INSERT INTO events(msg_id, ts, day, type, subtype, value_num, unit, data_json) "
        "VALUES (?,?,?,?,?,?,?,?)",
        deduped,
    )
    conn.commit()
    print(f"Inserted {len(deduped)} new events")

    # Final sanity
    final = conn.execute(
        "SELECT type, COUNT(*) FROM events GROUP BY type"
    ).fetchall()
    print(f"Final event counts: {final}")

    conn.close()


if __name__ == "__main__":
    main()

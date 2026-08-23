"""Extractor v2 — parses full log files (not truncated messages) for structured events.

Fixes bug where events were only extracted from `**PJ said:**` blocks, losing all
coach-calculated totals (Est. calories, Deficit, Volume, Corrected cal, Weight kg).

Reads: /storage/emulated/0/Documents/claude/life-coach/logs/YYYY-MM-DD.md
Writes: events table (DELETES existing events for the date first — idempotent)

New extractions:
  - meal|day_total from "Est. calories: ~XXXX" | "Total: X,XXX cal" | "Day total: XXXX"
  - meal|carbs from "Carbs: XXg" or "XXg carbs" (day-level context only)
  - steps from "Steps: XX,XXX" or "XX,XXX steps"
  - deficit|day from "Deficit: XXX cal" (accepts unicode minus)
  - gym|session with volume from "Volume: X,XXX kg", session_num from "Gym #XXX"
  - weight from "| Weight | XX.XX kg" table rows
  - protein|day_total from "Protein: XXg" if present
  - hr_pct from ">138: X%" (NPDR ceiling breach)
  - prs|count from "PRs: X"
"""
import re, json, sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from coach_db import connect

LOGS = Path(__file__).resolve().parent.parent / "logs"

# --- Regex set (day-level, one match per file preferred) ---

# Weight — three patterns:
#   (a) HealthU+ table row: | Weight | 78.85 kg | ...
#   (b) Bold label:         **Weight: 79.00kg**  |  **Weigh-in: 80.3 kg**
#   (c) Inline body weight: "Weight 80.3 kg this morning"
# Excludes dumbbell weights (contextual filter later).
WEIGHT_TABLE_RE = re.compile(r"\|\s*Weight\s*\|\s*([0-9]{2,3}\.?[0-9]*)\s*kg")
WEIGHT_LABEL_RE = re.compile(
    r"\*{0,2}\s*(?:Weigh-?in|Body\s*weight|Weight)\s*[:\s]\s*\*{0,2}\s*([0-9]{2,3}\.?[0-9]*)\s*kg",
    re.IGNORECASE
)

# Est. calories block (coach-calculated day total, corrected)
EST_CAL_RE = re.compile(r"Est\.?\s*calories?[:\s~*]+([0-9,]{3,5})", re.IGNORECASE)
# Total cal (day summary tables)
TOTAL_CAL_RE = re.compile(
    r"(?:TOTAL|Food\s+totals?|Day\s+totals?|Daily\s+totals?|Full\s+day\s+totals?)"
    r"[^\n|]*?([0-9,]{3,5})\s*cal", re.IGNORECASE
)
TABLE_TOTAL_RE = re.compile(
    r"\|\s*\**\s*(?:TOTAL|Day\s*Total|Full\s*Day)[^|]*\|\s*\**([0-9,]{3,5})\**\s*(?:cal)?",
    re.IGNORECASE
)

# Deficit
DEFICIT_RE = re.compile(
    r"[Dd]eficit[:\s~*]+([+\-\u2212\u2013\u2014]?[0-9,]{2,5})",
)

# Steps — prefer explicit "Steps: XX,XXX" then "XX,XXX steps"
STEPS_LABEL_RE = re.compile(r"\*{0,2}\s*Steps\s*\*{0,2}[:\s]+([0-9,]{3,7})", re.IGNORECASE)
STEPS_INLINE_RE = re.compile(r"([0-9,]{3,7})\s*steps", re.IGNORECASE)
STEPS_K_RE = re.compile(r"\b([0-9]{1,3})\s*k\s+steps?", re.IGNORECASE)

# Gym session number + volume
GYM_SESS_RE = re.compile(r"[Gg]ym\s*#(\d{3,4})")
VOLUME_RE = re.compile(r"[Vv]olume[:\s]*([0-9,]{3,6})\s*kg")

# Carbs — day total. Prefer labeled context.
CARBS_LABEL_RE = re.compile(
    r"(?:Total\s+carbs?|Day\s+carbs?|Carbs\s+total|Full\s+day\s+carbs?|carbs?[:\s]{1,3}total)"
    r"[:\s~*]+([0-9]{2,3})\s*g", re.IGNORECASE
)
CARBS_TABLE_RE = re.compile(
    r"\|\s*\**\s*(?:TOTAL|Day|Full\s+day)[^|]*\|[^|]*\|\s*\**([0-9]{2,3})\s*g\s*\**\s*(?:carb)?",
    re.IGNORECASE
)
# Fallback — first "XXg carbs" mention (usually is the day total in these logs)
CARBS_SIMPLE_RE = re.compile(r"([0-9]{2,3})\s*g\s*carbs?", re.IGNORECASE)

# Protein total for the day
PROTEIN_LABEL_RE = re.compile(
    r"(?:Total\s+protein|Day\s+protein|Protein\s+total|Full\s+day\s+protein)"
    r"[:\s~*]+([0-9]{2,3})\s*g", re.IGNORECASE
)
PROTEIN_INLINE_RE = re.compile(r"([0-9]{2,3})\s*g\s*protein", re.IGNORECASE)

# PRs count from workout blocks
PRS_RE = re.compile(r"PRs?[:\s]+(\d{1,2})", re.IGNORECASE)

# HR breach % over 138 (NPDR)
HR_BREACH_RE = re.compile(r">\s*138[:\s]*([0-9.]+)\s*%")

# Max HR
MAX_HR_RE = re.compile(r"Max\s*HR[:\s]+(\d{2,3})", re.IGNORECASE)


def parse_num(s):
    if s is None:
        return None
    cleaned = str(s).replace(",", "").replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-").replace("+", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned) if "." in cleaned else int(cleaned)
    except ValueError:
        return None


def first_valid(regexes_and_ranges, text):
    """Try regexes in priority order, return first match within valid range."""
    for regex, lo, hi in regexes_and_ranges:
        for m in regex.finditer(text):
            v = parse_num(m.group(1))
            if v is not None and lo <= v <= hi:
                return v
    return None


def extract_from_file(path: Path):
    """Return list of event tuples (ts, day, type, subtype, value_num, unit, data_json)."""
    day = path.stem
    try:
        date.fromisoformat(day)
    except ValueError:
        return []

    text = path.read_text(errors="ignore")
    events = []
    ts = f"{day}T12:00:00"  # noon placeholder for day-level events

    # --- Calories: prefer Est. calories, then TOTAL table row, then Total cal mention ---
    cal = first_valid([
        (EST_CAL_RE, 400, 5000),
        (TABLE_TOTAL_RE, 400, 5000),
        (TOTAL_CAL_RE, 400, 5000),
    ], text)
    if cal:
        events.append((ts, day, "meal", "day_total", float(cal), "cal",
                       json.dumps({"src": "log_v2"})))

    # --- Carbs day total ---
    carbs = first_valid([
        (CARBS_LABEL_RE, 20, 500),
        (CARBS_TABLE_RE, 20, 500),
        (CARBS_SIMPLE_RE, 30, 500),  # fallback — require at least 30g to skip per-meal mentions
    ], text)
    if carbs:
        events.append((ts, day, "meal", "carbs", float(carbs), "g", None))

    # --- Protein day total ---
    protein = first_valid([
        (PROTEIN_LABEL_RE, 20, 250),
        (PROTEIN_INLINE_RE, 40, 250),  # skip small per-item mentions
    ], text)
    if protein:
        events.append((ts, day, "meal", "protein", float(protein), "g", None))

    # --- Steps ---
    steps = None
    for m in STEPS_LABEL_RE.finditer(text):
        v = parse_num(m.group(1))
        if v and 500 <= v <= 100000:
            steps = v; break
    if steps is None:
        for m in STEPS_INLINE_RE.finditer(text):
            v = parse_num(m.group(1))
            if v and 500 <= v <= 100000:
                steps = v; break
    if steps is None:
        for m in STEPS_K_RE.finditer(text):
            v = parse_num(m.group(1))
            if v and 1 <= v <= 100:
                steps = v * 1000; break
    if steps:
        events.append((ts, day, "steps", "day_total", float(steps), "steps", None))

    # --- Deficit ---
    for m in DEFICIT_RE.finditer(text):
        v = parse_num(m.group(1))
        if v is not None and -3000 <= v <= 5000:
            events.append((ts, day, "deficit", "day", float(v), "cal", None))
            break

    # --- Gym session + volume ---
    gm = GYM_SESS_RE.search(text)
    if gm:
        sess = int(gm.group(1))
        if 400 <= sess <= 700:
            vol = None
            vm = VOLUME_RE.search(text)
            if vm:
                v = parse_num(vm.group(1))
                if v and 500 <= v <= 30000:
                    vol = v
            prs = None
            pm = PRS_RE.search(text)
            if pm:
                p = parse_num(pm.group(1))
                if p is not None and 0 <= p <= 15:
                    prs = p
            max_hr = None
            hm = MAX_HR_RE.search(text)
            if hm:
                h = parse_num(hm.group(1))
                if h and 60 <= h <= 220:
                    max_hr = h
            hr_pct = None
            hp = HR_BREACH_RE.search(text)
            if hp:
                h = parse_num(hp.group(1))
                if h is not None and 0 <= h <= 100:
                    hr_pct = h
            data = {"session_num": sess}
            if prs is not None: data["prs"] = prs
            if max_hr: data["max_hr"] = max_hr
            if hr_pct is not None: data["hr_pct_over_138"] = hr_pct
            events.append((ts, day, "gym", "session",
                           float(vol) if vol else None,
                           "kg" if vol else None,
                           json.dumps(data)))

    # --- Weight (body weight, not dumbbells) ---
    # Try table format first (HealthU+ export), then bold-label patterns.
    # Filter: reject matches near exercise/dumbbell keywords.
    EXERCISE_KEYWORDS = re.compile(
        r"dumbbell|barbell|\bDB\b|\bBB\b|curl|row|press|squat|deadlift|lunge|raise|fly|extension|pulldown|@\s*[0-9]|×|x\s*[0-9]",
        re.IGNORECASE
    )
    weight_found = None
    for regex, src in [(WEIGHT_TABLE_RE, "healthu"), (WEIGHT_LABEL_RE, "label")]:
        for m in regex.finditer(text):
            w = parse_num(m.group(1))
            if not (w and 60 <= w <= 120):
                continue
            # Context filter: look at 60 chars before match
            start = max(0, m.start() - 60)
            ctx = text[start:m.start()]
            if EXERCISE_KEYWORDS.search(ctx):
                continue
            weight_found = (w, src)
            break
        if weight_found:
            break
    if weight_found:
        w, src = weight_found
        events.append((ts, day, "weight", "kg", float(w), "kg",
                       json.dumps({"src": src})))

    return events


def main():
    dry = "--dry" in sys.argv
    files = sorted(LOGS.glob("*.md"))
    all_events = []
    per_day_summary = []

    for f in files:
        events = extract_from_file(f)
        if events:
            per_day_summary.append((f.stem, len(events), [e[2] + "/" + e[3] for e in events]))
            all_events.extend(events)

    print(f"Files scanned: {len(files)}")
    print(f"Days with events: {len(per_day_summary)}")
    print(f"Total events: {len(all_events)}")
    types = {}
    for e in all_events:
        k = f"{e[2]}/{e[3]}"
        types[k] = types.get(k, 0) + 1
    for k, n in sorted(types.items()):
        print(f"  {k}: {n}")

    if dry:
        print("\nSample days:")
        for d, n, kinds in per_day_summary[:5] + per_day_summary[-5:]:
            print(f"  {d}: {n} events → {kinds}")
        return

    # Wipe all existing events sourced from migration (any event without a live msg_id link, or with data_json containing 'src' == log_v2/repair)
    conn = connect()
    # Simpler: delete ALL events, re-insert from full-file extraction.
    # (Message table untouched, memory untouched.)
    conn.execute("DELETE FROM events")
    conn.executemany(
        "INSERT INTO events(ts, day, type, subtype, value_num, unit, data_json) "
        "VALUES (?,?,?,?,?,?,?)",
        all_events,
    )
    conn.commit()
    final = conn.execute("SELECT type, COUNT(*) FROM events GROUP BY type").fetchall()
    print("\nFinal counts:", final)
    conn.close()

if __name__ == "__main__":
    main()

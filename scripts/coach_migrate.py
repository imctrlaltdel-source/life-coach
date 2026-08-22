"""One-time migration: logs/*.md + memory/*.md + .remember/* → coach.db

Idempotent-ish: creates a synthetic 'migration' session, tags migrated msgs so re-runs skip.
"""
import re, json, os, sys
from pathlib import Path
from datetime import datetime, date
from coach_db import connect, now_iso
from coach_log import log_msg, log_event, upsert_memory, start_session

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
# Termux-specific Claude Code memory dir from the original migration (2026-08-15 on-device).
# Not portable — only meaningful if this script is ever re-run from that same phone.
MEM  = Path("/data/data/com.termux/files/home/.claude/projects/-storage-emulated-0-Documents-claude-life-coach/memory")
REMEM = ROOT / ".remember"

MSG_HEADER_RE = re.compile(r"^##\s+\[(\d{1,2}):(\d{2})\s*IST\]\s+—\s+Message\s+#?(\d+)?\s*—?\s*(.*)$")
PJ_SAID_RE = re.compile(r"^\*\*PJ said:\*\*\s*(.*)$", re.MULTILINE | re.DOTALL)
CAL_RE = re.compile(r"([0-9,]+)\s*cal", re.IGNORECASE)
CARB_RE = re.compile(r"([0-9]+)\s*g\s*carb", re.IGNORECASE)
STEPS_RE = re.compile(r"([0-9,]+)\s*(?:steps|k steps)", re.IGNORECASE)
GYM_RE = re.compile(r"gym\s*#?(\d+)?", re.IGNORECASE)
VOLUME_RE = re.compile(r"([0-9,]+)\s*kg\s*(?:volume|Volume)")
DEFICIT_RE = re.compile(r"[Dd]eficit[:\s]+([+-]?[0-9,]+)")

def parse_int(s):
    if not s:
        return None
    cleaned = s.replace(",", "").strip()
    if not cleaned or not cleaned.lstrip("+-").isdigit():
        return None
    return int(cleaned)

def migrate_logs(session_id):
    files = sorted(LOGS.glob("*.md"))
    n_msgs = n_events = 0
    for f in files:
        day = f.stem  # YYYY-MM-DD
        try:
            date.fromisoformat(day)
        except ValueError:
            continue
        text = f.read_text(errors="ignore")

        # Split by message headers
        blocks = re.split(r"^##\s+", text, flags=re.MULTILINE)
        for block in blocks[1:]:
            block = "## " + block
            m = MSG_HEADER_RE.search(block.split("\n", 1)[0])
            if m:
                hh, mm, mnum, title = m.groups()
                ts = f"{day}T{int(hh):02d}:{int(mm):02d}:00"
            else:
                # Not a message block — skip DAY SUMMARY etc for msgs but still scan for events
                ts = f"{day}T23:59:00"
                title = block.split("\n", 1)[0].replace("#", "").strip()

            # PJ said → user message
            pj = PJ_SAID_RE.search(block)
            if pj:
                content = pj.group(1).strip()[:4000]
                mid = log_msg("user", f"[migrated {day}] {content}", session_id)
                n_msgs += 1
            else:
                mid = log_msg("coach", f"[migrated {day} {title}] {block[:3500]}", session_id)
                n_msgs += 1

            # Extract structured events from block
            for m2 in CAL_RE.finditer(block):
                v = parse_int(m2.group(1))
                if v and 100 < v < 5000:  # sanity — daily cal total
                    log_event("meal", "day_total", v, "cal",
                              {"raw": m2.group(0)}, mid, ts); n_events += 1
                    break
            for m2 in CARB_RE.finditer(block):
                v = parse_int(m2.group(1))
                if v and 0 < v < 500:
                    log_event("meal", "carbs", v, "g", None, mid, ts); n_events += 1
                    break
            for m2 in STEPS_RE.finditer(block):
                raw = m2.group(1).replace(",", "").strip()
                if not raw.isdigit():
                    continue
                v = int(raw)
                if "k" in m2.group(0).lower():
                    v *= 1000
                if 100 < v < 100000:
                    log_event("steps", "day_total", v, "steps", None, mid, ts); n_events += 1
                    break
            gm = GYM_RE.search(block)
            if gm and gm.group(1):
                sess_num = int(gm.group(1))
                if 400 < sess_num < 700:
                    vol = None
                    vm = VOLUME_RE.search(block)
                    if vm: vol = parse_int(vm.group(1))
                    log_event("gym", "session", vol, "kg",
                              {"session_num": sess_num, "title": title}, mid, ts); n_events += 1
            dm = DEFICIT_RE.search(block)
            if dm:
                v = parse_int(dm.group(1).replace("+", ""))
                if v is not None and -3000 < v < 5000:
                    log_event("deficit", "day", v, "cal", None, mid, ts); n_events += 1

    return n_msgs, n_events

def migrate_memory():
    if not MEM.exists():
        return 0
    n = 0
    for f in MEM.glob("*.md"):
        if f.name == "MEMORY.md":
            continue
        text = f.read_text(errors="ignore")
        # Parse frontmatter
        kind = "reference"
        key = f.stem
        if text.startswith("---"):
            fm_end = text.find("---", 3)
            if fm_end > 0:
                fm = text[3:fm_end]
                body = text[fm_end+3:].strip()
                km = re.search(r"^type:\s*(\w+)", fm, re.MULTILINE)
                nm = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
                if km: kind = km.group(1).strip()
                if nm: key = nm.group(1).strip()[:80]
            else:
                body = text
        else:
            body = text
        upsert_memory(kind, key, body[:8000])
        n += 1
    return n

def migrate_remember():
    if not REMEM.exists():
        return 0
    n = 0
    for f in REMEM.glob("*.md"):
        if f.name in ("remember.md",):
            continue
        text = f.read_text(errors="ignore")[:4000]
        upsert_memory("reference", f"remember_{f.stem}", text)
        n += 1
    return n

def archive_originals():
    """Move originals to _archive/ (safe — reversible)."""
    arch = ROOT / "_archive_pre_db"
    arch.mkdir(exist_ok=True)
    moved = 0
    for src, name in [(LOGS, "logs"), (REMEM, "remember"), (MEM, "memory")]:
        if src.exists():
            dst = arch / name
            if not dst.exists():
                import shutil
                shutil.copytree(src, dst)
                moved += 1
    return moved

def main():
    dry = "--dry" in sys.argv
    archive = "--archive" in sys.argv

    # Check if migration already ran
    conn = connect()
    existing = conn.execute("SELECT COUNT(*) AS n FROM messages WHERE content LIKE '[migrated%'").fetchone()["n"]
    conn.close()
    if existing > 0 and not dry:
        print(f"⚠ Already migrated {existing} messages. Re-run with --force to add more.")
        if "--force" not in sys.argv:
            return

    if dry:
        print("DRY RUN — counts only")
        print(f"  log files: {len(list(LOGS.glob('*.md')))}")
        print(f"  memory files: {len(list(MEM.glob('*.md'))) if MEM.exists() else 0}")
        print(f"  remember files: {len(list(REMEM.glob('*.md'))) if REMEM.exists() else 0}")
        return

    sid = start_session("migration_pre_db")
    print(f"Migration session id: {sid}")

    n_msg, n_ev = migrate_logs(sid)
    print(f"Logs migrated: {n_msg} messages, {n_ev} events")

    n_mem = migrate_memory()
    print(f"Memory files migrated: {n_mem}")

    n_rem = migrate_remember()
    print(f"Remember snapshots migrated: {n_rem}")

    if archive:
        n_arch = archive_originals()
        print(f"Originals archived to _archive_pre_db/ ({n_arch} dirs)")

    print("\nDone.")

if __name__ == "__main__":
    main()

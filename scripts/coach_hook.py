#!/usr/bin/env python3
"""Claude Code hooks for the life-coach project.

  coach_hook.py open   UserPromptSubmit: pull sync (throttled), clock, DB context, log PJ's message,
                       print it all as context for the model.
  coach_hook.py close  Stop: log Coach's reply, refresh the DB snapshots of coaching-plan.md and
                       FABLE_PRIMER.md when they changed, push in the background (throttled).

Never blocks a message: any failure is written to .coach_hook/errors.log and the hook exits 0.
Set COACH_NO_SYNC=1 to skip all git work (used by tests).
"""
import hashlib, json, os, re, subprocess, sys, time, traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
STATE = ROOT / ".coach_hook"
STATE.mkdir(exist_ok=True)
PULL_EVERY, PUSH_EVERY = 600, 900          # seconds
NO_SYNC = bool(os.environ.get("COACH_NO_SYNC")) or not (ROOT / ".git").exists()
DOCS = [("doc_coaching_plan", "coaching-plan.md", "Coaching plan (the operating plan: training, diet targets, supplements, meds)"),
        ("doc_fable_primer", "FABLE_PRIMER.md", "Fable primer (the background briefing: history, patterns, deep-dive questions)")]

CHECKLIST = """REPLY CHECKLIST (from CLAUDE.md; follow it every time you coach):
1. PJ in pain, ill or exhausted: human reply only. No scorecard, tracker, numbers or Book Lens.
2. Otherwise: fit the time of day, at most 3 actions and 1 question.
3. Limits: protein 75 g/day (20 g/meal), carbs 120 g/day, dinner carbs up to 12 g, HR 138, never Kapalabhati, Bhastrika or Kumbhaka.
4. Meal in chat: look for a diary_auto row in today's events first, then estimate calories (+20% home, +30% restaurant; meal.py is out of service), then log the meal with --ts = time eaten.
5. End with the scorecard, the Week Deficit Tracker (Sun-Sat), and one Book Lens from the library only (Atomic Habits, Can't Hurt Me, Body Keeps the Score, Ikigai, Power of Now, Kashmir Shaivism, Why We Sleep, Good to Great){lens}."""


def log_err(where):
    with open(STATE / "errors.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} {where}\n{traceback.format_exc()}\n")


def stamp_age(name):
    p = STATE / name
    return time.time() - p.stat().st_mtime if p.exists() else 1e9


def touch(name):
    (STATE / name).write_text(str(time.time()))


def run(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)


def read_stdin():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def last_text_of_assistant(transcript_path):
    """Final reply = text blocks of the last assistant entry that has any."""
    last = None
    with open(transcript_path, errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") != "assistant":
                continue
            content = (d.get("message") or {}).get("content")
            if isinstance(content, list):
                txt = "\n".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
                if txt:
                    last = (d.get("uuid") or d.get("message", {}).get("id") or str(len(txt)), txt)
    return last


def do_open():
    data = read_stdin()
    prompt = (data.get("prompt") or "").strip()
    out = []
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    pull_note = "sync skipped (no git here)" if NO_SYNC else ""
    if not NO_SYNC:
        age = stamp_age("last_pull")
        if age < PULL_EVERY:
            pull_note = f"sync pulled {int(age // 60)} min ago"
        else:
            try:
                r = run(["bash", str(ROOT / "scripts/sync.sh"), "pull"], 25)
                if r.returncode == 0:
                    touch("last_pull")
                    pull_note = "sync pulled just now"
                else:
                    pull_note = "SYNC PROBLEM. Tell PJ before anything else and do not guess a fix:\n" + (r.stdout + r.stderr)[:600]
            except Exception as e:
                pull_note = f"SYNC PROBLEM ({e}). Tell PJ."
    try:
        ctx = run(["bash", str(ROOT / "scripts/ctx.sh")], 20).stdout.strip()[:5000]
    except Exception as e:
        ctx = f"(ctx.sh failed: {e}. Run it yourself.)"
    logged = ""
    if prompt and not prompt.startswith("/"):
        try:
            from coach_log import log_msg
            log_msg("user", prompt[:20000])
            logged = "PJ's message is already logged."
        except Exception:
            log_err("log user")
            logged = "LOGGING FAILED. Run coach_log.py msg user yourself and tell PJ."
    lens = ""
    try:
        from coach_db import connect
        c = connect()
        row = c.execute("SELECT content FROM messages WHERE role='coach' AND content LIKE '%📖%' ORDER BY id DESC LIMIT 1").fetchone()
        c.close()
        m = row and re.search(r"📖\s*\*{0,2}([^*\n]+?)\*{0,2}\s*(?:\n|$)", row["content"])
        if m:
            lens = f" (last time: {m.group(1).strip()})"
    except Exception:
        log_err("lens")
    out.append(f"COACH CONTEXT, loaded by the project hook. Do not repeat these steps.\nNow: {now.strftime('%A %d %B %Y, %H:%M')} IST. {pull_note}. {logged}\n\n{ctx}")
    try:
        last = float((ROOT / "logs/.deep-review-last").read_text().strip())
        days = int((time.time() - last) // 86400)
        if days >= 7:
            out.append(f"DEEP REVIEW OVERDUE: last done {days} days ago. Offer it at a natural moment (run or snooze). Never force it.")
    except Exception:
        pass
    out.append(CHECKLIST.format(lens=lens))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n\n".join(out)}}))


def do_close():
    data = read_stdin()
    text = data.get("last_assistant_message")
    uid = None
    if not text and data.get("transcript_path"):
        got = last_text_of_assistant(data["transcript_path"])
        if got:
            uid, text = got
    if text:
        tp = data.get("transcript_path")
        size = os.path.getsize(tp) if tp and os.path.exists(tp) else 0
        key = hashlib.md5(f"{data.get('session_id')}|{uid}|{size}|{text[:80]}".encode()).hexdigest()
        marker = STATE / "last_logged"
        if not marker.exists() or marker.read_text() != key:
            try:
                from coach_log import log_msg
                log_msg("coach", text[:20000])
                marker.write_text(key)
            except Exception:
                log_err("log coach")
    try:
        from coach_log import upsert_memory
        for key, fn, label in DOCS:
            p = ROOT / fn
            if not p.exists():
                continue
            h = hashlib.md5(p.read_bytes()).hexdigest()
            hp = STATE / f"hash_{key}"
            if not hp.exists() or hp.read_text() != h:
                upsert_memory("reference", key, f"SNAPSHOT of {fn} taken {datetime.now().strftime('%Y-%m-%d %H:%M')}. The file is canonical; this copy refreshes itself when the file changes.\n{label}\n\n" + p.read_text())
                hp.write_text(h)
    except Exception:
        log_err("snapshots")
    if not NO_SYNC and stamp_age("last_push") > PUSH_EVERY:
        try:
            touch("last_push")
            with open(STATE / "push.log", "a") as lf:
                subprocess.Popen(["bash", str(ROOT / "scripts/sync.sh"), "push"], cwd=ROOT, stdout=lf, stderr=lf, start_new_session=True)
        except Exception:
            log_err("push")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        {"open": do_open, "close": do_close}[mode]()
    except Exception:
        log_err(mode)
        if mode == "open":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "COACH HOOK FAILED. Run `bash scripts/ctx.sh` and `date` yourself, log the message by hand, and tell PJ the hook failed."}}))
    sys.exit(0)

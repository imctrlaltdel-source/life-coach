"""Write helpers — insert messages, events, memory.

Usage from CLI:
  python3 scripts/coach_log.py msg user "text here"
  python3 scripts/coach_log.py msg coach "response here"
  python3 scripts/coach_log.py event gym pull --num 10810 --unit kg --data '{"prs":3}'
  python3 scripts/coach_log.py mem feedback likes_moong "PJ prefers moong dal cheela over besan"

Usage from Python:
  from coach_log import log_msg, log_event, upsert_memory
"""
import sqlite3, json, sys, argparse, subprocess, os
from pathlib import Path
from coach_db import connect, now_iso, today

CTX_SH = str(Path(__file__).resolve().parent / "ctx.sh")

def _refresh_cache():
    """Fire-and-forget cache refresh so ctx.sh cache stays fresh."""
    try:
        subprocess.Popen(
            ["bash", CTX_SH, "refresh"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass

def log_msg(role: str, content: str, session_id: int | None = None, tokens: int | None = None) -> int:
    conn = connect()
    cur = conn.execute(
        "INSERT INTO messages(ts, role, content, session_id, tokens) VALUES (?,?,?,?,?)",
        (now_iso(), role, content, session_id, tokens),
    )
    mid = cur.lastrowid
    conn.commit()
    conn.close()
    _refresh_cache()
    return mid

def log_event(type_: str, subtype: str | None = None, value_num: float | None = None,
              unit: str | None = None, data: dict | None = None, msg_id: int | None = None,
              ts: str | None = None) -> int:
    ts = ts or now_iso()
    day = ts[:10]
    conn = connect()
    cur = conn.execute(
        "INSERT INTO events(msg_id, ts, day, type, subtype, value_num, unit, data_json) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (msg_id, ts, day, type_, subtype, value_num, unit, json.dumps(data) if data else None),
    )
    eid = cur.lastrowid
    conn.commit()
    conn.close()
    _refresh_cache()
    return eid

def upsert_memory(kind: str, key: str, value: str, source_msg: int | None = None) -> int:
    conn = connect()
    cur = conn.execute(
        "INSERT INTO memory(kind, key, value, updated_ts, source_msg) VALUES (?,?,?,?,?) "
        "ON CONFLICT(kind, key) DO UPDATE SET value=excluded.value, updated_ts=excluded.updated_ts, "
        "source_msg=COALESCE(excluded.source_msg, memory.source_msg)",
        (kind, key, value, now_iso(), source_msg),
    )
    conn.commit()
    # get id
    row = conn.execute("SELECT id FROM memory WHERE kind=? AND key=?", (kind, key)).fetchone()
    conn.close()
    _refresh_cache()
    return row["id"] if row else cur.lastrowid

def start_session(note: str | None = None) -> int:
    conn = connect()
    cur = conn.execute("INSERT INTO sessions(started_ts, note) VALUES (?,?)", (now_iso(), note))
    sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid

def end_session(session_id: int) -> None:
    conn = connect()
    conn.execute("UPDATE sessions SET ended_ts=? WHERE id=?", (now_iso(), session_id))
    conn.commit()
    conn.close()

def _cli():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("msg")
    m.add_argument("role", choices=["user", "coach"])
    m.add_argument("content")
    m.add_argument("--session", type=int)

    e = sub.add_parser("event")
    e.add_argument("type")
    e.add_argument("subtype", nargs="?")
    e.add_argument("--num", type=float)
    e.add_argument("--unit")
    e.add_argument("--data")
    e.add_argument("--msg", type=int)
    e.add_argument("--ts")

    mem = sub.add_parser("mem")
    mem.add_argument("kind", choices=["profile", "feedback", "project", "reference"])
    mem.add_argument("key")
    mem.add_argument("value")
    mem.add_argument("--src", type=int)

    ss = sub.add_parser("session-start")
    ss.add_argument("--note")

    se = sub.add_parser("session-end")
    se.add_argument("id", type=int)

    args = ap.parse_args()

    if args.cmd == "msg":
        print(log_msg(args.role, args.content, args.session))
    elif args.cmd == "event":
        data = json.loads(args.data) if args.data else None
        print(log_event(args.type, args.subtype, args.num, args.unit, data, args.msg, args.ts))
    elif args.cmd == "mem":
        print(upsert_memory(args.kind, args.key, args.value, args.src))
    elif args.cmd == "session-start":
        print(start_session(args.note))
    elif args.cmd == "session-end":
        end_session(args.id)
        print("ok")

if __name__ == "__main__":
    _cli()

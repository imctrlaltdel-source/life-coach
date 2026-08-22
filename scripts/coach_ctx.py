"""Context loader — dump everything Coach needs to open a session.

Run at the start of every response:
    python3 scripts/coach_ctx.py            # full context
    python3 scripts/coach_ctx.py --search "knee pain"
    python3 scripts/coach_ctx.py --days 14
"""
import sys, argparse, json
from datetime import date, timedelta, datetime
from coach_db import connect, today

BMR = 1635  # PJ baseline
STEP_CAL_PER_1000 = 15

def _week_bounds(d: date):
    """Week = Sunday to Saturday (per CLAUDE.md)."""
    days_since_sun = (d.weekday() + 1) % 7
    start = d - timedelta(days=days_since_sun)
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()

def load_context(n_msgs: int = 20, days_events: int = 3):
    conn = connect()
    ctx = {}

    # Latest messages (chronological)
    rows = conn.execute(
        "SELECT ts, role, content FROM messages ORDER BY ts DESC LIMIT ?", (n_msgs,)
    ).fetchall()
    ctx["recent_messages"] = [dict(r) for r in reversed(rows)]

    # Today's events
    t = today()
    rows = conn.execute(
        "SELECT ts, type, subtype, value_num, unit, data_json FROM events "
        "WHERE day=? ORDER BY ts", (t,)
    ).fetchall()
    ctx["today_events"] = [dict(r) for r in rows]

    # Last N days of key event totals per day
    since = (date.today() - timedelta(days=days_events)).isoformat()
    rows = conn.execute(
        "SELECT day, type, SUM(value_num) AS total, COUNT(*) AS n "
        "FROM events WHERE day>=? GROUP BY day, type ORDER BY day DESC, type",
        (since,),
    ).fetchall()
    ctx["recent_daily_totals"] = [dict(r) for r in rows]

    # Week deficit tracker
    ws, we = _week_bounds(date.today())
    rows = conn.execute(
        "SELECT day, type, SUM(value_num) AS total FROM events "
        "WHERE day BETWEEN ? AND ? AND type IN ('meal','steps','deficit') "
        "GROUP BY day, type", (ws, we),
    ).fetchall()
    by_day = {}
    for r in rows:
        by_day.setdefault(r["day"], {})[r["type"]] = r["total"] or 0
    week_deficit = 0
    for day, m in by_day.items():
        cals = m.get("meal", 0)
        steps = m.get("steps", 0)
        tdee = BMR + (steps * STEP_CAL_PER_1000 / 1000)
        if cals:
            week_deficit += (tdee - cals)
    ctx["week"] = {
        "start": ws, "end": we, "banked_deficit_cal": round(week_deficit),
        "target": 7000, "days_left": (date.fromisoformat(we) - date.today()).days,
    }

    # Memory (profile + active feedback/project)
    rows = conn.execute(
        "SELECT kind, key, value, updated_ts FROM memory ORDER BY kind, key"
    ).fetchall()
    ctx["memory"] = [dict(r) for r in rows]

    # Active flags (memory kind=flag OR events type=flag active)
    rows = conn.execute(
        "SELECT ts, subtype, data_json FROM events WHERE type='flag' ORDER BY ts DESC LIMIT 10"
    ).fetchall()
    ctx["flags"] = [dict(r) for r in rows]

    conn.close()
    return ctx

def search(q: str, limit: int = 20):
    conn = connect()
    rows = conn.execute(
        "SELECT m.ts, m.role, snippet(messages_fts, 0, '[', ']', '…', 12) AS snip "
        "FROM messages_fts JOIN messages m ON m.id=messages_fts.rowid "
        "WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?", (q, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fmt_human(ctx):
    out = []
    w = ctx["week"]
    out.append(f"📊 Week ({w['start']} → {w['end']}): banked {w['banked_deficit_cal']} cal / 7000 target · {w['days_left']} days left")
    out.append(f"\n📅 Today's events ({today()}): {len(ctx['today_events'])}")
    for e in ctx["today_events"]:
        v = f" {e['value_num']}{e['unit'] or ''}" if e["value_num"] else ""
        out.append(f"  {e['ts'][11:16]} {e['type']}/{e['subtype'] or '-'}{v}")
    if ctx["flags"]:
        out.append(f"\n🚩 Active flags:")
        for f in ctx["flags"]:
            out.append(f"  {f['ts'][:10]} {f['subtype']}")
    out.append(f"\n💬 Recent messages ({len(ctx['recent_messages'])}):")
    for m in ctx["recent_messages"][-10:]:
        preview = m["content"][:120].replace("\n", " ")
        out.append(f"  [{m['ts'][11:16]}] {m['role']}: {preview}")
    out.append(f"\n🧠 Memory: {len(ctx['memory'])} entries")
    kinds = {}
    for m in ctx["memory"]:
        kinds.setdefault(m["kind"], 0)
        kinds[m["kind"]] += 1
    for k, n in kinds.items():
        out.append(f"  {k}: {n}")
    return "\n".join(out)

def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", "-s")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--msgs", type=int, default=20)
    ap.add_argument("--days", type=int, default=3)
    args = ap.parse_args()

    if args.search:
        hits = search(args.search)
        if args.json:
            print(json.dumps(hits, indent=2))
        else:
            for h in hits:
                print(f"[{h['ts']}] {h['role']}: {h['snip']}")
        return

    ctx = load_context(args.msgs, args.days)
    if args.json:
        print(json.dumps(ctx, indent=2, default=str))
    else:
        print(fmt_human(ctx))

if __name__ == "__main__":
    _cli()

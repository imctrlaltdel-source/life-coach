#!/usr/bin/env bash
# Fast context loader — pure sqlite3 CLI, no Python startup.
# Usage: ./ctx.sh                → full context (~30ms)
#        ./ctx.sh search "term"  → FTS5 search
#        ./ctx.sh cache          → read pre-rendered cache (~5ms)
#        ./ctx.sh refresh        → rebuild cache
#
# Falls back to `python3 coach_ctx.py` when the sqlite3 CLI binary isn't
# installed (e.g. a laptop/server without it) — same DB, slower (~150-200ms
# vs ~20-30ms) but no system dependency required.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
DB="$ROOT/db/coach.db"
CACHE="$ROOT/db/ctx_cache.txt"
BMR=1635
STEP_CAL=15

if ! command -v sqlite3 >/dev/null 2>&1; then
  case "${1:-cache}" in
    search) exec python3 "$SCRIPT_DIR/coach_ctx.py" --search "$2" ;;
    *)      exec python3 "$SCRIPT_DIR/coach_ctx.py" ;;
  esac
fi

# Fast path: cache read, no date/stat calls at top
if [ "${1:-cache}" = "cache" ]; then
  [ -f "$CACHE" ] && exec cat "$CACHE"
fi

# Only compute dates for full/refresh path
TODAY=$(date +%Y-%m-%d)
DOW=$(date +%w)
WSTART=$(date -d "$TODAY -$DOW days" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
WEND=$(date -d "$WSTART +6 days" +%Y-%m-%d 2>/dev/null || echo "$WSTART")

_full() {
  sqlite3 "$DB" <<SQL
.mode list
.separator ""
.headers off

SELECT '📊 Week ($WSTART → $WEND)';
SELECT '  Banked cal deficit: ' || COALESCE((
    SELECT ROUND(SUM(
      ($BMR + COALESCE(steps,0)*$STEP_CAL/1000.0) - COALESCE(cals,0)
    ))
    FROM (
      SELECT day,
        SUM(CASE WHEN type='meal' AND subtype='day_total' THEN value_num END) AS cals,
        SUM(CASE WHEN type='steps' THEN value_num END) AS steps
      FROM events WHERE day BETWEEN '$WSTART' AND '$WEND' GROUP BY day
    ) WHERE cals IS NOT NULL
  ), 0) || ' / 7000 target';

SELECT '';
SELECT '📅 Today (' || '$TODAY' || '):';
SELECT '  ' || substr(ts,12,5) || ' ' || type || '/' || COALESCE(subtype,'-') ||
       CASE WHEN value_num IS NOT NULL THEN ' ' || value_num || COALESCE(unit,'') ELSE '' END
FROM events WHERE day='$TODAY' ORDER BY ts;

SELECT '';
SELECT '🚩 Active flags:';
SELECT '  ' || substr(ts,1,10) || ' ' || subtype
FROM events WHERE type='flag' ORDER BY ts DESC LIMIT 5;

SELECT '';
SELECT '💬 Last 15 messages:';
SELECT '  [' || substr(ts,12,5) || '] ' || role || ': ' ||
       substr(replace(replace(content, char(10), ' '), '  ', ' '), 1, 110)
FROM messages ORDER BY ts DESC LIMIT 15;

SELECT '';
SELECT '🧠 Memory (' || COUNT(*) || ' entries):' FROM memory;
SELECT '  ' || kind || ': ' || COUNT(*) FROM memory GROUP BY kind;
SQL
}

_search() {
  local q="$1"
  sqlite3 "$DB" <<SQL
.mode list
.separator ' | '
SELECT substr(m.ts,1,16), m.role, snippet(messages_fts, 0, '[', ']', '…', 10)
FROM messages_fts JOIN messages m ON m.id=messages_fts.rowid
WHERE messages_fts MATCH '$q' ORDER BY rank LIMIT 20;
SQL
}

_refresh() {
  _full > "$CACHE"
  echo "cache refreshed: $CACHE"
}

case "${1:-cache}" in
  refresh) _refresh ;;
  search)  _search "$2" ;;
  full|*)  _full ;;
esac

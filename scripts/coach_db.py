"""Coach memory DB — single source of truth.

DB path: db/coach.db
Tables: messages, events, memory, sessions
FTS5:   messages_fts, events_fts, memory_fts
"""
import sqlite3, os, json, time
from datetime import datetime, timedelta, date
from pathlib import Path

DB_PATH = Path("/storage/emulated/0/Documents/claude/life-coach/db/coach.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_ts   TEXT NOT NULL,
    ended_ts     TEXT,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,           -- ISO8601 IST
    role         TEXT NOT NULL,           -- 'user' | 'coach'
    content      TEXT NOT NULL,
    session_id   INTEGER REFERENCES sessions(id),
    tokens       INTEGER
);
CREATE INDEX IF NOT EXISTS idx_msg_ts    ON messages(ts DESC);
CREATE INDEX IF NOT EXISTS idx_msg_sess  ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_msg_role  ON messages(role, ts DESC);

-- Structured events extracted from messages
-- type: gym | meal | habit | weight | mood | steps | kriya | weed | parents | sleep | flag
-- subtype: e.g. meal.breakfast, gym.pull, habit.veg_first
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_id       INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    ts           TEXT NOT NULL,
    day          TEXT NOT NULL,           -- YYYY-MM-DD for fast day filter
    type         TEXT NOT NULL,
    subtype      TEXT,
    value_num    REAL,                    -- primary numeric (carbs g, cal, kg, steps...)
    unit         TEXT,
    data_json    TEXT                     -- full structured payload
);
CREATE INDEX IF NOT EXISTS idx_ev_ts      ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_ev_day     ON events(day, type);
CREATE INDEX IF NOT EXISTS idx_ev_type    ON events(type, ts DESC);

-- Long-lived facts (profile, feedback, project state, references)
-- kind: profile | feedback | project | reference
CREATE TABLE IF NOT EXISTS memory (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL,
    key          TEXT NOT NULL,
    value        TEXT NOT NULL,
    updated_ts   TEXT NOT NULL,
    source_msg   INTEGER REFERENCES messages(id),
    UNIQUE(kind, key)
);
CREATE INDEX IF NOT EXISTS idx_mem_kind ON memory(kind);

-- FTS5 for fast full-text search across content
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content, content='messages', content_rowid='id', tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    value, content='memory', content_rowid='id', tokenize='porter unicode61'
);

-- Sync triggers so FTS stays in step with base tables
CREATE TRIGGER IF NOT EXISTS msg_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS msg_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;
CREATE TRIGGER IF NOT EXISTS msg_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES ('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts(rowid, value) VALUES (new.id, new.value);
END;
CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, value) VALUES ('delete', old.id, old.value);
END;
CREATE TRIGGER IF NOT EXISTS mem_au AFTER UPDATE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, value) VALUES ('delete', old.id, old.value);
    INSERT INTO memory_fts(rowid, value) VALUES (new.id, new.value);
END;
"""

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def now_iso():
    # IST assumed (Termux TZ)
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def today():
    return date.today().isoformat()

if __name__ == "__main__":
    conn = connect()
    print("DB ready at", DB_PATH)
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','index') ORDER BY name"):
        print(" ", row["name"])
    conn.close()

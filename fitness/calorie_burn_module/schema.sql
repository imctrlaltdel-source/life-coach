-- Calorie-Burn Progression module — schema for the life-coach bot's existing SQL DB.
-- Prefix table names with cb_ if you need to avoid collisions with existing tables.

CREATE TABLE IF NOT EXISTS cb_plan_config (
    plan_id                 TEXT PRIMARY KEY,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cadence                 TEXT DEFAULT 'alternate_day',
    total_sessions          INTEGER DEFAULT 90,
    block_size              INTEGER DEFAULT 5,
    target_multiplier       REAL DEFAULT 3.0,
    horizon_months          INTEGER DEFAULT 6,
    baseline_kcal_per_min   REAL,               -- set from avg of user's first 3 logged sessions
    current_session_index   INTEGER DEFAULT 0,
    last_completed_date     DATE,
    projected_target_date   DATE,               -- recomputed after every log, see spec Section E
    notes                   TEXT
);

CREATE TABLE IF NOT EXISTS cb_sessions_plan (
    session_index           INTEGER PRIMARY KEY,
    block                   INTEGER NOT NULL,
    phase                   TEXT NOT NULL,
    is_deload               BOOLEAN NOT NULL DEFAULT 0,
    session_type            TEXT NOT NULL,       -- RunWalkA/B/C, Calisthenics, Combined
    warmup                  TEXT,
    main_set                TEXT,
    cooldown                TEXT,
    total_min_approx        INTEGER,
    hr_cap_pct_max_hr       REAL,
    target_kcal_per_min     REAL,
    status                  TEXT DEFAULT 'scheduled'  -- scheduled/completed/skipped/replaced_by_makeup/repeated
);

CREATE TABLE IF NOT EXISTS cb_workout_logs (
    log_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_index           INTEGER REFERENCES cb_sessions_plan(session_index),
    logged_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    workout_date            DATE NOT NULL,
    duration_min            REAL,
    avg_hr                  INTEGER,
    max_hr                  INTEGER,
    calories_burned         REAL,
    resting_hr_that_morning INTEGER,
    sleep_score             INTEGER,
    rpe_1_to_10             INTEGER,
    notes                   TEXT,
    raw_watch_payload       TEXT   -- store the full raw input JSON verbatim, unmodified, every time
);

CREATE TABLE IF NOT EXISTS cb_disruption_events (
    event_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date              DATE NOT NULL,
    end_date                DATE,
    reason                  TEXT,          -- 'travel','illness','other'
    sessions_missed         INTEGER,
    resume_action           TEXT           -- what step-back rule was applied, see spec Section D
);

CREATE TABLE IF NOT EXISTS cb_party_events (
    event_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date              DATE NOT NULL,
    trailing_avg_kcal       REAL,          -- 7-session trailing avg at time of event
    target_makeup_kcal      REAL,          -- 3x trailing_avg_kcal
    makeup_session_index    INTEGER REFERENCES cb_sessions_plan(session_index),
    achieved_kcal           REAL,
    notes                   TEXT
);

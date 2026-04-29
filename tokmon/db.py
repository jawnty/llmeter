import sqlite3
import os
import threading
from . import config

_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,           -- 'claude' | 'codex'
    cwd             TEXT,
    project         TEXT,
    started_at      TEXT,                    -- ISO8601 UTC
    last_seen_at    TEXT,
    opening_prompt  TEXT,
    models          TEXT,                    -- comma-joined unique models
    is_sidechain    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS turns (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id            TEXT NOT NULL,
    source                TEXT NOT NULL,
    ts                    TEXT NOT NULL,     -- ISO8601 UTC
    hour_local            TEXT NOT NULL,     -- YYYY-MM-DD HH local
    day_local             TEXT NOT NULL,     -- YYYY-MM-DD local
    model                 TEXT,
    input_tokens          INTEGER DEFAULT 0,
    output_tokens         INTEGER DEFAULT 0,
    cache_read_tokens     INTEGER DEFAULT 0,
    cache_create_tokens   INTEGER DEFAULT 0,
    reasoning_tokens      INTEGER DEFAULT 0,
    total_tokens          INTEGER DEFAULT 0,
    cost_usd              REAL DEFAULT 0,
    raw_uuid              TEXT UNIQUE        -- dedup key
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_day     ON turns(day_local);
CREATE INDEX IF NOT EXISTS idx_turns_hour    ON turns(hour_local);
CREATE INDEX IF NOT EXISTS idx_turns_ts      ON turns(ts);

CREATE TABLE IF NOT EXISTS file_offsets (
    path        TEXT PRIMARY KEY,
    offset      INTEGER NOT NULL,
    mtime       REAL NOT NULL
);
"""


def connect():
    conn = sqlite3.connect(config.db_path(), timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init():
    os.makedirs(config.db_path().parent, exist_ok=True)
    with _LOCK, connect() as c:
        c.executescript(SCHEMA)


def upsert_session(conn, sess):
    conn.execute(
        """
        INSERT INTO sessions (id, source, cwd, project, started_at, last_seen_at,
                              opening_prompt, models, is_sidechain)
        VALUES (:id, :source, :cwd, :project, :started_at, :last_seen_at,
                :opening_prompt, :models, :is_sidechain)
        ON CONFLICT(id) DO UPDATE SET
            last_seen_at   = excluded.last_seen_at,
            opening_prompt = COALESCE(sessions.opening_prompt, excluded.opening_prompt),
            models         = excluded.models,
            project        = COALESCE(sessions.project, excluded.project),
            cwd            = COALESCE(sessions.cwd, excluded.cwd)
        """,
        sess,
    )


def insert_turn(conn, turn):
    try:
        conn.execute(
            """
            INSERT INTO turns (session_id, source, ts, hour_local, day_local, model,
                               input_tokens, output_tokens, cache_read_tokens,
                               cache_create_tokens, reasoning_tokens, total_tokens,
                               cost_usd, raw_uuid)
            VALUES (:session_id, :source, :ts, :hour_local, :day_local, :model,
                    :input_tokens, :output_tokens, :cache_read_tokens,
                    :cache_create_tokens, :reasoning_tokens, :total_tokens,
                    :cost_usd, :raw_uuid)
            """,
            turn,
        )
        return True
    except sqlite3.IntegrityError:
        return False  # duplicate raw_uuid


def get_offset(conn, path):
    row = conn.execute("SELECT offset, mtime FROM file_offsets WHERE path=?", (path,)).fetchone()
    return (row["offset"], row["mtime"]) if row else (0, 0.0)


def set_offset(conn, path, offset, mtime):
    conn.execute(
        """INSERT INTO file_offsets (path, offset, mtime) VALUES (?, ?, ?)
           ON CONFLICT(path) DO UPDATE SET offset=excluded.offset, mtime=excluded.mtime""",
        (path, offset, mtime),
    )

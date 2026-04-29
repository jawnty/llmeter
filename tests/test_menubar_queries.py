from llmeter import db
from llmeter.menubar import queries


def _seed(monkeypatch, tmp_path, rows, sessions=None):
    monkeypatch.setenv("LLMETER_DB_PATH", str(tmp_path / "llmeter.db"))
    db.init()
    sessions = sessions or [
        ("s-claude", "claude", "appmint"),
        ("s-codex", "codex", "llmeter"),
    ]
    with db.connect() as c:
        for sid, source, project in sessions:
            c.execute(
                """INSERT OR IGNORE INTO sessions
                   (id, source, cwd, project, started_at, last_seen_at,
                    opening_prompt, models, is_sidechain)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (sid, source, "/tmp", project, "2026-04-29T17:00:00Z",
                 "2026-04-29T17:00:00Z", "hi", source),
            )
        for i, r in enumerate(rows):
            db.insert_turn(c, {
                "session_id": r["session_id"],
                "source": r["source"],
                "ts": r["ts"],
                "hour_local": r["ts"][:13].replace("T", " "),
                "day_local": r["day"],
                "model": r.get("model", "claude-sonnet-4-6"),
                "input_tokens": r.get("input_tokens", 0),
                "output_tokens": r.get("output_tokens", 0),
                "cache_read_tokens": 0,
                "cache_create_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": r["total_tokens"],
                "cost_usd": r.get("cost_usd", 0.0),
                "raw_uuid": r.get("raw_uuid", f"uuid-{i}"),
            })


def test_snapshot_empty_db(tmp_path, monkeypatch):
    monkeypatch.setenv("LLMETER_DB_PATH", str(tmp_path / "empty.db"))
    db.init()
    snap = queries.snapshot(day="2026-04-29")
    assert snap.total_tokens == 0
    assert snap.claude_tokens == 0
    assert snap.codex_tokens == 0
    assert snap.cost_usd == 0.0
    assert snap.turns == 0
    assert snap.last_session is None
    assert snap.title() == "⚡ 0"


def test_snapshot_totals_and_split(tmp_path, monkeypatch):
    rows = [
        {"session_id": "s-claude", "source": "claude", "ts": "2026-04-29T17:00:00Z",
         "day": "2026-04-29", "total_tokens": 1000, "cost_usd": 0.10},
        {"session_id": "s-claude", "source": "claude", "ts": "2026-04-29T17:05:00Z",
         "day": "2026-04-29", "total_tokens": 2000, "cost_usd": 0.20},
        {"session_id": "s-codex", "source": "codex", "ts": "2026-04-29T18:00:00Z",
         "day": "2026-04-29", "total_tokens": 500, "cost_usd": 0.05},
        # different day, must be ignored:
        {"session_id": "s-claude", "source": "claude", "ts": "2026-04-28T10:00:00Z",
         "day": "2026-04-28", "total_tokens": 9999, "cost_usd": 9.99},
    ]
    _seed(monkeypatch, tmp_path, rows)

    snap = queries.snapshot(day="2026-04-29")
    assert snap.total_tokens == 3500
    assert snap.claude_tokens == 3000
    assert snap.codex_tokens == 500
    assert round(snap.cost_usd, 2) == 0.35
    assert snap.turns == 3


def test_snapshot_last_session_is_most_recent(tmp_path, monkeypatch):
    rows = [
        {"session_id": "s-claude", "source": "claude", "ts": "2026-04-29T17:00:00Z",
         "day": "2026-04-29", "total_tokens": 100},
        {"session_id": "s-codex", "source": "codex", "ts": "2026-04-29T19:00:00Z",
         "day": "2026-04-29", "total_tokens": 200},
        {"session_id": "s-codex", "source": "codex", "ts": "2026-04-29T19:05:00Z",
         "day": "2026-04-29", "total_tokens": 300},
    ]
    _seed(monkeypatch, tmp_path, rows)

    snap = queries.snapshot(day="2026-04-29")
    assert snap.last_session is not None
    assert snap.last_session["id"] == "s-codex"
    assert snap.last_session["turns"] == 2
    assert snap.last_session["total_tokens"] == 500


def test_short_tokens_formatting():
    assert queries._short_tokens(0) == "0"
    assert queries._short_tokens(950) == "950"
    assert queries._short_tokens(1500) == "1.5K"
    assert queries._short_tokens(2_300_000) == "2.3M"


def test_fmt_last_session_handles_none():
    assert queries.fmt_last_session(None) == "Last session: —"
    assert "appmint" in queries.fmt_last_session({
        "project": "appmint", "turns": 4, "total_tokens": 12_000, "source": "claude",
    })

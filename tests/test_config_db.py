from tokmon import config, db


def test_db_path_can_be_overridden(tmp_path, monkeypatch):
    target = tmp_path / "custom.db"
    monkeypatch.setenv("TOKMON_DB_PATH", str(target))

    assert config.db_path() == target

    db.init()
    with db.connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert {"sessions", "turns", "file_offsets"}.issubset(tables)


def test_insert_turn_dedupes_by_raw_uuid(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKMON_DB_PATH", str(tmp_path / "tokmon.db"))
    db.init()

    turn = {
        "session_id": "s1",
        "source": "claude",
        "ts": "2026-04-29T17:00:00Z",
        "hour_local": "2026-04-29 10",
        "day_local": "2026-04-29",
        "model": "claude-sonnet-4",
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_read_tokens": 0,
        "cache_create_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 30,
        "cost_usd": 0.00033,
        "raw_uuid": "claude:test",
    }

    with db.connect() as conn:
        assert db.insert_turn(conn, turn) is True
        assert db.insert_turn(conn, turn) is False


def test_invalid_port_falls_back(monkeypatch):
    monkeypatch.setenv("TOKMON_PORT", "oops")

    assert config.port() == 4001

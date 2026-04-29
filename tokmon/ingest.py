"""Ingest pipeline: walk log files, resume from offsets, parse, write to SQLite."""

import os
import glob
import asyncio
from . import db
from . import parser_claude
from . import parser_codex


CLAUDE_GLOB = os.path.expanduser("~/.claude/projects/**/*.jsonl")
CODEX_GLOB = os.path.expanduser("~/.codex/sessions/**/*.jsonl")


def _models_merge(existing: str, new: str) -> str:
    if not new:
        return existing or ""
    items = [m for m in (existing or "").split(",") if m]
    if new not in items:
        items.append(new)
    return ",".join(items)


def _apply_events(conn, events):
    new_turns = 0
    for kind, payload in events:
        if kind == "session_init":
            row = conn.execute(
                "SELECT models FROM sessions WHERE id=?", (payload["id"],)
            ).fetchone()
            existing_models = row["models"] if row else ""
            payload = dict(payload)
            payload["models"] = _models_merge(existing_models, payload.get("models") or "")
            db.upsert_session(conn, payload)
        elif kind == "turn":
            if db.insert_turn(conn, payload):
                new_turns += 1
                conn.execute(
                    "UPDATE sessions SET last_seen_at=? WHERE id=?",
                    (payload["ts"], payload["session_id"]),
                )
    return new_turns


def ingest_file(conn, path: str, source: str) -> int:
    """Read new bytes from path, parse, and persist. Returns number of new turn rows."""
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return 0
    offset, _ = db.get_offset(conn, path)
    # If file shrank (truncated/rotated), restart from 0
    if st.st_size < offset:
        offset = 0
    if st.st_size == offset:
        return 0

    new_turns = 0
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            buf = f.read()
            new_offset = offset + len(buf)
    except OSError:
        return 0

    # If file doesn't end on newline, leave the trailing partial line for next pass
    text = buf.decode("utf-8", errors="replace")
    if not text.endswith("\n"):
        last_nl = text.rfind("\n")
        if last_nl == -1:
            return 0  # no complete line yet
        consumed = last_nl + 1
        text = text[:consumed]
        new_offset = offset + len(text.encode("utf-8"))

    events = []
    for line in text.split("\n"):
        if not line:
            continue
        if source == "claude":
            events.extend(parser_claude.parse_line(line))
        else:
            events.extend(parser_codex.parse_line(line, path))

    if events:
        with conn:
            new_turns = _apply_events(conn, events)
    db.set_offset(conn, path, new_offset, st.st_mtime)
    return new_turns


def scan_all(conn):
    total_new = 0
    for path in glob.glob(CLAUDE_GLOB, recursive=True):
        total_new += ingest_file(conn, path, "claude")
    for path in glob.glob(CODEX_GLOB, recursive=True):
        total_new += ingest_file(conn, path, "codex")
    return total_new

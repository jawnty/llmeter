"""Runtime configuration for tokmon.

Defaults are intentionally local and zero-config, but every path/port that
matters can be overridden for packaging and tests.
"""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    return Path(os.environ.get("TOKMON_DATA_DIR", project_root() / "data")).expanduser()


def db_path() -> Path:
    return Path(os.environ.get("TOKMON_DB_PATH", data_dir() / "tokmon.db")).expanduser()


def host() -> str:
    return os.environ.get("TOKMON_HOST", "127.0.0.1")


def port() -> int:
    raw = os.environ.get("TOKMON_PORT", "4001")
    try:
        return int(raw)
    except ValueError:
        return 4001


def claude_glob() -> str:
    return os.path.expanduser(
        os.environ.get("TOKMON_CLAUDE_GLOB", "~/.claude/projects/**/*.jsonl")
    )


def codex_glob() -> str:
    return os.path.expanduser(
        os.environ.get("TOKMON_CODEX_GLOB", "~/.codex/sessions/**/*.jsonl")
    )

"""Read-only query helpers for the menu bar app.

These reuse the same SQLite connection plumbing as the dashboard via
`llmeter.db`. No SQL is duplicated outside this module — the dashboard's
own queries live in `llmeter.server` and answer different shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .. import db


def today_local() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d")


@dataclass
class Snapshot:
    day: str
    total_tokens: int
    input_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    claude_tokens: int
    codex_tokens: int
    cost_usd: float
    turns: int
    last_session: dict | None  # {project, source, turns, total_tokens, last_ts} or None

    def title(self) -> str:
        """Compact menu bar title, e.g. '⚡ 1.2M' or '⚡ 0'."""
        return f"⚡ {_short_tokens(self.total_tokens)}"


def snapshot(day: str | None = None) -> Snapshot:
    day = day or today_local()
    with db.connect() as c:
        totals = c.execute(
            """
            SELECT COALESCE(SUM(total_tokens), 0) AS total,
                   COALESCE(SUM(input_tokens), 0) AS input_tokens,
                   COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens,
                   COALESCE(SUM(cache_create_tokens), 0) AS cache_create_tokens,
                   COALESCE(SUM(cost_usd), 0)     AS cost,
                   COUNT(*)                       AS turns,
                   COALESCE(SUM(CASE WHEN source='claude' THEN total_tokens ELSE 0 END), 0) AS claude_tokens,
                   COALESCE(SUM(CASE WHEN source='codex'  THEN total_tokens ELSE 0 END), 0) AS codex_tokens
            FROM turns
            WHERE day_local = ?
            """,
            (day,),
        ).fetchone()

        last = c.execute(
            """
            SELECT s.id, s.source, s.project,
                   COUNT(t.id) AS turns,
                   COALESCE(SUM(t.total_tokens), 0) AS total_tokens,
                   MAX(t.ts) AS last_ts
            FROM sessions s
            JOIN turns t ON t.session_id = s.id
            WHERE t.day_local = ?
            GROUP BY s.id
            ORDER BY last_ts DESC
            LIMIT 1
            """,
            (day,),
        ).fetchone()

    last_session = dict(last) if last else None
    return Snapshot(
        day=day,
        total_tokens=int(totals["total"] or 0),
        input_tokens=int(totals["input_tokens"] or 0),
        cache_read_tokens=int(totals["cache_read_tokens"] or 0),
        cache_create_tokens=int(totals["cache_create_tokens"] or 0),
        claude_tokens=int(totals["claude_tokens"] or 0),
        codex_tokens=int(totals["codex_tokens"] or 0),
        cost_usd=float(totals["cost"] or 0.0),
        turns=int(totals["turns"] or 0),
        last_session=last_session,
    )


def _short_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_cost(c: float) -> str:
    return f"${c:,.2f}"


def fmt_last_session(s: dict | None) -> str:
    if not s:
        return "Last session: —"
    project = s.get("project") or s.get("source") or "?"
    turns = s.get("turns") or 0
    toks = s.get("total_tokens") or 0
    return f"Last: {project} · {turns} turns · {_short_tokens(int(toks))} tok"

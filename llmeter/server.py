"""FastAPI server: dashboard + JSON APIs + SSE stream."""

import asyncio
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from . import db
from . import ingest

app = FastAPI(title="llmeter", docs_url="/api/docs", redoc_url=None)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Global event queue for SSE clients
_subscribers: list[asyncio.Queue] = []


def _today_local() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d")


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/docs", response_class=HTMLResponse)
def docs():
    return FileResponse(os.path.join(STATIC_DIR, "docs.html"))


@app.get("/api/today")
def api_today():
    day = _today_local()
    with db.connect() as c:
        rows = c.execute(
            """
            SELECT hour_local,
                   SUM(input_tokens)        AS input_tokens,
                   SUM(output_tokens)       AS output_tokens,
                   SUM(cache_read_tokens)   AS cache_read_tokens,
                   SUM(cache_create_tokens) AS cache_create_tokens,
                   SUM(reasoning_tokens)    AS reasoning_tokens,
                   SUM(total_tokens)        AS total_tokens,
                   SUM(cost_usd)            AS cost_usd,
                   COUNT(*)                 AS turns
            FROM turns
            WHERE day_local = ?
            GROUP BY hour_local
            ORDER BY hour_local
            """,
            (day,),
        ).fetchall()
        totals = c.execute(
            """
            SELECT SUM(total_tokens) AS total, SUM(cost_usd) AS cost, COUNT(*) AS turns,
                   SUM(CASE WHEN source='claude' THEN total_tokens ELSE 0 END) AS claude_tokens,
                   SUM(CASE WHEN source='codex'  THEN total_tokens ELSE 0 END) AS codex_tokens
            FROM turns WHERE day_local = ?
            """,
            (day,),
        ).fetchone()

    # Build full 24-hour series
    by_hour = {r["hour_local"]: dict(r) for r in rows}
    series = []
    for h in range(24):
        key = f"{day} {h:02d}"
        r = by_hour.get(key)
        series.append({
            "hour": h,
            "label": key,
            "total_tokens": r["total_tokens"] if r else 0,
            "cost_usd":     r["cost_usd"]     if r else 0,
            "turns":        r["turns"]        if r else 0,
        })

    return {
        "day": day,
        "series": series,
        "totals": {
            "total_tokens": totals["total"] or 0,
            "cost_usd":     totals["cost"] or 0,
            "turns":        totals["turns"] or 0,
            "claude_tokens": totals["claude_tokens"] or 0,
            "codex_tokens":  totals["codex_tokens"] or 0,
        },
    }


@app.get("/api/sessions")
def api_sessions(day: str | None = None, limit: int = 200):
    day = day or _today_local()
    with db.connect() as c:
        rows = c.execute(
            """
            SELECT s.id, s.source, s.project, s.cwd, s.opening_prompt, s.models,
                   s.is_sidechain,
                   MIN(t.ts) AS first_ts, MAX(t.ts) AS last_ts,
                   SUM(t.total_tokens) AS total_tokens,
                   SUM(t.input_tokens) AS input_tokens,
                   SUM(t.output_tokens) AS output_tokens,
                   SUM(t.cache_read_tokens) AS cache_read_tokens,
                   SUM(t.cache_create_tokens) AS cache_create_tokens,
                   SUM(t.cost_usd) AS cost_usd,
                   COUNT(*) AS turns
            FROM sessions s
            JOIN turns t ON t.session_id = s.id
            WHERE t.day_local = ?
            GROUP BY s.id
            ORDER BY last_ts DESC
            LIMIT ?
            """,
            (day, limit),
        ).fetchall()
    return {"day": day, "sessions": [dict(r) for r in rows]}


@app.get("/api/session/{sid}")
def api_session(sid: str):
    with db.connect() as c:
        sess = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if not sess:
            raise HTTPException(404, "session not found")
        turns = c.execute(
            """SELECT ts, model, input_tokens, output_tokens, cache_read_tokens,
                      cache_create_tokens, reasoning_tokens, total_tokens, cost_usd
               FROM turns WHERE session_id=? ORDER BY ts ASC""",
            (sid,),
        ).fetchall()
    return {"session": dict(sess), "turns": [dict(t) for t in turns]}


@app.get("/api/days")
def api_days():
    with db.connect() as c:
        rows = c.execute(
            """SELECT day_local, SUM(total_tokens) AS total_tokens, SUM(cost_usd) AS cost_usd,
                      COUNT(DISTINCT session_id) AS sessions, COUNT(*) AS turns
               FROM turns GROUP BY day_local ORDER BY day_local DESC LIMIT 30"""
        ).fetchall()
    return {"days": [dict(r) for r in rows]}


@app.get("/stream")
async def stream():
    queue: asyncio.Queue = asyncio.Queue(maxsize=64)
    _subscribers.append(queue)

    async def gen():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15)
                    yield {"event": "tick", "data": msg}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "keepalive"}
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return EventSourceResponse(gen())


def broadcast(msg: str):
    for q in list(_subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


async def poll_loop(interval: float = 3.0):
    """Background task: scan log files for new content and notify SSE subscribers."""
    while True:
        try:
            with db.connect() as c:
                new = ingest.scan_all(c)
            if new:
                broadcast(f"new_turns:{new}")
        except Exception as e:
            print(f"[llmeter] poll error: {e}", flush=True)
        await asyncio.sleep(interval)


@app.on_event("startup")
async def _startup():
    db.init()
    # Initial backfill
    with db.connect() as c:
        added = ingest.scan_all(c)
    print(f"[llmeter] backfill complete: {added} new turns", flush=True)
    asyncio.create_task(poll_loop())

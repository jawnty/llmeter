"""Parse Claude Code session JSONL files at ~/.claude/projects/**/*.jsonl

Each line is a JSON object. Relevant shapes:
- type: "user"      -> message.content (string or list)
- type: "assistant" -> message.usage with token counts, message.model
Sessions are identified by sessionId. cwd holds the project path.
isSidechain=true marks subagent files; we still record them but tag them.
"""

import json
from datetime import datetime, timezone
from .pricing import cost_usd
from .timeutil import to_local_buckets


def _opening_prompt(content):
    if isinstance(content, str):
        return content[:500]
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return (block.get("text") or "")[:500]
            if isinstance(block, str):
                return block[:500]
    return None


def parse_line(raw_line: str):
    """Yield (kind, payload) tuples. kind in {'session_init', 'turn'}."""
    line = raw_line.strip()
    if not line:
        return
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        return

    sid = d.get("sessionId")
    if not sid:
        return

    ts = d.get("timestamp")
    cwd = d.get("cwd") or ""
    project = cwd.rstrip("/").split("/")[-1] if cwd else None
    is_sidechain = 1 if d.get("isSidechain") else 0

    typ = d.get("type")

    if typ == "user":
        msg = d.get("message") or {}
        prompt = _opening_prompt(msg.get("content"))
        yield ("session_init", {
            "id": sid,
            "source": "claude",
            "cwd": cwd,
            "project": project,
            "started_at": ts,
            "last_seen_at": ts,
            "opening_prompt": prompt,
            "models": "",
            "is_sidechain": is_sidechain,
        })
        return

    if typ == "assistant":
        msg = d.get("message") or {}
        usage = msg.get("usage") or {}
        model = msg.get("model") or ""
        in_tok = usage.get("input_tokens", 0) or 0
        out_tok = usage.get("output_tokens", 0) or 0
        cr_tok = usage.get("cache_read_input_tokens", 0) or 0
        cw_tok = usage.get("cache_creation_input_tokens", 0) or 0
        if in_tok == 0 and out_tok == 0 and cr_tok == 0 and cw_tok == 0:
            return
        total = in_tok + out_tok + cr_tok + cw_tok
        hour_local, day_local = to_local_buckets(ts)
        cost = cost_usd(model, in_tok, out_tok, cr_tok, cw_tok)
        uuid = d.get("uuid") or f"{sid}-{ts}-{msg.get('id','')}"

        yield ("session_init", {
            "id": sid,
            "source": "claude",
            "cwd": cwd,
            "project": project,
            "started_at": ts,
            "last_seen_at": ts,
            "opening_prompt": None,
            "models": model,
            "is_sidechain": is_sidechain,
        })
        yield ("turn", {
            "session_id": sid,
            "source": "claude",
            "ts": ts,
            "hour_local": hour_local,
            "day_local": day_local,
            "model": model,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cache_read_tokens": cr_tok,
            "cache_create_tokens": cw_tok,
            "reasoning_tokens": 0,
            "total_tokens": total,
            "cost_usd": cost,
            "raw_uuid": f"claude:{uuid}",
        })

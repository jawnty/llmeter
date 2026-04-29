"""Parse Codex CLI session JSONL files at ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl

Relevant lines:
- type: "session_meta" -> payload.id, payload.cwd, payload.timestamp
- type: "event_msg", payload.type: "user_message" -> payload.message
- type: "event_msg", payload.type: "token_count" -> payload.info.last_token_usage
- type: "turn_context" -> payload.model (may carry model name)

Token counts only present in sessions after 2025-09-06 (token_count event commit).
Earlier sessions yield no turn rows.
"""

import json
import os
from .pricing import cost_usd
from .timeutil import to_local_buckets


# Per-file state: file path -> {"session_id":..., "cwd":..., "model":..., "first_user":..., "started_at":..., "last_total":int}
_FILE_STATE = {}


def _state_for(path):
    s = _FILE_STATE.get(path)
    if s is None:
        s = {
            "session_id": None,
            "cwd": None,
            "model": None,
            "first_user": None,
            "started_at": None,
            "last_total": {  # remember cumulative totals so we can emit deltas if needed
                "input": 0, "output": 0, "cached_input": 0, "reasoning": 0
            },
            "turn_idx": 0,
        }
        _FILE_STATE[path] = s
    return s


def _session_id_from_path(path):
    # Filename: rollout-2026-04-22T17-12-36-019db7ae-7498-7b41-bbb7-aa68db837455.jsonl
    base = os.path.basename(path)
    if base.startswith("rollout-") and base.endswith(".jsonl"):
        # Last 5 dash-segments form the UUID
        stem = base[len("rollout-"):-len(".jsonl")]
        parts = stem.split("-")
        if len(parts) >= 5:
            return "-".join(parts[-5:])
    return base


def parse_line(raw_line: str, path: str):
    line = raw_line.strip()
    if not line:
        return
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        return

    state = _state_for(path)
    typ = d.get("type")
    payload = d.get("payload") or {}
    pt = payload.get("type") if isinstance(payload, dict) else None
    ts = d.get("timestamp")

    if typ == "session_meta":
        state["session_id"] = payload.get("id") or _session_id_from_path(path)
        state["cwd"] = payload.get("cwd")
        state["started_at"] = payload.get("timestamp") or ts
        project = (state["cwd"] or "").rstrip("/").split("/")[-1] if state["cwd"] else None
        yield ("session_init", {
            "id": state["session_id"],
            "source": "codex",
            "cwd": state["cwd"] or "",
            "project": project,
            "started_at": state["started_at"],
            "last_seen_at": state["started_at"],
            "opening_prompt": None,
            "models": "",
            "is_sidechain": 0,
        })
        return

    if typ == "turn_context":
        m = payload.get("model")
        if m:
            state["model"] = m
        return

    if typ == "event_msg" and pt == "user_message":
        if not state["session_id"]:
            state["session_id"] = _session_id_from_path(path)
        if state["first_user"] is None:
            msg = payload.get("message") or ""
            state["first_user"] = msg[:500]
            project = (state["cwd"] or "").rstrip("/").split("/")[-1] if state["cwd"] else None
            yield ("session_init", {
                "id": state["session_id"],
                "source": "codex",
                "cwd": state["cwd"] or "",
                "project": project,
                "started_at": state["started_at"] or ts,
                "last_seen_at": ts,
                "opening_prompt": state["first_user"],
                "models": state["model"] or "",
                "is_sidechain": 0,
            })
        return

    if typ == "event_msg" and pt == "token_count":
        info = payload.get("info") or {}
        last = info.get("last_token_usage") or {}
        if not last:
            return  # pre-2025-09-06 session, no token data
        in_tok = last.get("input_tokens", 0) or 0
        out_tok = last.get("output_tokens", 0) or 0
        cr_tok = last.get("cached_input_tokens", 0) or 0
        reason = last.get("reasoning_output_tokens", 0) or 0
        total = last.get("total_tokens", 0) or (in_tok + out_tok)
        if in_tok == 0 and out_tok == 0:
            return
        # Codex's `input_tokens` includes cached. Subtract cached for non-cached input.
        non_cached_input = max(in_tok - cr_tok, 0)
        model = state["model"] or "gpt-5"
        hour_local, day_local = to_local_buckets(ts)
        cost = cost_usd(model, non_cached_input, out_tok, cr_tok, 0)
        sid = state["session_id"] or _session_id_from_path(path)
        state["turn_idx"] += 1
        uuid = f"codex:{sid}:{state['turn_idx']}:{ts}"
        yield ("session_init", {
            "id": sid,
            "source": "codex",
            "cwd": state["cwd"] or "",
            "project": (state["cwd"] or "").rstrip("/").split("/")[-1] if state["cwd"] else None,
            "started_at": state["started_at"] or ts,
            "last_seen_at": ts,
            "opening_prompt": state["first_user"],
            "models": model,
            "is_sidechain": 0,
        })
        yield ("turn", {
            "session_id": sid,
            "source": "codex",
            "ts": ts,
            "hour_local": hour_local,
            "day_local": day_local,
            "model": model,
            "input_tokens": non_cached_input,
            "output_tokens": out_tok,
            "cache_read_tokens": cr_tok,
            "cache_create_tokens": 0,
            "reasoning_tokens": reason,
            "total_tokens": total,
            "cost_usd": cost,
            "raw_uuid": uuid,
        })

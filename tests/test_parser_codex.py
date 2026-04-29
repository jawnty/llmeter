import json

from tokmon import parser_codex


def test_codex_session_prompt_and_token_count():
    parser_codex._FILE_STATE.clear()
    path = "/tmp/rollout-2026-04-29T17-00-00-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.jsonl"

    lines = [
        {
            "type": "session_meta",
            "timestamp": "2026-04-29T17:00:00Z",
            "payload": {
                "id": "sess-1",
                "cwd": "/Users/john/projects/tokmon",
                "timestamp": "2026-04-29T17:00:00Z",
            },
        },
        {
            "type": "turn_context",
            "timestamp": "2026-04-29T17:01:00Z",
            "payload": {"model": "gpt-5.5"},
        },
        {
            "type": "event_msg",
            "timestamp": "2026-04-29T17:02:00Z",
            "payload": {"type": "user_message", "message": "Please inspect tokmon"},
        },
        {
            "type": "event_msg",
            "timestamp": "2026-04-29T17:03:00Z",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 1000,
                        "cached_input_tokens": 250,
                        "output_tokens": 125,
                        "reasoning_output_tokens": 75,
                        "total_tokens": 1125,
                    }
                },
            },
        },
    ]

    events = []
    for line in lines:
        events.extend(parser_codex.parse_line(json.dumps(line), path))

    assert [kind for kind, _ in events] == ["session_init", "session_init", "session_init", "turn"]
    assert events[1][1]["opening_prompt"] == "Please inspect tokmon"
    turn = events[-1][1]
    assert turn["session_id"] == "sess-1"
    assert turn["source"] == "codex"
    assert turn["model"] == "gpt-5.5"
    assert turn["input_tokens"] == 750
    assert turn["cache_read_tokens"] == 250
    assert turn["output_tokens"] == 125
    assert turn["reasoning_tokens"] == 75
    assert turn["total_tokens"] == 1125

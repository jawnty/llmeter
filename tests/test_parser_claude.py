import json

from llmeter import parser_claude


def test_claude_user_line_initializes_session():
    line = json.dumps({
        "type": "user",
        "sessionId": "abc",
        "timestamp": "2026-04-29T17:00:00Z",
        "cwd": "/Users/john/projects/llmeter",
        "message": {"content": "Build the token dashboard"},
    })

    events = list(parser_claude.parse_line(line))

    assert events == [("session_init", {
        "id": "abc",
        "source": "claude",
        "cwd": "/Users/john/projects/llmeter",
        "project": "llmeter",
        "started_at": "2026-04-29T17:00:00Z",
        "last_seen_at": "2026-04-29T17:00:00Z",
        "opening_prompt": "Build the token dashboard",
        "models": "",
        "is_sidechain": 0,
    })]


def test_claude_assistant_line_emits_turn():
    line = json.dumps({
        "type": "assistant",
        "sessionId": "abc",
        "uuid": "turn-1",
        "timestamp": "2026-04-29T17:00:00Z",
        "cwd": "/Users/john/projects/llmeter",
        "message": {
            "id": "msg-1",
            "model": "claude-sonnet-4",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_input_tokens": 25,
                "cache_creation_input_tokens": 10,
            },
        },
    })

    events = list(parser_claude.parse_line(line))

    assert [kind for kind, _ in events] == ["session_init", "turn"]
    turn = events[1][1]
    assert turn["session_id"] == "abc"
    assert turn["source"] == "claude"
    assert turn["model"] == "claude-sonnet-4"
    assert turn["input_tokens"] == 100
    assert turn["output_tokens"] == 50
    assert turn["cache_read_tokens"] == 25
    assert turn["cache_create_tokens"] == 10
    assert turn["total_tokens"] == 185
    assert turn["raw_uuid"] == "claude:turn-1"

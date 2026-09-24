from __future__ import annotations

import json

import pytest

from deployments.tidmad_coding_agent_baseline.tools.usage import aggregate_usage


@pytest.mark.parametrize(
    ("product", "event", "expected"),
    [
        (
            "codex",
            {"type": "turn.completed", "usage": {"input_tokens": 17, "output_tokens": 3}},
            {"input_tokens": 17, "cached_input_tokens": 0, "output_tokens": 3},
        ),
        (
            "claude",
            {"type": "result", "usage": {"input_tokens": 11, "output_tokens": 2}},
            {
                "input_tokens": 11,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 2,
            },
        ),
    ],
)
def test_usage_skips_non_object_json_without_losing_final_event(
    tmp_path, product, event, expected
):
    log = tmp_path / f"{product}-invocation-0001.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}),
                json.dumps("/work/agent/results/candidate.score.json"),
                json.dumps(["tool", "output"]),
                json.dumps(None),
                "not json",
                json.dumps(event),
            ]
        )
        + "\n"
    )

    assert aggregate_usage(tmp_path, product) == {
        "product": product,
        "invocation_logs": 1,
        "totals": expected,
        "logs_without_final_usage": [],
    }

"""Replay two archived invalid replies through real generated-program recovery.

Stops at the first request not covered by the archived replies. No model,
generated code, skill, dataset, or training process is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


def replay(
    archive: Path,
    receipt_sha256: str,
    output: Path,
    recovery_policy: Path | None = None,
) -> dict:
    receipt_path = archive / "structured_output_receipts.jsonl"
    receipt_bytes = receipt_path.read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != receipt_sha256:
        raise ValueError("Archived receipt digest mismatch")
    rows = [json.loads(line) for line in receipt_bytes.decode().splitlines()]
    matches = [
        row
        for row in rows
        if row["stage"] == "data_analysis.generated_program"
        and row["repair_attempted"]
        and row["repair_passed"] is False
    ]
    if len(matches) != 1:
        raise ValueError("Expected exactly one failed generated-program repair receipt")
    receipt = matches[0]
    drafts = [receipt["initial_output"], receipt["repaired_output"]]

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline recovery replay cannot access the network")

    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"):
        os.environ.pop(key, None)

    import agent
    from agent.data_analysis.generated_program_planning import prepare_generated_program
    from agent.data_analysis.persistence import AnalysisRunStore
    from agent.data_analysis.structured_output import DataAnalysisStructuredOutputError
    from agent.schemas.data_analysis.common import canonical_sha256
    from agent.schemas.data_analysis.context import DataAnalysisInput
    from agent.schemas.storage import StorageConfig

    checkout = Path(agent.__file__).resolve().parents[2]
    if Path(sys.prefix).resolve() != (checkout / ".venv").resolve():
        raise ValueError("Use the executing infra checkout's own frozen environment")
    for draft, name in zip(drafts, ("initial", "repaired"), strict=True):
        if canonical_sha256(draft) != receipt[f"{name}_payload_sha256"]:
            raise ValueError(f"Archived {name} reply digest mismatch")
    analysis_input_bytes = (archive / "input.json").read_bytes()
    input_payload = json.loads(analysis_input_bytes)
    policy_bytes = None
    if recovery_policy is not None:
        policy_bytes = recovery_policy.read_bytes()
        input_payload["recovery_policy"] = json.loads(policy_bytes)
    analysis_input = DataAnalysisInput.model_validate(input_payload)
    output.mkdir(parents=True, exist_ok=False)
    store = AnalysisRunStore(
        StorageConfig(local={"workspace": str(output), "run_name": "offline"}),
        request_id=analysis_input.request_id,
    )
    captures = []

    class MissingReply(BaseException):
        """The current code requested a call absent from the archived witness."""

    class ArchivedReplies:
        def generate(self, system, user, *, label):
            index = len(captures)
            captures.append({"label": label, "system": system, "user": user})
            if index >= len(drafts):
                raise MissingReply()
            expected = (
                "data_analysis.generated_program",
                "data_analysis.generated_program.repair",
            )[index]
            if label != expected:
                raise AssertionError(
                    f"Reply routing changed: expected {expected}, got {label}"
                )
            return deepcopy(drafts[index])

    try:
        prepare_generated_program(
            bridge=ArchivedReplies(),
            store=store,
            analysis_input=analysis_input,
            question_ids=tuple(drafts[0]["question_ids"]),
            provider="openai",
            requested_model_id="offline-archived-replies",
            llm_config={},
        )
    except MissingReply:
        outcome = "additional_request_without_archived_reply"
    except DataAnalysisStructuredOutputError:
        outcome = "failed_after_archived_repair"
    else:
        raise AssertionError(
            "Both archived replies are invalid; execution must not be reached"
        )

    source_digest = hashlib.sha256()
    for source in sorted((checkout / "src").rglob("*.py")):
        source_digest.update(str(source.relative_to(checkout)).encode() + b"\0")
        source_digest.update(hashlib.sha256(source.read_bytes()).digest())
    result = {
        "source_tree_sha256": source_digest.hexdigest(),
        "infra_revision": subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_diff_sha256": hashlib.sha256(
            subprocess.check_output(
                ["git", "-C", str(checkout), "diff", "HEAD", "--", "src"]
            )
        ).hexdigest(),
        "capture_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "receipt_sha256": receipt_sha256,
        "input_sha256": hashlib.sha256(analysis_input_bytes).hexdigest(),
        "recovery_policy_sha256": (
            None if policy_bytes is None else hashlib.sha256(policy_bytes).hexdigest()
        ),
        "outcome": outcome,
        "requests": [
            {
                "label": item["label"],
                **{
                    f"{name}_sha256": hashlib.sha256(item[name].encode()).hexdigest()
                    for name in ("system", "user")
                },
            }
            for item in captures
        ],
        "archived_replies_consumed": min(len(captures), len(drafts)),
        "api_calls": 0,
        "training_calls": 0,
        "generated_program_executions": 0,
        "scope": "archived failure branch only; not complete conversation replay",
    }
    (output / "messages.json").write_text(json.dumps(captures, indent=2) + "\n")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--recovery-policy", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            replay(
                args.archive.resolve(),
                args.receipt_sha256,
                args.output.resolve(),
                args.recovery_policy,
            ),
            indent=2,
        )
    )

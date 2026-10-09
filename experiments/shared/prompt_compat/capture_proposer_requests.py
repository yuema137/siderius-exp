"""Capture synthetic full proposer requests using the executing infra checkout.

Only the provider boundary is scripted. Protocol conversion, node orchestration,
validation, prompt assembly and retries use the selected framework source.
No scientific dataset, provider, training or inference is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from unittest.mock import MagicMock, patch

from capture import validate_checkout
from pydantic import BaseModel, ConfigDict, Field, JsonValue


class Witness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    mode: Literal["legacy", "explore", "exploit"]
    is_trial: bool
    trial: float | None
    formal: float | None
    responses: list[str]
    expected_labels: list[str]
    text_reasoning: bool = False
    prior_stage_max_chars: int | None = None


class WitnessBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    provenance: dict[str, str]
    interpretation: dict[str, JsonValue]
    replies: dict[str, dict[str, JsonValue]]
    cases: list[Witness] = Field(min_length=1)


def capture_case(
    bundle: WitnessBundle, case: Witness, workspace: Path
) -> list[dict[str, str]]:
    from agent.schemas.interpretation import InterpretationOutput
    from agent.schemas.proposal import ReasoningPipelineConfig, ReasoningStage
    from agent.schemas.protocols.ml_result_interp_to_ml_model_propose import (
        local_full_context,
    )
    from agent.schemas.storage import LocalStorageConfig, StorageConfig
    from agent.schemas.task_config import ForwardContract
    from core.generated_library import bind_generated_library_to_workspace
    from nodes.ml_model_proposal_agent import MLModelProposalAgent

    bind_generated_library_to_workspace(str(workspace))
    stages = (
        []
        if case.mode == "legacy"
        else [
            ReasoningStage(name="comparison", system_prompt_key="COMPARATIVE_ANALYSIS"),
            ReasoningStage(
                name="causal_reasoning", system_prompt_key="CAUSAL_REASONING"
            ),
        ]
    )
    inp = local_full_context(
        InterpretationOutput.model_validate(bundle.interpretation),
        StorageConfig(
            backend="local",
            local=LocalStorageConfig(
                workspace=str(workspace), run_name="budget-context"
            ),
        ),
        reasoning_pipeline=ReasoningPipelineConfig(
            stages=stages,
            exploration_mode="exploit" if case.mode == "exploit" else "explore",
        ),
        trial_time_budget_minutes=case.trial,
        formal_time_budget_minutes=case.formal,
        is_trial=case.is_trial,
    )
    inp.forward_contract = ForwardContract(
        input_shape="[B, T] int64",
        input_description="class indices",
        output_shape="[B, 256, T] float32",
        output_description="per-timestep class logits",
        num_classes=256,
        task_type="classification",
    )
    if case.text_reasoning:
        for stage in inp.reasoning_pipeline.stages:
            stage.output_mode = "text"
    if case.prior_stage_max_chars is not None:
        inp.reasoning_pipeline.policy.prior_stage_max_chars = case.prior_stage_max_chars
    responses = iter(deepcopy([bundle.replies[key] for key in case.responses]))
    messages = []

    def generate(system, user, **kwargs):
        messages.append({"label": kwargs["label"], "system": system, "user": user})
        return next(responses)

    def generate_text(system, user, **kwargs):
        messages.append({"label": kwargs["label"], "system": system, "user": user})
        return "Choose a spectral convolution."

    bridge = MagicMock()
    bridge.generate.side_effect = generate
    bridge.generate_text.side_effect = generate_text
    node = MLModelProposalAgent(
        provider="gemini",
        model_id="offline-budget-witness",
        bridge_factory=lambda **_: bridge,
    )
    node.run(inp)
    if [m["label"] for m in messages] != case.expected_labels:
        raise AssertionError(f"{case.case_id}: expected request branch was not reached")
    if next(responses, None) is not None:
        raise AssertionError(f"{case.case_id}: scripted replies remained unused")
    return messages


def capture(
    fixture: Path, output: Path, expected_revision: str, profile_name: str
) -> dict:
    revision = validate_checkout(expected_revision)
    fixture_bytes = fixture.read_bytes()
    bundle = WitnessBundle.model_validate_json(fixture_bytes)

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Provider/network/training access is forbidden during offline capture"
        )

    with ExitStack() as stack:
        # Restore all temporary bindings, including each case's generated library.
        stack.enter_context(patch.dict(os.environ))
        for name in ("connect", "connect_ex"):
            stack.enter_context(patch.object(socket.socket, name, forbidden))
        stack.enter_context(patch.object(socket, "create_connection", forbidden))
        stack.enter_context(patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""}))
        for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"):
            os.environ.pop(name, None)

        from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
        from execute_tools.dataset_config import (
            ChannelIdentity,
            DatasetConfig,
            DatasetProfile,
            ValueEncoding,
            bind_dataset_profile,
        )

        profile = resolve_prompt_profile(profile_name)
        identity = profile.identity().model_dump(mode="json")
        stack.enter_context(bind_prompt_profile(profile))
        dataset = DatasetConfig(
            psd_segment_length=200_000,
            segments_per_file=4,
            num_files=20,
            sampling_frequency=1000.0,
            training_file_pattern="training_{file_index:04d}.h5",
            validation_file_pattern="validation_{file_index:04d}.h5",
        )
        # An explicit synthetic topology supplies existing node schema defaults.
        # No file is created or opened for this declaration.
        stack.enter_context(
            bind_dataset_profile(
                DatasetProfile(
                    partition_count=20,
                    topology={
                        "dataset": dataset.model_dump(),
                        "channels": ChannelIdentity(
                            input_channel="input", target_channel="target"
                        ).model_dump(),
                        "encoding": ValueEncoding(
                            storage_dtype="int8",
                            compute_dtype="int16",
                            value_offset=128,
                            num_classes=256,
                        ).model_dump(),
                    },
                    anchor_selection_files=[0, 1, 2],
                    health_peek_files=[0, 1, 2],
                )
            )
        )
        with TemporaryDirectory(prefix="proposer-budget-witness-") as temp:
            rows = [
                {
                    "case": case.case_id,
                    "messages": capture_case(bundle, case, Path(temp) / case.case_id),
                }
                for case in bundle.cases
            ]
    output.mkdir(parents=True, exist_ok=False)
    (output / "messages.json").write_text(json.dumps(rows, indent=2) + "\n")
    receipt = {
        "infra_revision": revision,
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "capture_sources": {
            name: hashlib.sha256(
                Path(__file__).with_name(name).read_bytes()
            ).hexdigest()
            for name in ("capture_proposer_requests.py", "capture.py")
        },
        "profile": identity,
        "scope": bundle.provenance["scope"],
        "cases": [
            {
                "case": row["case"],
                "messages": [
                    {
                        "label": m["label"],
                        **{
                            role + "_sha256": hashlib.sha256(
                                m[role].encode()
                            ).hexdigest()
                            for role in ("system", "user")
                        },
                    }
                    for m in row["messages"]
                ],
            }
            for row in rows
        ],
        "provider_calls": 0,
        "training_calls": 0,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    capture(args.fixture, args.output, args.expected_revision, args.profile)

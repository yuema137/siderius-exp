"""Replay declared timing evidence through the installed execution-session owners.

This offline harness performs no model, data, GPU or provider execution. Environment
capture and setup clock are controlled inputs; phase timing comes from archived
numeric traces. It cannot certify a complete training run or conversation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch


def replay_cases(
    fixture: dict, *, completion_policy: str | None, historical_verifier: bool = False
) -> list[dict]:
    """Run pre-fix or explicitly selected candidate admission for the same traces."""
    import core.runtime_control.session as owner
    from core.runtime_control.workload import ResolvedPhaseWorkload

    results = []
    with tempfile.TemporaryDirectory(prefix="runtime-completion-replay-") as directory:
        for index, case in enumerate(fixture["cases"]):
            inputs = case["input"]
            policy_fields = {
                "operator_budget_seconds": inputs["operator_budget_seconds"],
                "time_admission_source": "measured",
                "safety_factor": inputs["safety_factor"],
                "verification": inputs["verification"],
            }
            if completion_policy is not None:
                policy_fields["runtime_completion_policy"] = completion_policy
            if historical_verifier:
                family = case["reference_infra_revision"][:8]
                policy_fields["runtime_verifier"] = f"legacy-{family}-verifier-v1"
            policy = owner.RuntimeControlPolicy.model_validate(policy_fields)
            with (
                patch.object(owner, "capture_environment_provenance", return_value={}),
                patch.object(owner.time, "perf_counter", return_value=0.0) as clock,
            ):
                session = owner.RuntimeVerificationSession(
                    str(Path(directory) / f"{index}.json"), policy=policy
                )
                clock.return_value = case["expected_archived"]["admission"][
                    "setup_cost_seconds"
                ]
                session.complete_setup(
                    storage_provenance={},
                    training_workload=ResolvedPhaseWorkload.model_validate(
                        inputs["workload"]
                    ),
                )
                verifier = session.start_phase_verification(
                    inputs["phase"],
                    unit=inputs["workload"]["unit"],
                    prior_expected_unit_ms=inputs["prior_expected_unit_ms"],
                )
                observed = 0
                for rate, elapsed in zip(
                    inputs["unit_timings_ms"],
                    inputs["observation_elapsed_ms"],
                    strict=True,
                ):
                    if verifier.is_terminal:
                        break
                    verifier.feed(rate, elapsed_ms=elapsed)
                    observed += 1
                if completion_policy == "completed-workload-v1":
                    session.complete_phase_workload(
                        inputs["phase"],
                        actual_seconds=sum(inputs["observation_elapsed_ms"]) / 1000.0,
                        executed_unit_count=inputs["workload"]["unit_count"],
                        verifier=verifier,
                        source="real_dataset_warmup",
                    )
                else:
                    session.complete_phase_verification(
                        inputs["phase"], verifier, source="real_dataset_warmup"
                    )
                admission = session.decide_admission(stage="post_training_verification")
                observation = session.observation
                results.append(
                    {
                        "case_id": case["case_id"],
                        "policy": policy.model_dump(mode="json"),
                        "observed_units": observed,
                        "component": observation.components[inputs["phase"]].model_dump(
                            mode="json"
                        ),
                        "admission": admission.model_dump(mode="json"),
                        "final_status": observation.final_status,
                    }
                )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--completion-policy")
    parser.add_argument("--historical-verifier", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revision = subprocess.check_output(
        ["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != args.expected_revision or subprocess.check_output(
        ["git", "-C", str(args.checkout), "diff", "HEAD", "--", "src"], text=True
    ):
        raise ValueError("Reference source must match the declared clean revision")
    import core.runtime_control.session as owner

    if (
        Path(owner.__file__).resolve()
        != (args.checkout / "src/core/runtime_control/session.py").resolve()
    ):
        raise ValueError("Use the selected checkout's own installed environment")
    results = replay_cases(
        json.loads(args.fixture.read_text()),
        completion_policy=args.completion_policy,
        historical_verifier=args.historical_verifier,
    )
    args.output.write_text(
        json.dumps({"infra_revision": revision, "results": results}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

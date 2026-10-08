"""Installed provider, child transport and historical session qualification.

These checks intentionally require the paired infra and a qualified assembly;
they must not pass by skipping unavailable integration or patching qualification.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from core.runtime_control.adaptive import AdaptiveVerificationConfig
from core.runtime_control.session import RuntimeControlPolicy
from core.runtime_control.verifier_provider import (
    create_runtime_verifier,
    resolve_runtime_verifier,
)

from experiments.shared.runtime_compat.replay import replay_cases

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "fixtures/paper-finite-workloads.json").read_text())
SELECTIONS = [
    f"legacy-{family}-verifier-v1" for family in ("345c802d", "7689fd58", "349b6cd6")
]
OVERLAY = json.loads((ROOT / "paper-measured-completion-v1.json").read_text())


@pytest.mark.parametrize(
    "unit", OVERLAY["covered_units"], ids=lambda unit: unit["run_id"]
)
def test_paper_overlay_reaches_the_standard_launch_owner(unit, tmp_path):
    """Exercise real CLI normalization and projection without launching a workflow."""
    from workflows.launch_identity import resolve_launch_identity
    from workflows.standard_cli import build_parser, normalize_args
    from workflows.standard_launch import build_standard_launch_config

    flags = OVERLAY["launch_parameters"] | unit["launch_parameters"]
    args = normalize_args(
        build_parser().parse_args(
            [
                "--workspace",
                str(tmp_path / "new-workspace"),
                "--run_name",
                unit["run_id"],
                "--start_iteration",
                "1",
                "--task_composition",
                str(tmp_path / "external-task.yaml"),
                "--data_dir",
                str(tmp_path / "external-data"),
                *[value for pair in flags.items() for value in pair],
            ]
        )
    )
    launch = build_standard_launch_config(
        args,
        resolve_launch_identity(args),
        resolved_paths=[],
        fixed_candidate_plan=None,
    )
    expected = resolve_runtime_verifier(flags["--runtime_verifier"]).identity()
    assert launch.runtime_verifier == expected.name
    assert launch.runtime_verifier_identity == expected
    assert launch.runtime_completion_policy == "verified-prediction-v1"
    assert launch.trial_time_admission_source == "measured"
    assert launch.formal_time_admission_source == "measured"


@pytest.mark.parametrize("selection", SELECTIONS)
def test_installed_profile_is_preserved_and_revalidated_in_child(selection):
    policy = RuntimeControlPolicy(
        runtime_verifier=selection,
        runtime_completion_policy="verified-prediction-v1",
    )
    encoded = policy.model_dump_json()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from core.runtime_control.session import RuntimeControlPolicy; "
                "import json; from core.runtime_control.adaptive import AdaptiveVerificationConfig; "
                "from core.runtime_control.verifier_provider import create_runtime_verifier; "
                "policy = RuntimeControlPolicy.model_validate_json(sys.stdin.read()); "
                "verifier = create_runtime_verifier("
                "selection=policy.runtime_verifier, expected=policy.runtime_verifier_identity, "
                "unit='optimizer_step', config=AdaptiveVerificationConfig(), "
                "prior_expected_unit_ms=None, completion_policy=policy.runtime_completion_policy); "
                "print(json.dumps({'policy': policy.model_dump(mode='json'), "
                "'permits_workload_completion': verifier.permits_workload_completion, "
                "'verifier_module': type(verifier).__module__}))"
            ),
        ],
        input=encoded,
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT,
    )
    actual = json.loads(result.stdout)
    assert actual["policy"] == json.loads(encoded)
    assert actual["permits_workload_completion"] is False
    assert actual["verifier_module"] == "siderius_runtime_compat.adapter"
    assert (
        policy.runtime_verifier_identity
        == resolve_runtime_verifier(selection).identity()
    )


@pytest.mark.parametrize("selection", SELECTIONS)
def test_changed_identity_is_rejected_before_phase_work(selection):
    identity = resolve_runtime_verifier(selection).identity()
    changed = identity.model_copy(update={"content_sha256": "0" * 64})
    with pytest.raises(ValueError, match="changed after launch"):
        RuntimeControlPolicy(
            runtime_verifier=selection,
            runtime_verifier_identity=changed,
            runtime_completion_policy="verified-prediction-v1",
        )


@pytest.mark.parametrize("selection", SELECTIONS)
def test_installed_provider_rejects_incompatible_completion(selection):
    identity = resolve_runtime_verifier(selection).identity()
    with pytest.raises(ValueError, match="require runtime_completion_policy"):
        create_runtime_verifier(
            selection=selection,
            expected=identity,
            unit="optimizer_step",
            config=AdaptiveVerificationConfig(),
            prior_expected_unit_ms=None,
            completion_policy="completed-workload-v1",
        )


def test_unknown_installed_selection_fails_closed():
    with pytest.raises(ValueError, match="Expected one installed runtime verifier"):
        RuntimeControlPolicy(runtime_verifier="uninstalled-historical-verifier")


def test_unqualified_assembly_fails_before_phase_work(monkeypatch):
    import core.runtime_control.verifier_provider as owner

    monkeypatch.setattr(owner, "verifier_assembly_digest", lambda: "0" * 64)
    with pytest.raises(ValueError, match="has not qualified this assembly"):
        RuntimeControlPolicy(runtime_verifier=SELECTIONS[0])


def test_historical_sessions_preserve_all_original_finite_trace_decisions():
    outputs = replay_cases(
        FIXTURE,
        completion_policy="verified-prediction-v1",
        historical_verifier=True,
    )
    for case, output in zip(FIXTURE["cases"], outputs, strict=True):
        expected = case["expected_archived"]
        assert output["component"]["measurement"] == expected["measurement"], case[
            "case_id"
        ]
        assert output["component"]["prediction"] == expected["prediction"], case[
            "case_id"
        ]
        assert output["final_status"] == expected["final_status"], case["case_id"]
        assert output["admission"] == expected["admission"], case["case_id"]
        assert output["observed_units"] == len(case["input"]["unit_timings_ms"])

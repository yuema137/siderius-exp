"""Frozen arithmetic/search comparisons and explicit provider selection guards."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

pytest.importorskip("core.preflight_estimation")

from agent.skills.evaluate_vram_skill import batch_resolver
from agent.skills.evaluate_vram_skill.structural_probe import (
    AutogradTapeReport,
    ForwardLayerReport,
    ProbeResult,
)
from core.preflight_estimation import (
    bind_preflight_estimator,
    estimation_assembly_digest,
    resolve_preflight_estimator,
)
from core.preflight_observations import PhaseObservations, RegisteredStateInventory
from siderius_preflight_compat import SELECTION, historical_profile
from siderius_preflight_compat.arithmetic import estimate_historical_phase
from siderius_preflight_compat.configuration import historical_task_composition

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures/reference.json").read_text()
)
UNAVAILABLE = RegisteredStateInventory(
    status="unavailable", reason="Not required by historical arithmetic"
)


@pytest.mark.parametrize("case", FIXTURE["estimates"])
def test_frozen_reference_estimates(case):
    observations = PhaseObservations.model_validate(
        case["observations"]
        | {
            "model_state": UNAVAILABLE,
            "loss_state": UNAVAILABLE,
            "optimizer_type": "sgd",
        }
    )
    result = estimate_historical_phase(observations)
    assert result.admission_bytes == case["admission_bytes"]
    assert result.diagnostic_bytes == case["diagnostic_bytes"]
    assert result.breakdown == case["breakdown"]


@pytest.mark.parametrize("case", FIXTURE["searches"])
def test_frozen_reference_batch_search(case):
    # This local binding is a unit-test harness, not a qualification manifest.
    profile = replace(
        historical_profile(),
        qualified_assemblies=frozenset({estimation_assembly_digest()}),
    )

    def mocked_probe(*args, **kwargs):
        sample = kwargs.get("input_sample", args[2] if len(args) > 2 else None)
        batch = sample.shape[0]
        return ProbeResult(
            mode="inference",
            model_forward=ForwardLayerReport(
                module_name="Synthetic",
                layers=[],
                total_param_bytes=case["params"],
                forward_output_bytes_sum=case["outputs"] * batch,
                forward_output_bytes_max=case["outputs"] * batch // 3,
            ),
            input_bytes=4 * batch,
            output_bytes=8 * batch,
            autograd_tape=AutogradTapeReport(
                unique_storage_count=2, total_saved_bytes=31 * batch
            ),
        )

    with (
        bind_preflight_estimator(profile),
        patch.object(
            batch_resolver, "probe_activation_footprint", side_effect=mocked_probe
        ),
    ):
        try:
            result = batch_resolver.resolve_inference_decision(
                torch.nn.Linear(2, 2),
                case["segmentation"],
                case["cap"],
                candidate_batches=case["candidates"],
                supplied_probe=torch.zeros(1, 2),
            )
            outcome = "accepted"
        except batch_resolver.BatchSearchRefused as exc:
            result = exc.decision
            outcome = "refused"
    assert outcome == case["outcome"]
    assert result.model_dump(mode="json") == case["decision"]


def test_unknown_assembly_is_not_implicitly_qualified(monkeypatch):
    import core.preflight_estimation as registry

    monkeypatch.setattr(registry, "estimation_assembly_digest", lambda: "f" * 64)
    with pytest.raises(ValueError, match="has not qualified"):
        historical_profile().identity()


def test_configuration_copy_is_explicit_and_does_not_mutate_source():
    original = {"task_name": "synthetic", "nested": {"value": 1}}
    before = deepcopy(original)
    updated = historical_task_composition(original)
    updated["nested"]["value"] = 2
    assert original == before
    assert updated["preflight_estimator"] == "legacy-078b23ca-preflight-v1"
    with pytest.raises(ValueError, match="different preflight estimator"):
        historical_task_composition({"preflight_estimator": "registered-state-v1"})


def test_installed_historical_provider_controls_fresh_cpu_probe_batch():
    """Exercise actual forward observations and discovery, without test qualification."""
    shared = torch.nn.Linear(2, 2)
    model = torch.nn.Sequential(shared, shared, shared, shared)
    sample = torch.zeros(1, 2)
    arguments = {
        "candidate_batches": (7, 4, 1),
        "supplied_probe": sample,
    }
    cap = 185 * 1024**2 + 256
    with bind_preflight_estimator(resolve_preflight_estimator(SELECTION)):
        historical = batch_resolver.resolve_inference_decision(
            model, None, cap, **arguments
        )
    native = batch_resolver.resolve_inference_decision(model, None, cap, **arguments)
    assert (
        historical.model_dump(mode="json") == FIXTURE["actual_cpu_search"]["decision"]
    )
    assert historical.batch_size == 4
    assert native.batch_size == 7

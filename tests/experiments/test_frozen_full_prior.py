"""The published Full treatment must retain the operator-frozen prior bytes."""

import json
from pathlib import Path

import pytest
import yaml

from experiments.shared.checksum_manifest import sha256_file
from experiments.tidmad.information_treatments.frozen_prior import full_analysis_policy
from experiments.tidmad.information_treatments.prepare_full import prepare_full
from experiments.tidmad.information_treatments.prior_binding import Prior, resolve_prior
from experiments.tidmad.main_fixed_workflow.full_binding import (
    verify_full_analysis_binding,
)

ROOT = Path(__file__).resolve().parents[2]


def test_training_order_advice_reaches_the_agent_that_owns_the_executable_field():
    """Moving the executable hint to proposal would leave ordering at shuffle."""
    advice = json.loads(
        (
            ROOT
            / "experiments/tidmad/information_treatments/full-prior-v8/advice.json"
        ).read_text()
    )
    tuner_advice = "\n".join(advice["tune"])
    assert 'order_strategy: "sequential"' in tuner_advice
    assert "published band-specific FCNet processed one file at a time" in tuner_advice
    assert all("order_strategy" not in item for item in advice["propose"])


@pytest.mark.parametrize("band", ["0-3", "4-9", "10-14", "15-19"])
def test_shared_prior_materializes_frozen_policy_and_refuses_budget_drift(
    tmp_path, band
):
    """A separately hashed operator policy must not override the frozen 600s budget."""
    receipt = prepare_full(ROOT, band, tmp_path / band)
    assert (
        receipt["advice_sha256"]
        == "3f20093dc894a0600c9cb491d4bd9350b4a09cef0f43e5a8d6fb712a71e81ac7"
    )
    assert full_analysis_policy(ROOT, band).resource_envelope.wall_time_budget_s == 600
    assert resolve_prior(ROOT, Prior.OFF).advice_path is None
    policy_path = Path(receipt["analysis_policy_path"])
    policy = yaml.safe_load(policy_path.read_text())
    policy["resource_envelope"]["wall_time_budget_s"] = 300
    policy_path.write_text(yaml.safe_dump(policy))
    with pytest.raises(ValueError, match="frozen V8"):
        verify_full_analysis_binding(
            ROOT,
            band=band,
            policy_path=policy_path,
            policy_sha256=sha256_file(policy_path),
            composition_path=Path(receipt["composition_path"]),
        )


def test_frozen_artifact_rejects_tampered_bytes_and_escape(tmp_path):
    from experiments.tidmad.information_treatments.frozen_prior import FrozenArtifact

    artifact = tmp_path / "policy.yaml"
    artifact.write_text("original")
    ref = FrozenArtifact(path="policy.yaml", sha256=sha256_file(artifact))
    artifact.write_text("changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        ref.verify(tmp_path)
    with pytest.raises(ValueError, match="inside its repository"):
        ref.model_copy(update={"path": "../policy.yaml"}).verify(tmp_path)

"""Focused witnesses for the 04B TIDMAD prerelease consumer contract."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSITION = ROOT / "tasks/tidmad/compositions/continuous_regression.yaml"


def test_continuous_composition_has_waveform_contract_and_blocking_health() -> None:
    from workflows.task_composition import compose_run_task_bindings

    composition = compose_run_task_bindings(str(COMPOSITION))
    assert composition.forward_contract.task_type == "regression"
    assert composition.forward_contract.input_shape == "[B, T] int64"
    assert composition.forward_contract.output_shape == "[B, T] float32"
    assert composition.forward_contract.num_classes == 0
    assert composition.metric.spec.id == "tidmad_denoising_score"
    assert composition.metric.spec.direction == "higher"
    health = yaml.safe_load(Path(composition.task_health_binding).read_text())
    dispositions = {g["gate_id"]: g["disposition"] for g in health["roster"]}
    assert dispositions["amplitude_collapse_blocking"] == "blocking"
    assert dispositions["output_diversity_blocking"] == "recording"
    assert dispositions["output_std_blocking"] == "recording"


def test_explicit_health_scope_is_distinct_from_task_peek_defaults() -> None:
    from execute_tools.dataset_config import DataScope

    assert list(DataScope.from_cli("15-19").file_indices) == [15, 16, 17, 18, 19]
    health = yaml.safe_load(
        (ROOT / "tasks/tidmad/framework_configs/health_regression.yaml").read_text()
    )
    assert health["health_peek_files"] == [3, 10, 17]


def test_advice_is_factual_and_does_not_lock_fcnet() -> None:
    advice = json.loads(
        (
            ROOT / "experiments/tidmad/prerelease-tidmad-proof-of-function/advice.json"
        ).read_text()
    )
    text = " ".join(advice["propose"])
    baseline = json.loads(
        (ROOT / "tasks/tidmad/reference_data/legacy_baseline_configs.json").read_text()
    )["fcnet"]
    assert baseline["model_cfg"]["segmentation_size"] == 40000
    assert baseline["model_cfg"]["latent_dims"] == [4000, 400, 40]
    assert baseline["loss_cfg"] == {
        "loss_type": "smooth_l1",
        "beta": 1.0,
        "reduction": "mean",
        "use_class_weights": False,
    }
    assert "40000 -> 4000 -> 400 -> 40" in text
    assert "SmoothL1" in text and "beta=1" in text
    assert "activations" in text and "must not be invented" in text
    assert "parameter count" not in text.lower() or "not a model lock" in " ".join(
        advice["tune"]
    )


def test_advice_digest_and_schema_are_verified_by_framework_loader() -> None:
    from workflows.run_one_iteration import load_advice_artifact

    path = ROOT / "experiments/tidmad/prerelease-tidmad-proof-of-function/advice.json"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    artifact = load_advice_artifact(str(path), declared_sha256=digest)
    assert set(artifact.content) == {"propose", "tune"}

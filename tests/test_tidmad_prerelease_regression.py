"""Focused witnesses for the 04B TIDMAD prerelease consumer contract."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
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


def _fake_checkout(tmp_path: Path, *, revision: str) -> tuple[Path, Path]:
    checkout = tmp_path / "fake-siderius"
    (checkout / "scripts/launch").mkdir(parents=True)
    (checkout / "configs/llm").mkdir(parents=True)
    (checkout / "configs/llm/openai_tiered_pro.json").write_text("{}")
    capture = tmp_path / "argv.txt"
    (checkout / "scripts/launch/run_chain.sh").write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$@" > "$CAPTURE"\n'
    )
    (checkout / "scripts/launch/run_chain.sh").chmod(0o755)
    shim = tmp_path / "git"
    shim.write_text(
        f"#!/usr/bin/env bash\nif [[ $1 == -C ]]; then echo {revision}; exit 0; fi\nexit 1\n"
    )
    shim.chmod(0o755)
    return checkout, capture


def _data_root(tmp_path: Path, *, tamper_anchor: bool = False) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    for index in range(15, 20):
        (data / f"abra_training_{index:04d}.h5").write_bytes(b"x")
        (data / f"abra_validation_{index:04d}.h5").write_bytes(b"x")
    anchor = ROOT / "tasks/tidmad/reference_data/segment_anchors.json"
    (data / "segment_anchors.json").write_bytes(
        anchor.read_bytes() + (b"x" if tamper_anchor else b"")
    )
    return data


def test_launcher_subprocess_binds_every_locked_value(tmp_path: Path) -> None:
    revision = "1aa96013335d0d16e2484439ef6dd7ae8c26b94d"
    checkout, capture = _fake_checkout(tmp_path, revision=revision)
    data = _data_root(tmp_path)
    workspace = tmp_path / "workspace"
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "CAPTURE": str(capture),
    }
    result = subprocess.run(
        [
            "bash",
            str(
                ROOT
                / "experiments/tidmad/prerelease-tidmad-proof-of-function/launch.sh"
            ),
            "--siderius-checkout",
            str(checkout),
            "--workspace",
            str(workspace),
            "--data_dir",
            str(data),
            "--dry-run",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    argv = capture.read_text().splitlines()

    def value(flag: str) -> str:
        return argv[argv.index(flag) + 1]

    assert value("--run_name") == "prerelease-tidmad-proof-of-function"
    assert value("--task_composition") == str(COMPOSITION)
    assert value("--llm_config") == str(checkout / "configs/llm/openai_tiered_pro.json")
    assert value("--num_iterations") == "10" and value("--max_rounds") == "2"
    assert value("--max_epochs") == "1" and value("--trial_max_epochs") == "1"
    assert value("--formal_max_epochs") == "1"
    assert value("--trial_portion") == "0.1" and value("--formal_portion") == "1.0"
    assert value("--train_portion") == "0.1" and value("--eval_portion") == "0.1"
    assert (
        value("--formal_train_portion") == "0.1"
        and value("--formal_eval_portion") == "1.0"
    )
    assert (
        value("--trial_time_budget_minutes") == "30"
        and value("--formal_time_budget_minutes") == "120"
    )
    assert (
        value("--trial_vram_budget_gb") == "16"
        and value("--formal_vram_budget_gb") == "16"
    )
    assert value("--formal_round_strategy") == "full_clone"
    assert "--force_formal_round" in argv
    assert value("--trial_time_admission_source") == "measured"
    assert value("--formal_time_admission_source") == "measured"
    assert value("--data_scope") == "15-19" and value("--health_gate_files") == "15-19"
    assert value("--order_strategy_override") == "sequential"
    assert value("--file_order_override") == "15,16,17,18,19"
    assert (
        "--force_fresh" in argv and "--no_auto_resume" in argv and "--dry-run" in argv
    )
    advice = ROOT / "experiments/tidmad/prerelease-tidmad-proof-of-function/advice.json"
    assert value("--advice") == str(advice)
    assert value("--advice_sha256") == hashlib.sha256(advice.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("override", "locked treatment"),
        ("nonempty", "fresh and empty"),
        ("anchor", "segment_anchors"),
        ("missing_anchor", "segment_anchors"),
        ("revision", "revision mismatch"),
        ("hdf5", "required TIDMAD file"),
    ],
)
def test_launcher_refuses_stale_inputs_and_overrides(
    tmp_path: Path, kind: str, expected: str
) -> None:
    revision = "1aa96013335d0d16e2484439ef6dd7ae8c26b94d"
    checkout, _ = _fake_checkout(
        tmp_path, revision=("wrong" if kind == "revision" else revision)
    )
    data = _data_root(tmp_path)
    launcher = ROOT / "experiments/tidmad/prerelease-tidmad-proof-of-function/launch.sh"
    workspace = tmp_path / "workspace"
    command = [
        "bash",
        str(launcher),
        "--siderius-checkout",
        str(checkout),
        "--workspace",
        str(workspace),
        "--data_dir",
        str(data),
    ]
    if kind == "override":
        command += ["--num_iterations", "99"]
    if kind == "nonempty":
        workspace.mkdir()
        (workspace / "x").write_text("x")
    if kind == "anchor":
        (data / "segment_anchors.json").write_text("tampered")
    if kind == "missing_anchor":
        (data / "segment_anchors.json").unlink()
    if kind == "hdf5":
        (data / "abra_training_0015.h5").unlink()
    result = subprocess.run(
        command,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert expected in result.stderr


def test_gold_regression_yaml_blobs_remain_unchanged() -> None:
    pairs = (
        (
            "tasks/tidmad/declared/task_config_regression.yaml",
            "campaigns/tidmad_gold/task/task_config_regression.yaml",
        ),
        (
            "tasks/tidmad/framework_configs/health_regression.yaml",
            "campaigns/tidmad_gold/task/task_health_regression.yaml",
        ),
        (
            "tasks/tidmad/framework_configs/proposal_regression.yaml",
            "campaigns/tidmad_gold/task/task_proposal_regression.yaml",
        ),
    )
    for task_path, gold_path in pairs:
        expected_sha = {
            "task_config_regression.yaml": "7eabe995fc1345ab0072ddc83625af22f12b412af790821f0f29685233406efe",
            "task_health_regression.yaml": "9d3fd2fa1ce9e58e2218f7ae34f4176af244077c3ba42b62919918aa45fad762",
            "task_proposal_regression.yaml": "fc35f7d69ef6027d14dc25ead22a9e2b7bb9e170230be97b83fffb525021e6b4",
        }[Path(gold_path).name]
        assert (
            hashlib.sha256((ROOT / gold_path).read_bytes()).hexdigest() == expected_sha
        )
        task = yaml.safe_load((ROOT / task_path).read_text())
        gold = yaml.safe_load((ROOT / gold_path).read_text())
        if "roster" in task:
            assert task["roster"] == gold["roster"]
        elif "forward_contract" in task:
            assert task["forward_contract"]["task_type"] == "regression"
            assert gold["forward_contract"]["task_type"] == "regression"
        else:
            assert task["output_contract_guidance"] == gold["output_contract_guidance"]

"""Scientific transform, source integrity and frozen selection boundaries."""

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from tasks.phyts_project8.dual_representation import dual_representation
from tasks.phyts_project8.tools.build_dual_representation import (
    ARRAY_PATHS,
    build,
    sha256,
)
from tasks.shared.prepared_regression import PreparedDeclaration

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("bin_index", [7, -9])
def test_complex_tone_preserves_frequency_sign_phase_and_energy(bin_index):
    length = 128
    phase = 0.37
    signal = np.exp(1j * (2 * np.pi * bin_index * np.arange(length) / length + phase))
    iq = np.stack([signal.real, signal.imag], axis=0)[None].astype(np.float32)
    result = dual_representation(iq)
    np.testing.assert_array_equal(result[:, :2], iq)
    spectrum = result[0, 2] + 1j * result[0, 3]
    assert np.argmax(np.abs(spectrum)) == bin_index % length
    np.testing.assert_allclose(
        spectrum[bin_index % length], np.sqrt(length) * np.exp(1j * phase), rtol=1e-6
    )
    np.testing.assert_allclose(np.fft.ifft(spectrum, norm="ortho"), signal, atol=2e-7)
    np.testing.assert_allclose(
        np.sum(abs(spectrum) ** 2), np.sum(abs(signal) ** 2), rtol=1e-6
    )


def test_transform_is_event_local_and_handles_constants():
    iq = np.random.default_rng(42).normal(size=(4, 2, 32)).astype(np.float32)
    all_at_once = dual_representation(iq)
    np.testing.assert_array_equal(
        all_at_once, np.concatenate([dual_representation(x[None]) for x in iq])
    )
    np.testing.assert_array_equal(
        dual_representation(np.zeros((1, 2, 32), np.float32)), 0
    )


@pytest.mark.parametrize("value", [np.nan, np.inf])
def test_nonfinite_input_is_refused(value):
    iq = np.zeros((1, 2, 32), np.float32)
    iq[0, 0, 0] = value
    with pytest.raises(ValueError, match="nonfinite"):
        dual_representation(iq)


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    rng = np.random.default_rng(17)
    for split, count in [("training", 30), ("evaluator/validation", 20)]:
        folder = root / split
        folder.mkdir(parents=True)
        np.save(
            folder / "inputs.npy", rng.normal(size=(count, 2, 32)).astype(np.float32)
        )
        np.save(folder / "targets.npy", np.arange(count, dtype=np.float32)[:, None])
    np.save(root / "evaluator/validation/loss_indices.npy", np.array([3, 17], np.int64))
    artifacts = [
        {
            "path": name,
            "bytes": (root / name).stat().st_size,
            "sha256": sha256(root / name),
        }
        for name in sorted(ARRAY_PATHS)
    ]
    (root / "manifest.json").write_text(json.dumps({"artifacts": artifacts}))
    declaration = PreparedDeclaration(
        task_id="phyts_project8_energy",
        manifest_sha256=sha256(root / "manifest.json"),
        train_count=30,
        validation_count=20,
        channels=2,
        length=32,
        loss_indices=(3, 17),
    )
    path = tmp_path / "declaration.json"
    path.write_text(declaration.model_dump_json())
    return root, path


def test_materialization_preserves_rows_targets_snapshot_and_source(source, tmp_path):
    root, declaration = source
    before = {name: sha256(root / name) for name in ARRAY_PATHS}
    output = tmp_path / "dual"
    receipt = build(root, declaration, output, batch=7)
    assert receipt["manifest_sha256"] == sha256(output / "manifest.json")
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["task_id"] == "phyts_project8_energy_dual"
    for split in ["training", "evaluator/validation"]:
        old = np.load(root / split / "inputs.npy")
        new = np.load(output / split / "inputs.npy")
        np.testing.assert_array_equal(new, dual_representation(old))
        assert sha256(root / split / "targets.npy") == sha256(
            output / split / "targets.npy"
        )
    assert sha256(root / "evaluator/validation/loss_indices.npy") == sha256(
        output / "evaluator/validation/loss_indices.npy"
    )
    assert before == {name: sha256(root / name) for name in ARRAY_PATHS}
    for artifact in manifest["artifacts"]:
        assert artifact["sha256"] == sha256(output / artifact["path"])
        assert (output / artifact["path"]).stat().st_mode & 0o222 == 0
    with pytest.raises(FileExistsError):
        build(root, declaration, output)


def test_corrupt_source_fails_before_output_creation(source, tmp_path):
    root, declaration = source
    with (root / "training/targets.npy").open("ab") as stream:
        stream.write(b"corrupt")
    output = tmp_path / "refused"
    with pytest.raises(ValueError, match="checksum"):
        build(root, declaration, output)
    assert not output.exists()


def test_new_task_requires_both_views_without_changing_old_contract():
    task = ROOT / "tasks/phyts_project8"
    new = yaml.safe_load(
        (task / "declared/dual_representation/task_config.yaml").read_text()
    )
    old = yaml.safe_load((task / "declared/task_config.yaml").read_text())
    assert (
        new["forward_contract"]["model_io"]["input"]["axes"][1]["dimension"]["fixed"]
        == 4
    )
    assert (
        old["forward_contract"]["model_io"]["input"]["axes"][1]["dimension"]["fixed"]
        == 2
    )
    assert (
        "both the supplied time-domain and frequency-domain representations"
        in new["task_description"]
    )
    assert (
        "discarding one representation does not satisfy the task"
        in new["task_description"]
    )


def test_composition_delivers_context_and_keeps_formal_budgets(tmp_path):
    import os
    import subprocess
    import sys

    script = """
import sys
from workflows.task_composition import compose_run_task_bindings
from execute_tools.task_data_path import ScopeBuildRequest
c = compose_run_task_bindings(sys.argv[1])
a = c.task_data_path
assert a.task_data_path_id == "phyts_project8_energy_dual"
assert a.declaration.channels == 4
r = ScopeBuildRequest(round_kind="formal", selection_strategy="snapshot", portion=1.0)
assert a.build_training_scope(r).row_count == 40000
assert a.build_eval_scope(r).row_count == 5000
assert a.build_eval_scope(r.model_copy(update={"portion":0.1})).row_count == 500
assert "both the supplied time-domain and frequency-domain representations" in c.task_description
assert "403 MHz" in c.task_description
assert c.metric.spec.id == "r2"
"""
    subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(ROOT / "tasks/phyts_project8/compositions/dual_representation.yaml"),
        ],
        cwd=tmp_path,
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
        check=True,
        timeout=60,
    )
    base = ROOT / "experiments/phyts_project8"
    old = json.loads((base / "main_fixed_workflow/workflow.json").read_text())
    new = json.loads(
        (base / "main_fixed_workflow_dual_representation/workflow.json").read_text()
    )
    assert new["parameters"] == old["parameters"]
    assert new["workflow_parameter_rules"] == old["workflow_parameter_rules"]
    treatment = yaml.safe_load(
        (
            base / "main_fixed_workflow_dual_representation/information_treatment.yaml"
        ).read_text()
    )
    assert treatment["advice"]["mode"] == "disabled"
    assert treatment["modules"]["data_analysis"]["siderius"] == "disabled"

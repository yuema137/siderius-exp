"""Counterfactual witnesses for checkpoint-based Stage-3 full inference."""

from __future__ import annotations

import os
from pathlib import Path

import h5py
import pytest

import campaigns.tidmad_gold.stage3.full_inference as full_inference
from campaigns.tidmad_gold.paths import GOLD_STAGE3_TASK_COMPOSITION_PATH
from campaigns.tidmad_gold.stage3.full_inference import (
    FullInferenceCandidate,
    FullInferenceError,
    run_full_inference,
)
from core.iteration_manifest import sha256_file
from core.sandbox_executor import sandbox_models_dir
from execute_tools.task_registration_scope import run_registration_scope
from execute_tools import task_data_path


FULL_SEGMENTS = 200
PSD_SAMPLES = 10_000_000


def _candidate(tmp_path: Path) -> FullInferenceCandidate:
    source = tmp_path / "source"
    base = source / "iteration_001" / "wavenet"
    models = Path(sandbox_models_dir(str(base)))
    models.mkdir(parents=True)
    checkpoint = models / "model_wavenet_expA_agent.pth"
    checkpoint.write_bytes(b"checkpoint")
    (models / "_OK_expA").write_text("ok\n", encoding="utf-8")
    return FullInferenceCandidate(
        band="0-3",
        source_workspace=str(source),
        source_base_dir=str(base),
        exp_id="expA",
        run_name="iter_001",
        model_type="wavenet",
        checkpoint_sha256=sha256_file(str(checkpoint)),
        model_config={"model_type": "wavenet"},
        loss_config={"loss_type": "ce"},
        inference_batch=7,
        file_indices=(0,),
    )


class _InferenceSandbox:
    emitted_segments = FULL_SEGMENTS
    calls: list[dict] = []

    def __init__(self, *, workspace: str, deliverable_naming, **kwargs) -> None:
        self.workspace = workspace
        self.naming = deliverable_naming
        Path(sandbox_models_dir(workspace)).mkdir(parents=True)

    def execute_inference(self, **kwargs):
        self.calls.append(kwargs)
        for index in kwargs["sample_set"]:
            name = self.naming.name(
                model_type=kwargs["model_type"],
                run_name=kwargs["run_name"],
                exp_id=kwargs["exp_id"],
                input_identity=index,
            )
            with h5py.File(os.path.join(self.workspace, name), "w") as handle:
                series = handle.create_group("timeseries")
                shape = (self.emitted_segments * PSD_SAMPLES,)
                for channel in ("channel0001", "channel0002"):
                    group = series.create_group(channel)
                    group.create_dataset(
                        "timeseries", shape=shape, dtype="int8", chunks=(1,)
                    )
        return {"status": "success"}


@pytest.fixture(autouse=True)
def _sandbox(monkeypatch: pytest.MonkeyPatch):
    _InferenceSandbox.calls = []
    _InferenceSandbox.emitted_segments = FULL_SEGMENTS
    monkeypatch.setattr(full_inference, "TidmadSandbox", _InferenceSandbox)
    monkeypatch.setattr(task_data_path, "_REGISTRY", {})
    monkeypatch.setattr(task_data_path, "_CONTENT", {})
    with run_registration_scope():
        yield


def test_winner_checkpoint_runs_exact_full_scope_inference(tmp_path: Path) -> None:
    """A 20-segment replay or a different inference batch fails this witness."""
    candidate = _candidate(tmp_path)

    paths = run_full_inference(
        candidate,
        output_root=str(tmp_path / "stage3"),
        data_dir=str(tmp_path),
        task_manifest=str(GOLD_STAGE3_TASK_COMPOSITION_PATH),
    )

    assert list(paths) == [0]
    assert Path(paths[0]).is_file()
    assert len(_InferenceSandbox.calls) == 1
    call = _InferenceSandbox.calls[0]
    assert call["sample_set"] == {0: list(range(FULL_SEGMENTS))}
    assert call["inference_batch"] == 7
    assert call["model_type"] == candidate.model_type
    assert call["m_cfg"] == candidate.model_config
    assert call["l_cfg"] == candidate.loss_config


def test_twenty_segment_deliverable_is_refused_before_scoring(tmp_path: Path) -> None:
    """The historical Stage-1 10% artifact cannot pass as a final result."""
    _InferenceSandbox.emitted_segments = 20

    with pytest.raises(FullInferenceError, match="incomplete 200-segment"):
        run_full_inference(
            _candidate(tmp_path),
            output_root=str(tmp_path / "stage3"),
            data_dir=str(tmp_path),
            task_manifest=str(GOLD_STAGE3_TASK_COMPOSITION_PATH),
        )

    assert not (tmp_path / "stage3" / "band_0-3").exists()


def test_missing_checkpoint_refuses_before_inference(tmp_path: Path) -> None:
    """Selection metadata alone cannot manufacture a replayable winner."""
    candidate = _candidate(tmp_path)
    checkpoint = (
        Path(sandbox_models_dir(candidate.source_base_dir))
        / "model_wavenet_expA_agent.pth"
    )
    checkpoint.unlink()

    with pytest.raises(FullInferenceError, match="missing checkpoint evidence"):
        run_full_inference(
            candidate,
            output_root=str(tmp_path / "stage3"),
            data_dir=str(tmp_path),
            task_manifest=str(GOLD_STAGE3_TASK_COMPOSITION_PATH),
        )

    assert _InferenceSandbox.calls == []


def test_changed_checkpoint_identity_refuses_before_inference(tmp_path: Path) -> None:
    """A checkpoint replaced after winner selection cannot be replayed."""
    candidate = _candidate(tmp_path)
    checkpoint = (
        Path(sandbox_models_dir(candidate.source_base_dir))
        / "model_wavenet_expA_agent.pth"
    )
    checkpoint.write_bytes(b"different checkpoint")

    with pytest.raises(FullInferenceError, match="checkpoint identity changed"):
        run_full_inference(
            candidate,
            output_root=str(tmp_path / "stage3"),
            data_dir=str(tmp_path),
            task_manifest=str(GOLD_STAGE3_TASK_COMPOSITION_PATH),
        )

    assert _InferenceSandbox.calls == []

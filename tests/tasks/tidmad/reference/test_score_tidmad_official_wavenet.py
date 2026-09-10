"""Task-owned contract tests for the official generalist WaveNet scorer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from execute_tools.dataset_config import load_dataset_profile
from tasks.tidmad.tools import score_tidmad_official_wavenet as scorer


def test_historical_output_name_remains_exact() -> None:
    """A renamed temporary artifact would disconnect inference from scoring."""
    assert (
        scorer.denoised_filename(7)
        == "abra_validation_denoised_wavenet_tidmad_official_0007.h5"
    )


def test_machine_and_dataset_inputs_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No developer checkout, checkpoint, data root, or work root may leak in."""
    monkeypatch.setattr(sys, "argv", ["score-tidmad-official-wavenet"])

    with pytest.raises(SystemExit) as exc_info:
        scorer.parse_args()

    assert exc_info.value.code == 2


def test_input_validation_uses_the_task_owned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Profile cardinality, rather than a framework TIDMAD constant, owns the scan."""
    repo = tmp_path / "tidmad"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    (repo / "network.py").touch()
    checkpoint = repo / "WaveNet_0_20.pth"
    checkpoint.touch()
    anchor_map = tmp_path / "anchors.json"
    anchor_map.touch()
    for index in range(2):
        (data / f"abra_validation_{index:04d}.h5").touch()

    full_profile = load_dataset_profile(scorer.DEFAULT_DATASET_PROFILE)
    profile = full_profile.model_copy(update={"partition_count": 2})
    segments_per_file = scorer.tidmad_topology(profile).dataset.segments_per_file
    monkeypatch.setattr(
        scorer,
        "load_anchor_map",
        lambda _: {
            "anchors": {"0": {}, "1": {}},
            "s_max": scorer.EXPECTED_S_MAX,
            "num_files": 2,
            "segments_per_file": segments_per_file,
        },
    )
    args = argparse.Namespace(
        batch_size=1,
        score_workers=1,
        tidmad_repo=repo,
        checkpoint=checkpoint,
        data_dir=data,
        anchor_map=anchor_map,
    )

    validated = scorer.validate_inputs(args, profile)

    assert validated["num_files"] == 2


def test_profile_and_anchor_cardinality_must_agree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plausible anchor map for another scope must fail before inference."""
    repo = tmp_path / "tidmad"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    (repo / "network.py").touch()
    checkpoint = repo / "WaveNet_0_20.pth"
    checkpoint.touch()
    anchor_map = tmp_path / "anchors.json"
    anchor_map.touch()
    for index in range(2):
        (data / f"abra_validation_{index:04d}.h5").touch()

    full_profile = load_dataset_profile(scorer.DEFAULT_DATASET_PROFILE)
    profile = full_profile.model_copy(update={"partition_count": 2})
    segments_per_file = scorer.tidmad_topology(profile).dataset.segments_per_file
    monkeypatch.setattr(
        scorer,
        "load_anchor_map",
        lambda _: {
            "anchors": {"0": {}, "1": {}},
            "s_max": scorer.EXPECTED_S_MAX,
            "num_files": 20,
            "segments_per_file": segments_per_file,
        },
    )
    args = argparse.Namespace(
        batch_size=1,
        score_workers=1,
        tidmad_repo=repo,
        checkpoint=checkpoint,
        data_dir=data,
        anchor_map=anchor_map,
    )

    with pytest.raises(ValueError, match="file count disagrees"):
        scorer.validate_inputs(args, profile)

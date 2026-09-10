"""Task-owned contract tests for the official band-split scorers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from execute_tools.dataset_config import load_dataset_profile
from tasks.tidmad.tools import score_tidmad_official_banded as scorer


def test_paper_bands_and_model_contracts_remain_exact() -> None:
    """A changed band or output kind would load or decode the wrong checkpoint."""
    assert scorer.BANDS == [(0, 4), (4, 10), (10, 15), (15, 20)]
    assert {
        key: (spec.checkpoint_prefix, spec.output_kind, spec.expected_class_name)
        for key, spec in scorer.MODEL_SPECS.items()
    } == {
        "punet": ("PUNet", "classifier", "PositionalUNet"),
        "fcnet": ("FCNet", "regressor", "AE"),
        "transformer": ("Transformer", "classifier", "TransformerModel"),
        "rnn": ("RNN", "classifier", "RNNSeq2Seq"),
    }


def test_historical_checkpoint_and_output_names_remain_exact() -> None:
    """Existing checkpoints and temporary outputs must remain discoverable."""
    fcnet = scorer.MODEL_SPECS["fcnet"]

    assert (
        scorer.checkpoint_path(Path("/checkpoints"), fcnet, (10, 15)).name
        == "FCNet_10_15.pth"
    )
    assert (
        scorer.denoised_filename("fcnet", 12)
        == "abra_validation_denoised_fcnet_tidmad_official_banded_0012.h5"
    )


def test_machine_inputs_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """No developer repository, dataset, checkpoint, or work path may leak in."""
    monkeypatch.setattr(sys, "argv", ["score-tidmad-official-banded"])

    with pytest.raises(SystemExit) as exc_info:
        scorer.parse_args()

    assert exc_info.value.code == 2


def test_paper_checkpoint_geometry_is_task_owned() -> None:
    """A different task profile must fail before any official checkpoint loads."""
    profile = load_dataset_profile(scorer.DEFAULT_DATASET_PROFILE)
    scorer.validate_official_profile(profile)

    incompatible = profile.model_copy(update={"partition_count": 19})
    with pytest.raises(ValueError, match="require 20 validation partitions"):
        scorer.validate_official_profile(incompatible)

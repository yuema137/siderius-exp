"""Input-only Full view must never publish the validation target channel."""

from pathlib import Path

import h5py
import numpy as np
import pytest

from experiments.tidmad.main_orchestrator import analysis_input_view


def test_build_input_view_copies_only_inputs(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[2]
    profile = root / "tasks/tidmad/resolved/dataset_profile.json"
    source = tmp_path / "private"
    source.mkdir()
    for index in range(4):
        with h5py.File(source / f"abra_validation_{index:04d}.h5", "w") as file:
            file.create_dataset(
                "timeseries/channel0001/timeseries",
                data=np.array([index, 2], dtype="i1"),
            )
            file.create_dataset(
                "timeseries/channel0002/timeseries", data=np.array([99, 99], dtype="i1")
            )
            file.attrs["secret"] = "must-not-copy"
    monkeypatch.setattr(analysis_input_view.os, "geteuid", lambda: 0)
    monkeypatch.setattr(analysis_input_view.os, "chown", lambda *_: None)
    output = tmp_path / "published"
    receipt = analysis_input_view.build_input_view(
        band="0-3",
        profile_path=profile,
        validation_dir=source,
        output_dir=output,
        read_gid=985,
    )
    assert receipt["input_only"] is True
    assert len(receipt["files"]) == 4
    for index in range(4):
        with h5py.File(output / "0-3" / f"abra_validation_{index:04d}.h5") as file:
            assert list(file["timeseries"]) == ["channel0001"]
            assert dict(file.attrs) == {}
            np.testing.assert_array_equal(
                file["timeseries/channel0001/timeseries"][:], [index, 2]
            )
    with pytest.raises(FileExistsError):
        analysis_input_view.build_input_view(
            band="0-3",
            profile_path=profile,
            validation_dir=source,
            output_dir=output,
            read_gid=985,
        )

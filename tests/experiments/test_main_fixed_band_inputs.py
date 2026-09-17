"""One-band data isolation and byte identity before a fixed-workflow launch."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from experiments.tidmad.main_fixed_workflow.band_inputs import BANDS, verify_band_inputs


def _prepared_band(tmp_path: Path, band: str) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    data = tmp_path / "band-data"
    data.mkdir()
    manifest = repository / "campaigns/tidmad_gold/inputs/q3_data_manifest.sha256"
    manifest.parent.mkdir(parents=True)
    lines = []
    for index in BANDS[band]:
        for family in ("training", "validation"):
            name = f"abra_{family}_{index:04d}.h5"
            content = f"{family}:{index}".encode()
            (data / name).write_bytes(content)
            lines.append(f"{hashlib.sha256(content).hexdigest()}  {name}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    anchor = repository / "tasks/tidmad/reference_data/segment_anchors.json"
    anchor.parent.mkdir(parents=True)
    anchor.write_bytes(b'{"approved":true}\n')
    (data / anchor.name).write_bytes(anchor.read_bytes())
    return repository, data


def test_main_band_accepts_only_complete_matching_file_pairs(tmp_path: Path) -> None:
    repository, data = _prepared_band(tmp_path, "0-3")
    receipt = verify_band_inputs(repository, data, "0-3")
    assert receipt["data_scope"] == receipt["health_gate_files"] == "0-3"
    assert len(receipt["file_sha256"]) == 8

    (data / "abra_validation_0002.h5").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_band_inputs(repository, data, "0-3")


def test_main_band_refuses_other_band_visibility_and_wrong_anchor(tmp_path: Path) -> None:
    repository, data = _prepared_band(tmp_path, "15-19")
    (data / "abra_training_0004.h5").write_bytes(b"other band")
    with pytest.raises(ValueError, match="outside band"):
        verify_band_inputs(repository, data, "15-19")

    (data / "abra_training_0004.h5").unlink()
    (data / "segment_anchors.json").write_bytes(b"wrong")
    with pytest.raises(ValueError, match="staged segment_anchors"):
        verify_band_inputs(repository, data, "15-19")

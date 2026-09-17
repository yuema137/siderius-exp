"""Verify one main fixed-workflow band against frozen TIDMAD input bytes."""

from __future__ import annotations

from pathlib import Path

from experiments.shared.checksum_manifest import sha256_file, verify_selected_files

BANDS: dict[str, tuple[int, ...]] = {
    "0-3": tuple(range(0, 4)),
    "4-9": tuple(range(4, 10)),
    "10-14": tuple(range(10, 15)),
    "15-19": tuple(range(15, 20)),
}


def verify_band_inputs(repository_root: Path, data_dir: Path, band: str) -> dict[str, object]:
    """Certify one band's file pairs and staged scoring anchor.

    The directory must expose only the selected band's TIDMAD HDF5 files so a
    single-band unit cannot read a different band's scientific data.
    """

    if band not in BANDS:
        raise ValueError(f"unsupported TIDMAD main band: {band}")
    names = {
        f"abra_{family}_{index:04d}.h5"
        for family in ("training", "validation")
        for index in BANDS[band]
    }
    visible = {path.name for path in data_dir.glob("abra_*.h5")}
    unexpected = visible - names
    if unexpected:
        raise ValueError(f"data directory exposes files outside band {band}: {sorted(unexpected)}")
    manifest = repository_root / "campaigns/tidmad_gold/inputs/q3_data_manifest.sha256"
    checksums = verify_selected_files(data_dir, manifest, names)
    reference_anchor = repository_root / "tasks/tidmad/reference_data/segment_anchors.json"
    staged_anchor = data_dir / "segment_anchors.json"
    anchor_digest = sha256_file(reference_anchor)
    if not staged_anchor.is_file() or sha256_file(staged_anchor) != anchor_digest:
        raise ValueError("staged segment_anchors.json differs from the committed anchor")
    return {
        "band": band,
        "data_scope": band,
        "health_gate_files": band,
        "data_manifest_sha256": sha256_file(manifest),
        "file_sha256": checksums,
        "segment_anchors_sha256": anchor_digest,
    }

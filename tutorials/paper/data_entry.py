"""Reuse existing machine data without downloading or copying raw files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from experiments.shared.checksum_manifest import verify_selected_files
from tasks.phyts_tess.tools.stage_data import main as stage_tess
from tutorials.paper.prepare_tess import TessSource
from tutorials.paper.runner import ROOT, disjoint


def _locations(project: Path, source: Path) -> tuple[Path, Path]:
    project, source = project.resolve(), source.resolve()
    binding = json.loads((project / "project.json").read_text())
    infra = Path(binding["infra_checkout"])
    if any(
        not disjoint(project, repo) or not disjoint(source, repo)
        for repo in (ROOT, infra)
    ):
        raise ValueError("project and raw data must remain outside source checkouts")
    if not source.is_dir():
        raise ValueError(
            f"existing data directory not found: {source}; use the download entry on other machines"
        )
    return project, source


def use_existing_tidmad(project: Path, source: Path) -> Path:
    """Expose eight symlinks and a local anchor; never copy or modify raw HDF5."""
    project, source = _locations(project, source)
    destination = project / "data/band-0-3"
    if not disjoint(source, destination):
        raise ValueError("shared source and project data view must be separate")
    names = {
        f"abra_{family}_{i:04d}.h5"
        for family in ("training", "validation")
        for i in range(4)
    }
    for name in names:
        link = destination / name
        if (link.exists() or link.is_symlink()) and (
            not link.is_symlink() or link.resolve() != (source / name).resolve()
        ):
            raise ValueError(f"existing data entry is not this source link: {link}")
    verify_selected_files(
        source, ROOT / "campaigns/tidmad_gold/inputs/q3_data_manifest.sha256", names
    )
    destination.mkdir(parents=True, exist_ok=True)
    anchor = destination / "segment_anchors.json"
    reference = ROOT / "tasks/tidmad/reference_data/segment_anchors.json"
    if not anchor.exists():
        with anchor.open("xb") as stream:
            stream.write(reference.read_bytes())
    for name in sorted(names):
        link = destination / name
        if not link.is_symlink():
            link.symlink_to(source / name)
    # Hash verification above owns raw bytes; verify the small local anchor here.
    if anchor.read_bytes() != reference.read_bytes() or {
        p.name for p in destination.iterdir()
    } != names | {anchor.name}:
        raise ValueError(
            "band view must expose exactly eight source links and the committed anchor"
        )
    return destination


def use_existing_tess(project: Path, source: Path) -> Path:
    """Read existing Parquet once and create only the required NPZ run format."""
    project, source = _locations(project, source)
    destination = project / "data/tess-data"
    if destination.exists():
        raise ValueError(
            "TESS run data already exists; reuse its data_dir, do not stage again"
        )
    declared = TessSource.model_validate_json(
        (ROOT / "tutorials/paper/configs/tess_source.json").read_text()
    )
    for relative, expected in declared.files.items():
        path = source / Path(relative).name
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(
                    f"existing TESS source differs from the pinned release: {path.name}"
                )
    stage_tess(["--source", str(source), "--data_dir", str(destination)])
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=("tess", "tidmad"), required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    prepare = use_existing_tess if args.task == "tess" else use_existing_tidmad
    print("Run data:", prepare(args.project, args.source))


if __name__ == "__main__":
    main()

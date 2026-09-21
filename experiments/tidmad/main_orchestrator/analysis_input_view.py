"""Build a read-only Full analysis view containing validation inputs only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import h5py
from execute_tools.dataset_config import DatasetProfile, tidmad_topology

from experiments.tidmad.main_fixed_workflow.band_inputs import BANDS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_input_view(
    *,
    band: str,
    profile_path: Path,
    validation_dir: Path,
    output_dir: Path,
    read_gid: int,
) -> dict:
    """Copy only the task-declared input dataset; never copy targets or attrs."""
    if band not in BANDS:
        raise ValueError(f"unsupported band {band!r}")
    if os.geteuid() != 0:
        raise PermissionError(
            "input-only view construction requires the operator account"
        )
    profile = DatasetProfile.model_validate_json(profile_path.read_text())
    source_root = validation_dir.resolve(strict=True)
    output_root = output_dir.resolve()
    if output_root == source_root or output_root.is_relative_to(source_root):
        raise ValueError("input-only view must be outside private validation")
    topology = tidmad_topology(profile)
    input_path = f"timeseries/{topology.channels.input_channel}/timeseries"
    destination = output_dir / band
    temporary = output_dir / f".{band}.building"
    if destination.exists() or temporary.exists():
        raise FileExistsError(
            "input-only view already exists or has an incomplete build"
        )
    output_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
    os.chown(output_dir, 0, read_gid)
    output_dir.chmod(0o750)
    temporary.mkdir(mode=0o700)
    files = []
    for index in BANDS[band]:
        name = topology.dataset.validation_file_name(index)
        source = validation_dir / name
        target = temporary / name
        with h5py.File(source, "r") as original, h5py.File(target, "w") as view:
            dataset = original[input_path]
            if dataset.ndim != 1:
                raise ValueError(f"validation input is not one-dimensional: {name}")
            original.copy(input_path, view, name=input_path)
            assert tuple(view.keys()) == ("timeseries",)
            assert tuple(view["timeseries"].keys()) == (
                topology.channels.input_channel,
            )
            assert tuple(
                view[f"timeseries/{topology.channels.input_channel}"].keys()
            ) == ("timeseries",)
            copied = view[input_path]
            for name_of_attribute in tuple(copied.attrs):
                del copied.attrs[name_of_attribute]
            if any(
                len(view[path].attrs)
                for path in (
                    "/",
                    "timeseries",
                    f"timeseries/{topology.channels.input_channel}",
                    input_path,
                )
            ):
                raise ValueError(f"input-only view retained an HDF5 attribute: {name}")
            if copied.shape != dataset.shape or copied.dtype != dataset.dtype:
                raise ValueError(
                    f"copied validation input differs in shape or dtype: {name}"
                )
        os.chown(target, 0, read_gid)
        target.chmod(0o440)
        files.append(
            {
                "name": name,
                "bytes": target.stat().st_size,
                "sha256": _sha256(target),
            }
        )
    os.chown(temporary, 0, read_gid)
    temporary.chmod(0o550)
    temporary.rename(destination)
    return {
        "band": band,
        "output": str(destination),
        "input_only": True,
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--band", choices=tuple(BANDS), required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--validation-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--read-gid", type=int, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build_input_view(
                band=args.band,
                profile_path=args.profile,
                validation_dir=args.validation_dir,
                output_dir=args.output_dir,
                read_gid=args.read_gid,
            )
        )
    )


if __name__ == "__main__":
    main()

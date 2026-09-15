"""Prepare identical public inputs while keeping evaluation truth private."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

import h5py

from .io import atomic_write_json, fsync_directory, sha256_file
from .model import DEVELOPMENT_FILE_BY_BAND, DEVELOPMENT_FILES, TRAINING_FILES


def _manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            entries[name] = digest
    return entries


def _verified_copy(source: Path, destination: Path, expected: str) -> None:
    if sha256_file(source) != expected:
        raise ValueError(f"source checksum mismatch: {source.name}")
    descriptor, raw = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(raw)
    try:
        shutil.copyfile(source, temporary)
        if sha256_file(temporary) != expected:
            raise RuntimeError(f"copied bytes differ: {source.name}")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _copy_validation_input(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale preparation file: {temporary}")
    try:
        with h5py.File(source, "r") as raw, h5py.File(temporary, "x") as public:
            if "timeseries/channel0001" not in raw:
                raise ValueError(f"input channel missing: {source}")
            # Root attributes encode release identity, including the original
            # file number and creation time. They are irrelevant to inference
            # and would let a candidate recover the evaluator's hidden index.
            group = public.require_group("timeseries")
            for key, value in raw["timeseries"].attrs.items():
                group.attrs[key] = value
            raw.copy("timeseries/channel0001", group, name="channel0001")
            public.flush()
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(
    source_root: Path,
    data_root: Path,
    manifest_path: Path,
    private_group: str | None = None,
) -> None:
    """Copy a verified raw release into public/private machine-owned views."""

    source_root = source_root.resolve(strict=True)
    data_root = data_root.resolve(strict=True)
    if source_root == data_root:
        raise ValueError("raw staging source must be a dedicated subdirectory")
    source_root.chmod(0o700)
    targets = {
        "training": data_root / "public-training",
        "development_input": data_root / "public-development",
        "development_truth": data_root / "private-development",
        "validation_input": data_root / "private-validation-input",
        "validation_truth": data_root / "private-validation",
    }
    if any(path.exists() for path in targets.values()):
        raise FileExistsError("prepared data targets must all be absent")
    entries = _manifest(manifest_path)
    for path in targets.values():
        path.mkdir(mode=0o700)
    try:
        public_development_manifest: dict[str, str] = {}
        private_validation_input_manifest: dict[str, str] = {}
        for index in TRAINING_FILES:
            training_name = f"abra_training_{index:04d}.h5"
            _verified_copy(
                source_root / training_name,
                targets["training"] / training_name,
                entries[training_name],
            )
        for index in DEVELOPMENT_FILES:
            training_name = f"abra_training_{index:04d}.h5"
            development_name = f"abra_validation_{index:04d}.h5"
            _verified_copy(
                source_root / training_name,
                targets["development_truth"] / development_name,
                entries[training_name],
            )
            band = next(
                band for band, held_out in DEVELOPMENT_FILE_BY_BAND.items() if held_out == index
            )
            public_development = targets["development_input"] / f"development-band-{band}.h5"
            _copy_validation_input(source_root / training_name, public_development)
            with h5py.File(public_development, "r") as prepared:
                if "timeseries/channel0002" in prepared:
                    raise RuntimeError(f"development truth leaked into {public_development}")
            public_development_manifest[public_development.name] = sha256_file(public_development)
        for index in range(20):
            validation_name = f"abra_validation_{index:04d}.h5"
            _verified_copy(
                source_root / validation_name,
                targets["validation_truth"] / validation_name,
                entries[validation_name],
            )
            private_validation_input = targets["validation_input"] / validation_name
            _copy_validation_input(source_root / validation_name, private_validation_input)
            with h5py.File(private_validation_input, "r") as prepared:
                if "timeseries/channel0002" in prepared:
                    raise RuntimeError(f"evaluation truth leaked into {private_validation_input}")
            private_validation_input_manifest[validation_name] = sha256_file(
                private_validation_input
            )
        atomic_write_json(
            data_root / "public-development-manifest.json",
            public_development_manifest,
        )
        atomic_write_json(
            data_root / "private-validation-input-manifest.json",
            private_validation_input_manifest,
        )
        for path in (*targets.values(),):
            is_private = path in {
                targets["development_truth"],
                targets["validation_input"],
                targets["validation_truth"],
            }
            for child in path.iterdir():
                child.chmod(0o440 if is_private else 0o444)
                if is_private and private_group:
                    shutil.chown(child, user="root", group=private_group)
            path.chmod(0o550 if is_private else 0o555)
        if private_group:
            for key in (
                "development_truth",
                "validation_input",
                "validation_truth",
            ):
                shutil.chown(targets[key], user="root", group=private_group)
    except BaseException:
        for path in targets.values():
            if path.exists():
                shutil.rmtree(path)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=Path("/data"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("/opt/tidmad-evaluator/assets/data_manifest.sha256"),
    )
    parser.add_argument("--private-group", default="baseline-evaluator")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("data preparation must run as root")
    prepare(args.source_root, args.data_root, args.manifest, args.private_group)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Prepare identical public inputs while keeping evaluation truth private."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

import h5py

from .io import atomic_write_json, fsync_directory, sha256_file
from .model import ALL_FILE_INDICES


def _manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            entries[name] = digest
    return entries


def _staged_indices(entries: dict[str, str]) -> tuple[int, ...]:
    """Derive one complete training/validation file scope from frozen digests."""

    allowed = set(ALL_FILE_INDICES)
    training = {
        index for index in allowed if f"abra_training_{index:04d}.h5" in entries
    }
    validation = {
        index for index in allowed if f"abra_validation_{index:04d}.h5" in entries
    }
    expected_names = {
        f"abra_{kind}_{index:04d}.h5"
        for index in training | validation
        for kind in ("training", "validation")
    }
    if not training or training != validation or set(entries) != expected_names:
        raise ValueError(
            "data manifest must contain exactly matching train/validation files"
        )
    return tuple(sorted(training))


def _verified_copy(source: Path, destination: Path, expected: str) -> None:
    if sha256_file(source) != expected:
        raise ValueError(f"source checksum mismatch: {source.name}")
    descriptor, raw = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
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


def _training_pool(
    path: Path, staged: tuple[int, ...]
) -> tuple[int, dict[int, list[int]]]:
    """Validate the task-owned, fixed per-file training selection."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "tidmad_training_pool_v1":
        raise ValueError("unsupported frozen training pool manifest")
    length = payload.get("psd_segment_length")
    per_file = payload.get("segments_per_file")
    portion = payload.get("source_portion")
    if not isinstance(length, int) or length <= 0 or per_file != 200 or portion != 0.1:
        raise ValueError("invalid frozen training pool geometry or portion")
    selected = payload.get("sample_set")
    if not isinstance(selected, dict) or set(selected) != {str(i) for i in range(20)}:
        raise ValueError("frozen training pool does not cover all training files")
    count = round(per_file * portion)
    for key, indices in selected.items():
        if (
            not isinstance(indices, list)
            or len(indices) != count
            or any(not isinstance(i, int) or i < 0 or i >= per_file for i in indices)
            or len(set(indices)) != count
        ):
            raise ValueError(f"invalid frozen training indices for file {key}")
    return length, {index: selected[str(index)] for index in staged}


def _required_pool(unit_path: Path, supplied: Path | None) -> Path | None:
    """A single-band bundle makes its frozen pool mandatory, not a remembered flag."""

    if not unit_path.is_file():
        return supplied
    unit = json.loads(unit_path.read_text(encoding="utf-8"))
    expected = unit.get("training_pool_sha256")
    if expected is None:
        return supplied
    if supplied is None:
        raise ValueError("single-band unit requires --training-pool-manifest")
    if sha256_file(supplied) != expected:
        raise ValueError("training pool manifest does not match the frozen unit")
    return supplied


def _copy_training_pool(
    source: Path, destination: Path, indices: list[int], length: int
) -> None:
    """Expose only selected raw/clean PSD segments; preserve exact sample bytes."""

    temporary = destination.with_name(f".{destination.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale preparation file: {temporary}")
    try:
        with h5py.File(source, "r") as raw, h5py.File(temporary, "x") as public:
            timeseries = public.require_group("timeseries")
            for channel in ("channel0001", "channel0002"):
                path = f"timeseries/{channel}/timeseries"
                if path not in raw:
                    raise ValueError(
                        f"training channel missing: {source.name}:{channel}"
                    )
                original = raw[path]
                if (
                    len(original.shape) != 1
                    or original.shape[0] < (max(indices) + 1) * length
                ):
                    raise ValueError(
                        f"training file too short for frozen pool: {source.name}"
                    )
                group = timeseries.create_group(channel)
                compact = group.create_dataset(
                    "timeseries",
                    shape=(len(indices) * length,),
                    dtype=original.dtype,
                    chunks=(min(length, 1_000_000),),
                    compression="lzf",
                )
                for local, original_index in enumerate(indices):
                    compact[local * length : (local + 1) * length] = original[
                        original_index * length : (original_index + 1) * length
                    ]
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
    training_pool_manifest: Path | None = None,
) -> None:
    """Copy a verified raw release into public/private machine-owned views."""

    source_root = source_root.resolve(strict=True)
    data_root = data_root.resolve(strict=True)
    if source_root == data_root:
        raise ValueError("raw staging source must be a dedicated subdirectory")
    source_root.chmod(0o700)
    targets = {
        "training": data_root / "public-training",
        "evaluation_input": data_root / "private-validation-input",
        "evaluation_truth": data_root / "private-validation",
    }
    if any(path.exists() for path in targets.values()):
        raise FileExistsError("prepared data targets must all be absent")
    entries = _manifest(manifest_path)
    indices = _staged_indices(entries)
    pool = (
        _training_pool(training_pool_manifest, indices)
        if training_pool_manifest
        else None
    )
    for path in targets.values():
        path.mkdir(mode=0o700)
    try:
        private_validation_input_manifest: dict[str, str] = {}
        public_training_manifest: dict[str, str] = {}
        for index in indices:
            training_name = f"abra_training_{index:04d}.h5"
            source = source_root / training_name
            destination = targets["training"] / training_name
            if pool is None:
                _verified_copy(source, destination, entries[training_name])
            else:
                if sha256_file(source) != entries[training_name]:
                    raise ValueError(f"source checksum mismatch: {training_name}")
                _copy_training_pool(source, destination, pool[1][index], pool[0])
            public_training_manifest[training_name] = sha256_file(destination)
        atomic_write_json(
            data_root / "public-training-manifest.json", public_training_manifest
        )
        for index in indices:
            validation_name = f"abra_validation_{index:04d}.h5"
            _verified_copy(
                source_root / validation_name,
                targets["evaluation_truth"] / validation_name,
                entries[validation_name],
            )
            private_validation_input = targets["evaluation_input"] / validation_name
            _copy_validation_input(
                source_root / validation_name, private_validation_input
            )
            with h5py.File(private_validation_input, "r") as prepared:
                if "timeseries/channel0002" in prepared:
                    raise RuntimeError(
                        f"evaluation truth leaked into {private_validation_input}"
                    )
            private_validation_input_manifest[validation_name] = sha256_file(
                private_validation_input
            )
        atomic_write_json(
            data_root / "private-validation-input-manifest.json",
            private_validation_input_manifest,
        )
        for path in (*targets.values(),):
            is_private = path in {
                targets["evaluation_input"],
                targets["evaluation_truth"],
            }
            for child in path.iterdir():
                child.chmod(0o440 if is_private else 0o444)
                if is_private and private_group:
                    shutil.chown(child, user="root", group=private_group)
            path.chmod(0o550 if is_private else 0o555)
        if private_group:
            for key in ("evaluation_input", "evaluation_truth"):
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
    parser.add_argument("--training-pool-manifest", type=Path)
    parser.add_argument(
        "--unit",
        type=Path,
        default=Path("/opt/tidmad-evaluator/assets/unit.json"),
    )
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("data preparation must run as root")
    prepare(
        args.source_root,
        args.data_root,
        args.manifest,
        args.private_group,
        _required_pool(args.unit, args.training_pool_manifest),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

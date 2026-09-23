"""Build a new immutable view from an explicitly pinned prepared I/Q dataset.

    python -m tasks.phyts_project8.tools.build_dual_representation \
        --source /data/project8-time --declaration /code/prepared.json \
        --output /data/project8-dual-v1

This offline operator tool reads both splits. Its output retains the evaluator
directory boundary; deployment must apply the same access policy as its source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from tasks.phyts_project8.dual_representation import (
    CHANNEL_NAMES,
    TRANSFORM_ID,
    dual_representation,
)
from tasks.shared.prepared_regression import PreparedDeclaration

ARRAY_PATHS = frozenset(
    {
        "training/inputs.npy",
        "training/targets.npy",
        "evaluator/validation/inputs.npy",
        "evaluator/validation/targets.npy",
        "evaluator/validation/loss_indices.npy",
    }
)


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SourceManifest(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    artifacts: tuple[Artifact, ...]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_source(source: Path, declaration: PreparedDeclaration) -> SourceManifest:
    if declaration.task_id != "phyts_project8_energy" or declaration.channels != 2:
        raise ValueError("source must be the two-channel Project8 prepared task")
    manifest_path = source / "manifest.json"
    if sha256(manifest_path) != declaration.manifest_sha256:
        raise ValueError("source manifest differs from the pinned declaration")
    manifest = SourceManifest.model_validate_json(manifest_path.read_bytes())
    if (
        len(manifest.artifacts) != 5
        or {a.path for a in manifest.artifacts} != ARRAY_PATHS
    ):
        raise ValueError(
            "source manifest must contain exactly the five prepared arrays"
        )
    for artifact in manifest.artifacts:
        relative = PurePosixPath(artifact.path)
        path = source / relative
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError(f"source array escapes the prepared directory: {relative}")
        if path.stat().st_size != artifact.bytes or sha256(path) != artifact.sha256:
            raise ValueError(f"source array checksum mismatch: {relative}")
    return manifest


def build_split(
    source: Path, destination: Path, count: int, length: int, batch: int
) -> None:
    inputs = np.load(source / "inputs.npy", mmap_mode="r", allow_pickle=False)
    targets = np.load(source / "targets.npy", mmap_mode="r", allow_pickle=False)
    if inputs.dtype != np.float32 or inputs.shape != (count, 2, length):
        raise ValueError("source input shape/dtype differs from its declaration")
    if (
        targets.dtype != np.float32
        or targets.shape != (count, 1)
        or not np.isfinite(targets).all()
    ):
        raise ValueError("source target shape/dtype/values differ from the contract")
    destination.mkdir(parents=True)
    output = np.lib.format.open_memmap(
        destination / "inputs.npy",
        mode="w+",
        dtype=np.float32,
        shape=(count, 4, length),
    )
    for start in range(0, count, batch):
        output[start : start + batch] = dual_representation(
            inputs[start : start + batch]
        )
    output.flush()
    del output
    shutil.copyfile(source / "targets.npy", destination / "targets.npy")


def build(source: Path, declaration_path: Path, output: Path, batch: int = 32) -> dict:
    if batch < 1:
        raise ValueError("batch must be positive")
    if output.exists() or output.is_symlink():
        raise FileExistsError("refusing to overwrite an existing prepared view")
    declaration = PreparedDeclaration.model_validate_json(declaration_path.read_bytes())
    verify_source(source, declaration)
    indices = np.load(
        source / "evaluator/validation/loss_indices.npy", allow_pickle=False
    )
    if indices.dtype != np.int64 or not np.array_equal(
        indices, declaration.loss_indices
    ):
        raise ValueError(
            "source validation snapshot differs from the frozen declaration"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".project8-dual-", dir=output.parent
    ) as temporary:
        staging = Path(temporary) / "view"
        for split, count in [
            ("training", declaration.train_count),
            ("evaluator/validation", declaration.validation_count),
        ]:
            build_split(
                source / split, staging / split, count, declaration.length, batch
            )
        shutil.copyfile(
            source / "evaluator/validation/loss_indices.npy",
            staging / "evaluator/validation/loss_indices.npy",
        )
        artifacts = [
            Artifact(
                path=name,
                bytes=(staging / name).stat().st_size,
                sha256=sha256(staging / name),
            )
            for name in sorted(ARRAY_PATHS)
        ]
        manifest = {
            "version": "project8-dual-representation-v1",
            "task_id": "phyts_project8_energy_dual",
            "source_manifest_sha256": declaration.manifest_sha256,
            "source_declaration_sha256": sha256(declaration_path),
            "transform": {
                "id": TRANSFORM_ID,
                "channels": CHANNEL_NAMES,
                "definition": "fft(time_I + 1j*time_Q, norm='ortho'); full unshifted complex spectrum",
                "frequency_axis": "numpy.fft.fftfreq(length, d=1/403000000); units Hz",
                "time_channels": "bitwise unchanged prepared float32 source I/Q",
                "frequency_channels": "float64 transform; real/imag cast to float32; no further scaling",
                "length": declaration.length,
                "numpy_version": np.__version__,
                "implementation_sha256": sha256(
                    Path(__file__).resolve().parents[1] / "dual_representation.py"
                ),
            },
            "populations": {
                "train": declaration.train_count,
                "validation": declaration.validation_count,
            },
            "split_policy": "preserve original row order, physical targets, and frozen loss-validation indices; no test",
            "artifacts": [a.model_dump() for a in artifacts],
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (staging / "SHA256SUMS").write_text(
            "".join(f"{a.sha256}  {a.path}\n" for a in artifacts)
        )
        for path in staging.rglob("*"):
            if path.is_file():
                path.chmod(0o444)
        if output.exists():
            raise FileExistsError("prepared output appeared during materialization")
        staging.rename(output)
    return {
        "output": str(output),
        "manifest_sha256": sha256(output / "manifest.json"),
        "artifacts": len(artifacts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.source, args.declaration, args.output, args.batch), indent=2
        )
    )


if __name__ == "__main__":
    main()

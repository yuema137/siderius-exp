#!/usr/bin/env python3
"""Stage the PhyTS TESS train and validation light curves into a run data root.

This is the operative test-split isolation. The data path's type-level
refusal (``TessSplit`` admits ``train`` and ``val`` only) declares that no
scope can name the held-out population; it does not stop arbitrary generated
code from opening a file that happens to sit in the same directory. Keeping
the test split OUT of ``--data_dir`` is what makes that impossible, and that
is this tool's job.

It also performs the one-time parquet to npz conversion. Reading parquet
needs ``pyarrow``, which siderius-exp does not declare as a dependency, and a
per-epoch reparse of a variable-length list column is slower than a lazily
decompressed archive. RAW flux is stored: ``normalize_curve`` in the data
path stays the single preprocessing authority, so this tool cannot quietly
become a second one.

Because the conversion needs pyarrow and the run does not, run this tool with
pyarrow supplied for the duration::

    uv run --no-project --with pyarrow --with numpy \\
        python tasks/phyts_tess/tools/stage_data.py \\
            --source /path/to/PhyTS/TESS/split \\
            --data_dir /path/to/run-data

Everything afterwards uses the checkout's own ``.venv/bin/python``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

import numpy as np

PACK_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PACK_ROOT / "data" / "manifests" / "rotation_identity.csv"

#: The only two splits a run may see. Named explicitly rather than globbed:
#: a glob over the source directory is exactly how a test file gets copied by
#: accident.
STAGED_SPLITS = ("train", "val")
SOURCE_FILENAME = "tess_regression_{split}.parquet"
STAGED_FILENAME = "tess_rotation_{split}.npz"

#: Anything matching these in the destination means the directory is not a
#: clean run data root. Refusing is the point.
FORBIDDEN_SUBSTRINGS = ("test",)


def _manifest_keys() -> dict[str, set[str]]:
    """``{split: {"gaia:sector", ...}}`` from the committed identity manifest."""
    keys: dict[str, set[str]] = {}
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            keys.setdefault(row["split"], set()).add(
                f"{row['gaia_id']}:{row['sector']}"
            )
    return keys


def _refuse_existing_test_artifacts(data_dir: Path) -> None:
    offenders = sorted(
        path.name
        for path in data_dir.glob("*")
        if any(token in path.name.lower() for token in FORBIDDEN_SUBSTRINGS)
    )
    if offenders:
        raise SystemExit(
            f"refusing to stage into {data_dir}: it already contains {offenders}. "
            "A PhyTS TESS run data root must never hold the held-out test "
            "population. Use a clean directory."
        )


def _convert(origin: Path, target: Path, expected: set[str], split: str) -> None:
    """Parquet to npz, refusing any population that is not the pinned one."""
    import pyarrow.parquet as pq

    table = pq.read_table(origin, columns=["GaiaID", "sector", "flux"])
    curves: dict[str, np.ndarray] = {}
    for gaia, sector, flux in zip(
        table.column("GaiaID").to_pylist(),
        table.column("sector").to_pylist(),
        table.column("flux").to_pylist(),
        strict=True,
    ):
        curves[f"{int(gaia)}:{int(sector)}"] = np.asarray(flux, dtype=np.float32)

    observed = set(curves)
    if observed != expected:
        missing = sorted(expected - observed)[:3]
        extra = sorted(observed - expected)[:3]
        raise SystemExit(
            f"staged {split} population does not match the committed identity "
            f"manifest: {len(expected)} declared, {len(observed)} present, "
            f"first missing {missing}, first unexpected {extra}. The source data "
            "is not this task package's pinned population; do not run against it."
        )
    empty = sorted(key for key, value in curves.items() if value.size == 0)
    if empty:
        raise SystemExit(
            f"staged {split} carries {len(empty)} empty curves, e.g. {empty[:3]}"
        )
    np.savez_compressed(target, **curves)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        help="Directory holding the released tess_regression_{split}.parquet files.",
    )
    parser.add_argument(
        "--data_dir",
        required=True,
        help="Run data root to create. Must not already contain test artifacts.",
    )
    args = parser.parse_args(argv)

    source = Path(args.source).expanduser().resolve()
    data_dir = Path(args.data_dir).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"--source is not a directory: {source}")
    if source == data_dir:
        raise SystemExit(
            "--source and --data_dir must differ; staging in place would leave the "
            "test parquet beside the staged splits."
        )

    data_dir.mkdir(parents=True, exist_ok=True)
    _refuse_existing_test_artifacts(data_dir)

    keys = _manifest_keys()
    print(f"identity manifest: {MANIFEST}")
    print(f"  sha256 {hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}")
    for split in STAGED_SPLITS:
        origin = source / SOURCE_FILENAME.format(split=split)
        if not origin.is_file():
            raise SystemExit(f"source split not found: {origin}")
        target = data_dir / STAGED_FILENAME.format(split=split)
        _convert(origin, target, keys[split], split)
        size_mb = target.stat().st_size / (1024 * 1024)
        print(
            f"staged {split}: {len(keys[split])} curves -> {target} ({size_mb:.1f} MiB)"
        )

    print(f"\ndata root ready: {data_dir}")
    print(
        "the held-out test split was NOT staged and must stay outside this directory."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

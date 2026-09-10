"""Compare FCNet and collapsed-baseline diversity across TIDMAD files.

This task-owned diagnostic reads historical denoised artifacts. It deliberately
keeps their filename conventions instead of using the current producer naming
contract, because the files predate that contract.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, cast

import h5py
import numpy as np

NUM_FILES = 20
MV_PER_LSB = 40.0 / 128.0
PEEK_SAMPLES = 1_000_000


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dir",
        type=Path,
        required=True,
        help="Directory containing abra_validation_NNNN.h5 target files.",
    )
    parser.add_argument(
        "--fcnet-dir",
        type=Path,
        required=True,
        help="Primary directory containing FCNet denoised artifacts.",
    )
    parser.add_argument(
        "--fcnet-fallback-dir",
        type=Path,
        help="Optional fallback directory for missing FCNet artifacts.",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        required=True,
        help="Directory containing historical collapsed WaveNet artifacts.",
    )
    parser.add_argument(
        "--baseline-exp-id",
        default="1784177030",
        help="Historical experiment id embedded in baseline artifact names.",
    )
    return parser.parse_args()


def fcnet_path(
    file_index: int,
    *,
    primary_dir: Path,
    fallback_dir: Path | None,
) -> Path:
    """Resolve a historical FCNet artifact, preferring the complete scan."""
    filename = f"abra_validation_denoised_fcnet_{file_index:04d}.h5"
    primary = primary_dir / filename
    if primary.exists() or fallback_dir is None:
        return primary
    return fallback_dir / filename


def baseline_path(file_index: int, *, directory: Path, exp_id: str) -> Path:
    """Return the historical paper-spec WaveNet artifact path."""
    return directory / (
        "abra_validation_denoised_wavenet_baseline_wavenet_baseline_wavenet_"
        f"{exp_id}_{file_index:04d}.h5"
    )


def target_path(file_index: int, *, directory: Path) -> Path:
    return directory / f"abra_validation_{file_index:04d}.h5"


def read_channel(path: Path, channel: str, n_samples: int) -> np.ndarray:
    """Read one TIDMAD channel prefix from an HDF5 artifact."""
    with h5py.File(path, "r") as handle:
        node: Any = handle
        for key in ("timeseries", channel, "timeseries"):
            node = node[key]
        dataset = cast(h5py.Dataset, node)
        return np.asarray(dataset[:n_samples])


def scan_denoised(path: Path, *, peek_samples: int = PEEK_SAMPLES) -> dict[str, Any]:
    arr = read_channel(path, "channel0001", peek_samples)
    counts = np.bincount(arr.astype(np.int64) + 128, minlength=256)
    return {
        "unique_int8": len(np.unique(arr)),
        "std_mv": float(np.std(arr.astype(np.float64)) * MV_PER_LSB),
        "mode_fraction": float(counts.max() / len(arr)),
        "array": arr,
    }


def compute_pearson(denoised: np.ndarray, target: np.ndarray) -> float:
    """Return Pearson correlation in physical units, or NaN when undefined."""
    size = min(len(denoised), len(target))
    denoised_mv = denoised[:size].astype(np.float64) * MV_PER_LSB
    target_mv = target[:size].astype(np.float64) * MV_PER_LSB
    if np.std(denoised_mv) < 1e-12 or np.std(target_mv) < 1e-12:
        return float("nan")
    value = float(np.corrcoef(denoised_mv, target_mv)[0, 1])
    return value if np.isfinite(value) else float("nan")


def _fmt(value: float, width: int = 8) -> str:
    if math.isnan(value):
        return "nan".rjust(width)
    return f"{value:{width}.4f}"


def _summary(label: str, values: list[float]) -> str:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return f"  {label:30s}: n/a"
    return (
        f"  {label:30s}: min={min(finite):.4f}  "
        f"median={float(np.median(finite)):.4f}  max={max(finite):.4f}  "
        f"mean={float(np.mean(finite)):.4f}"
    )


def scan(args: argparse.Namespace) -> str:
    """Return the historical comparison table for explicitly supplied roots."""
    lines = [
        "=" * 110,
        "  file  target_std_mv | FCNet: unique std_mv mode% pearson | "
        "Baseline: unique std_mv mode% pearson",
        "-" * 110,
    ]
    fcnet_rows: dict[int, dict[str, Any]] = {}
    baseline_rows: dict[int, dict[str, Any]] = {}

    for file_index in range(NUM_FILES):
        target_file = target_path(file_index, directory=args.target_dir)
        if not target_file.exists():
            lines.append(f"{file_index:6d}  MISSING target file {target_file}")
            continue
        target = read_channel(target_file, "channel0002", PEEK_SAMPLES)
        target_std = float(np.std(target.astype(np.float64)) * MV_PER_LSB)

        fcnet_file = fcnet_path(
            file_index,
            primary_dir=args.fcnet_dir,
            fallback_dir=args.fcnet_fallback_dir,
        )
        if fcnet_file.exists():
            fcnet = scan_denoised(fcnet_file)
            fcnet["pearson"] = compute_pearson(fcnet["array"], target)
            fcnet_rows[file_index] = fcnet
            fcnet_cells = (
                f"{fcnet['unique_int8']:6d} {fcnet['std_mv']:7.4f} "
                f"{100 * fcnet['mode_fraction']:6.2f}% {_fmt(fcnet['pearson'])}"
            )
        else:
            fcnet_cells = "MISSING".center(34)

        baseline_file = baseline_path(
            file_index,
            directory=args.baseline_dir,
            exp_id=args.baseline_exp_id,
        )
        if baseline_file.exists():
            baseline = scan_denoised(baseline_file)
            baseline["pearson"] = compute_pearson(baseline["array"], target)
            baseline_rows[file_index] = baseline
            baseline_cells = (
                f"{baseline['unique_int8']:6d} {baseline['std_mv']:7.4f} "
                f"{100 * baseline['mode_fraction']:6.2f}% {_fmt(baseline['pearson'])}"
            )
        else:
            baseline_cells = "MISSING".center(34)

        lines.append(
            f"{file_index:6d}  {target_std:12.4e} | {fcnet_cells} | {baseline_cells}"
        )

    lines.extend(["", "SUMMARY", "=" * 90])
    for label, rows in (("FCNet", fcnet_rows), ("Baseline", baseline_rows)):
        lines.append(f"{label} (n={len(rows)}):")
        lines.append(
            _summary(
                "unique_int8", [float(row["unique_int8"]) for row in rows.values()]
            )
        )
        lines.append(
            _summary("std_mv", [float(row["std_mv"]) for row in rows.values()])
        )
        lines.append(
            _summary(
                "mode_fraction", [float(row["mode_fraction"]) for row in rows.values()]
            )
        )
        lines.append(
            _summary("pearson", [float(row["pearson"]) for row in rows.values()])
        )

    if fcnet_rows and baseline_rows:
        fcnet_unique = [int(row["unique_int8"]) for row in fcnet_rows.values()]
        baseline_unique = [int(row["unique_int8"]) for row in baseline_rows.values()]
        lines.extend(
            [
                "",
                "Threshold gap analysis:",
                f"  FCNet min unique_int8: {min(fcnet_unique)}   vs   "
                f"Baseline max unique_int8: {max(baseline_unique)}",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    print(scan(_args()))


if __name__ == "__main__":
    main()

"""Evaluate Pearson and diversity metrics on historical TIDMAD outputs.

The five comparison cases and their artifact names reproduce the original
Health-gate feasibility investigation. Machine-local roots are explicit CLI
inputs; no repository or user-home layout is assumed.
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from tasks.tidmad.tools.fcnet_diversity_pearson_scan import (
    MV_PER_LSB,
    baseline_path,
    compute_pearson,
    read_channel,
)

NUM_FILES = 20
SAMPLE_SIZE = 1_000_000
BASELINE_EXP_ID = "1784177030"
AGENT_BEST_EXP_ID = "012"
AGENT_BEST_FILES = tuple(range(12, 20))
FCNET_FILES = (10, 11, 12, 13, 14)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--fcnet-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    return parser.parse_args()


def target_path(file_index: int, *, directory: Path) -> Path:
    return directory / f"abra_validation_{file_index:04d}.h5"


def agent_best_path(file_index: int, *, directory: Path) -> Path:
    return directory / (
        "abra_validation_denoised_wavenet_diagnostic_baseline_pre_v17_agent_"
        "wavenet_diagnostic_baseline_pre_v17_agent_"
        f"{AGENT_BEST_EXP_ID}_{file_index:04d}.h5"
    )


def fcnet_path(file_index: int, *, directory: Path) -> Path:
    return directory / f"abra_validation_denoised_fcnet_{file_index:04d}.h5"


def synthesize_collapse(
    value: int,
    perturbation_rate: float,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return the original bounded synthetic-collapse comparison."""
    output = np.full(n_samples, value, dtype=np.int8)
    perturbations = int(n_samples * perturbation_rate)
    if perturbations:
        indices = rng.choice(n_samples, size=perturbations, replace=False)
        output[indices] = np.clip(
            value + rng.integers(-2, 3, size=perturbations),
            -128,
            127,
        ).astype(np.int8)
    return output


def compute_metrics(denoised: np.ndarray, target: np.ndarray) -> dict[str, float | int]:
    """Compute the original alignment-sensitive and diversity measurements."""
    denoised_mv = denoised.astype(np.float64) * MV_PER_LSB
    target_mv = target.astype(np.float64) * MV_PER_LSB
    return {
        "pearson": compute_pearson(denoised, target),
        "mse_mv2": float(np.mean((denoised_mv - target_mv) ** 2)),
        "output_std_mv": float(np.std(denoised_mv)),
        "target_std_mv": float(np.std(target_mv)),
        "output_unique_int8_count": len(np.unique(denoised)),
    }


def _read_case(
    *,
    files: Iterable[int],
    paths: dict[int, Path],
    targets: dict[int, np.ndarray],
    sample_size: int,
) -> dict[int, dict[str, float | int]]:
    rows: dict[int, dict[str, float | int]] = {}
    for file_index in files:
        path = paths[file_index]
        if file_index not in targets or not path.exists():
            continue
        denoised = read_channel(path, "channel0001", sample_size)
        rows[file_index] = compute_metrics(denoised, targets[file_index])
    return rows


def _synthetic_case(
    *,
    targets: dict[int, np.ndarray],
    value: int,
    rng: np.random.Generator,
) -> dict[int, dict[str, float | int]]:
    return {
        file_index: compute_metrics(
            synthesize_collapse(value, 0.001, len(target), rng),
            target,
        )
        for file_index, target in targets.items()
    }


def _stats(rows: dict[int, dict[str, Any]], key: str) -> str:
    values = [
        float(row[key])
        for row in rows.values()
        if isinstance(row[key], (int, float)) and math.isfinite(float(row[key]))
    ]
    if not values:
        return "n/a (all NaN)"
    return (
        f"min={min(values):+.4f}  max={max(values):+.4f}  "
        f"mean={float(np.mean(values)):+.4f}  "
        f"median={float(np.median(values)):+.4f}"
    )


def investigate(args: argparse.Namespace) -> str:
    """Return the complete five-case feasibility summary."""
    sample_size = int(args.sample_size)
    if sample_size < 1:
        raise ValueError("sample_size must be positive")

    targets = {
        file_index: read_channel(
            target_path(file_index, directory=args.target_dir),
            "channel0002",
            sample_size,
        )
        for file_index in range(NUM_FILES)
        if target_path(file_index, directory=args.target_dir).exists()
    }
    rng = np.random.default_rng(42)
    cases = {
        "Case 1 agent_012 tuning-best": _read_case(
            files=AGENT_BEST_FILES,
            paths={
                index: agent_best_path(index, directory=args.agent_dir)
                for index in AGENT_BEST_FILES
            },
            targets=targets,
            sample_size=sample_size,
        ),
        "Case 2 paper-spec baseline": _read_case(
            files=range(NUM_FILES),
            paths={
                index: baseline_path(
                    index,
                    directory=args.baseline_dir,
                    exp_id=BASELINE_EXP_ID,
                )
                for index in range(NUM_FILES)
            },
            targets=targets,
            sample_size=sample_size,
        ),
        "Case 3 synthetic K=0": _synthetic_case(targets=targets, value=0, rng=rng),
        "Case 4 synthetic K=-1": _synthetic_case(targets=targets, value=-1, rng=rng),
        "Case 5 FCNet paper reproduction": _read_case(
            files=FCNET_FILES,
            paths={
                index: fcnet_path(index, directory=args.fcnet_dir)
                for index in FCNET_FILES
            },
            targets=targets,
            sample_size=sample_size,
        ),
    }

    lines = [
        "=" * 90,
        "PEARSON FEASIBILITY EXPERIMENT",
        f"  target dir: {args.target_dir}",
        f"  baseline dir: {args.baseline_dir}",
        f"  agent dir: {args.agent_dir}",
        f"  FCNet dir: {args.fcnet_dir}",
        f"  sample size: {sample_size}",
        "=" * 90,
    ]
    for metric in ("pearson", "output_std_mv", "output_unique_int8_count", "mse_mv2"):
        lines.extend(["", f"[{metric}]"])
        for case, rows in cases.items():
            lines.append(f"  {case:<42s}: {_stats(rows, metric)}")
    return "\n".join(lines)


def main() -> None:
    print(investigate(_args()))


if __name__ == "__main__":
    main()

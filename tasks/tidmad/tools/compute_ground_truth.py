#!/usr/bin/env python3
"""Regenerate TIDMAD perfect-denoiser reference scores from an anchor map."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from execute_tools.scoring_utils import coerce_nonfinite_to_none


def _global_per_file_ceiling(
    anchors_f: list[float], s_max: float
) -> tuple[float, float, int]:
    """Return one file's log score, linear sum, and segment count."""
    n_segments = len(anchors_f)
    linear_sum = sum(value * value for value in anchors_f) / s_max
    linear_mean = linear_sum / n_segments
    score = (
        float(math.log(linear_mean, 5.27))
        if linear_mean > 0 and math.isfinite(linear_mean)
        else float("-inf")
    )
    return score, float(linear_sum), n_segments


def _anchor_normalized_ceiling(
    anchors: dict[str, list[float]], s_max: float
) -> tuple[list[float], float]:
    """Return per-file linear means and their segment-weighted log score."""
    file_vector: list[float] = []
    total_linear_sum = 0.0
    total_segments = 0
    for file_index in sorted(anchors, key=int):
        values = anchors[file_index]
        linear_sum = sum(value * value for value in values) / s_max
        file_vector.append(linear_sum / len(values))
        total_linear_sum += linear_sum
        total_segments += len(values)

    grand_mean = total_linear_sum / total_segments
    score = (
        float(math.log(grand_mean, 5.27))
        if grand_mean > 0 and math.isfinite(grand_mean)
        else float("-inf")
    )
    return file_vector, score


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(coerce_nonfinite_to_none(payload), indent=2) + "\n",
        encoding="utf-8",
    )


def regenerate(anchor_map: Path, output_dir: Path, *, override: bool) -> None:
    """Regenerate all committed-schema ceiling artifacts in ``output_dir``."""
    anchor_payload = json.loads(anchor_map.read_text(encoding="utf-8"))
    anchors: dict[str, list[float]] = anchor_payload["anchors"]
    s_max = float(anchor_payload["s_max"])
    output_dir.mkdir(parents=True, exist_ok=True)
    computed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for file_index_text in sorted(anchors, key=int):
        file_index = int(file_index_text)
        output_path = output_dir / f"ground_truth_score_file_{file_index:04d}.json"
        if output_path.exists() and not override:
            continue
        score, linear_sum, n_segments = _global_per_file_ceiling(
            anchors[file_index_text], s_max
        )
        _write_json(
            output_path,
            {
                "file_index": file_index,
                "score": score,
                "linear_sum": linear_sum,
                "n_segments": n_segments,
                "mode": "fine",
                "s_max": s_max,
                "formula": "option_b_global_s_max_ceiling",
                "source": anchor_map.name,
                "computed_at": computed_at,
            },
        )

    file_vector, scalar_score = _anchor_normalized_ceiling(anchors, s_max)
    _write_json(
        output_dir / "ceiling_anchor_normalized.json",
        {
            "scalar_score": scalar_score,
            "file_vector": file_vector,
            "formula": "anchor_normalized_ceiling",
            "s_max": s_max,
            "num_files": int(anchor_payload.get("num_files", len(anchors))),
            "source": anchor_map.name,
            "computed_at": computed_at,
        },
    )


def main() -> None:
    """Run the explicit-path reference-data regeneration command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--anchor-map",
        type=Path,
        required=True,
        help="TIDMAD segment_anchors.json input path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Destination for regenerated reference JSON files.",
    )
    parser.add_argument(
        "--override",
        action="store_true",
        help="Replace per-file JSON files that already exist.",
    )
    arguments = parser.parse_args()
    regenerate(arguments.anchor_map, arguments.output_dir, override=arguments.override)


if __name__ == "__main__":
    main()

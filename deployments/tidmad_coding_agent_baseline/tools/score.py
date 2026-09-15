"""Expose the existing task-owned scorer without a second scientific formula."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .archive_candidate import (
    archive_candidate,
    candidate_tree_digest,
    validate_candidate_identity,
    validate_candidate_source,
)
from .evaluator_policy import EvaluatorPolicy
from .final_inference import run_candidate_inference
from .health import evaluate_candidate_health
from .io import atomic_write_json, fsync_directory
from .model import BANDS, DEVELOPMENT_FILE_BY_BAND, utc_text


def _load_runtime(input_root: Path):
    """Import the immutable task snapshot and its pinned generic dependencies."""

    resolved = str(input_root.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)
    from tasks.tidmad.runtime.anchor_map import load_anchor_map
    from tasks.tidmad.runtime.scoreability import TidmadScoreabilityContract
    from tasks.tidmad.runtime.scoring import score_vector

    from execute_tools.dataset_config import load_dataset_profile

    return (
        load_dataset_profile,
        load_anchor_map,
        TidmadScoreabilityContract,
        score_vector,
    )


def _sample_set(path: Path) -> dict[int, list[int]]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise TypeError("sample set must be a JSON object")
    return {int(key): [int(value) for value in values] for key, values in payload.items()}


def _deliverable_name(input_root: Path, file_index: int) -> str:
    spec = json.loads(
        (input_root / "tasks" / "tidmad" / "resolved" / "deliverable_spec.json").read_text()
    )
    naming = spec["naming"]
    return f"{naming['prefix']}_{file_index:0{int(naming['index_width'])}d}{naming['extension']}"


def _scoreability(input_root: Path, deliverables: dict[int, str], contract_type: Any) -> None:
    metric = json.loads(
        (input_root / "tasks" / "tidmad" / "resolved" / "metric_spec.json").read_text()
    )
    contract = contract_type(**metric["scoreability"])
    for raw_path in deliverables.values():
        path = Path(raw_path)
        mode = path.lstat().st_mode
        if path.is_symlink() or not stat.S_ISREG(mode):
            raise ValueError(f"candidate deliverable must be a regular file: {path}")
    verdict = contract.check(deliverables)
    if not verdict.scoreable:
        details = "; ".join(f"{item.requirement}: {item.detail}" for item in verdict.failures)
        raise ValueError(f"candidate deliverables are not scoreable: {details}")


def compute_score(
    *,
    input_root: Path,
    raw_data_dir: Path,
    denoised_dir: Path,
    sample_set_path: Path,
    workers: int,
) -> tuple[dict[str, Any], list[Path]]:
    load_profile, load_anchors, contract_type, score_vector = _load_runtime(input_root)
    task_root = input_root / "tasks" / "tidmad"
    profile = load_profile(task_root / "resolved" / "dataset_profile.json")
    anchor_map = load_anchors(task_root / "reference_data" / "segment_anchors.json")
    sample_set = _sample_set(sample_set_path)
    paths = [denoised_dir / _deliverable_name(input_root, index) for index in sample_set]
    deliverables = {index: str(path) for index, path in zip(sample_set, paths, strict=True)}
    _scoreability(input_root, deliverables, contract_type)
    file_vector, scalar = score_vector(
        data_dir=str(denoised_dir),
        sample_set=sample_set,
        anchor_map=anchor_map["anchors"],
        s_max=float(anchor_map["s_max"]),
        denoised_filename_fn=lambda index: _deliverable_name(input_root, index),
        raw_data_dir=str(raw_data_dir),
        parallel=workers > 1,
        num_workers=workers,
        legacy_mode=False,
        profile=profile,
    )
    scoreable = math.isfinite(float(scalar))
    return (
        {
            "version": "tidmad-coding-agent-score-v2",
            "scoreable": scoreable,
            # Eligibility is established only after task-owned Health runs.
            "valid": False,
            "scalar": float(scalar),
            "file_vector": file_vector,
            "sample_set": {str(key): value for key, value in sample_set.items()},
        },
        paths,
    )


def _delete_scored_deliverables(paths: list[Path]) -> None:
    for path in paths:
        path.unlink()


def score_candidate(args: argparse.Namespace, policy: EvaluatorPolicy | None = None) -> Path:
    policy = policy or EvaluatorPolicy()
    validate_candidate_identity(args.candidate_id)
    candidate_source = policy.agent_path(args.candidate_source, label="candidate source")
    sample_set = policy.scope_path(
        f"band-{args.band}-development",
        band=args.band,
        phase="development",
    )
    policy.archive_root.parent.mkdir(parents=True, exist_ok=True)
    snapshot_root = Path(
        tempfile.mkdtemp(prefix=f".{args.candidate_id}.snapshot.", dir=policy.archive_root.parent)
    )
    snapshot = snapshot_root / "candidate"
    # Preserve links as links so an evaluator-owned copy cannot dereference an
    # agent-created link into hidden truth or another privileged path.
    shutil.copytree(candidate_source, snapshot, symlinks=True)
    validate_candidate_source(snapshot)
    candidate_digest = candidate_tree_digest(snapshot)
    try:
        denoised_dir = run_candidate_inference(
            winners={args.band: (args.candidate_id, snapshot_root)},
            task_root=policy.input_root,
            input_root=policy.development_input_dir,
            output_root=snapshot_root / "denoised",
            files_by_band={args.band: (DEVELOPMENT_FILE_BY_BAND[args.band],)},
            opaque_band_inputs=True,
        )
        score, deliverables = compute_score(
            input_root=policy.input_root,
            raw_data_dir=policy.development_truth_dir,
            denoised_dir=denoised_dir,
            sample_set_path=sample_set,
            workers=args.workers,
        )
        denoised_paths = {
            index: path for index, path in zip(_sample_set(sample_set), deliverables, strict=True)
        }
        health = evaluate_candidate_health(
            input_root=policy.input_root,
            raw_data_dir=policy.development_truth_dir,
            denoised_paths=denoised_paths,
            file_vector=score["file_vector"],
            scalar=float(score["scalar"]),
            candidate_id=args.candidate_id,
            run_id=os.environ.get("BASELINE_RUN_ID", "unbound"),
            config_root=policy.health_config_root,
        )
        score.update(
            {
                "evaluation_split": "development",
                "health_status": health.status,
                "health_passed": health.eligible,
                "health_gate_results": health.gate_results,
                "health_effective_config_sha256": health.effective_config_sha256,
                "eligible_for_selection": bool(score["scoreable"] and health.eligible),
            }
        )
        score["valid"] = score["eligible_for_selection"]
        score["candidate_tree_sha256"] = candidate_digest
        scored_epoch = int(time.time())
        score["score_epoch"] = scored_epoch
        score["score_utc"] = utc_text(scored_epoch)
        score["run_id"] = os.environ.get("BASELINE_RUN_ID")
        score["invocation_id"] = os.environ.get("BASELINE_INVOCATION_ID")
        if not score["eligible_for_selection"]:
            return _publish_ineligible_evaluation(
                args=args,
                policy=policy,
                score=score,
            )
        return _publish_candidate_score(
            args=args,
            policy=policy,
            snapshot=snapshot,
            score=score,
            deliverables=deliverables,
        )
    finally:
        shutil.rmtree(snapshot_root)


def _publish_ineligible_evaluation(
    *,
    args: argparse.Namespace,
    policy: EvaluatorPolicy,
    score: dict[str, Any],
) -> Path:
    """Persist feedback without retaining or selecting an invalid candidate."""

    band_root = policy.evaluation_root / args.band
    band_root.mkdir(parents=True, exist_ok=True)
    destination = band_root / f"{args.candidate_id}.json"
    if destination.exists():
        raise FileExistsError(f"candidate evaluation already exists: {destination}")
    atomic_write_json(destination, score)
    destination.chmod(0o440)
    fsync_directory(band_root)
    return destination


def _publish_candidate_score(
    *,
    args: argparse.Namespace,
    policy: EvaluatorPolicy,
    snapshot: Path,
    score: dict[str, Any],
    deliverables: list[Path],
) -> Path:
    descriptor, raw_score = tempfile.mkstemp(
        prefix=f".{args.candidate_id}.score.",
        suffix=".json",
        dir=policy.archive_root.parent,
    )
    os.close(descriptor)
    temporary_score = Path(raw_score)
    atomic_write_json(temporary_score, score)
    try:
        destination = archive_candidate(
            source=snapshot,
            score_path=temporary_score,
            archive_root=policy.archive_root,
            band=args.band,
            candidate_id=args.candidate_id,
        )
    finally:
        temporary_score.unlink(missing_ok=True)
    _delete_scored_deliverables(deliverables)
    return destination


def _winner_map(values: list[str]) -> dict[str, str]:
    winners: dict[str, str] = {}
    for value in values:
        band, separator, candidate_id = value.partition("=")
        if not separator or band not in BANDS or not candidate_id:
            raise ValueError(f"invalid --winner value: {value!r}")
        winners[band] = candidate_id
    if set(winners) != set(BANDS):
        raise ValueError("final scoring requires exactly one winner for every band")
    return winners


def score_final(args: argparse.Namespace, policy: EvaluatorPolicy | None = None) -> Path:
    policy = policy or EvaluatorPolicy()
    winners = _winner_map(args.winner)
    denoised_dir = args.denoised_dir.resolve(strict=True)
    if denoised_dir != policy.final_output_dir.resolve(strict=True):
        raise ValueError(f"final denoised directory must be evaluator-owned: {denoised_dir}")
    sample_set = policy.scope_path("all-final", band=None, phase="final")
    score, deliverables = compute_score(
        input_root=policy.input_root,
        raw_data_dir=policy.final_truth_dir,
        denoised_dir=denoised_dir,
        sample_set_path=sample_set,
        workers=args.workers,
    )
    denoised_paths = {
        index: path for index, path in zip(_sample_set(sample_set), deliverables, strict=True)
    }
    health = evaluate_candidate_health(
        input_root=policy.input_root,
        raw_data_dir=policy.final_truth_dir,
        denoised_paths=denoised_paths,
        file_vector=score["file_vector"],
        scalar=float(score["scalar"]),
        candidate_id="final-submission",
        run_id=os.environ.get("BASELINE_RUN_ID", "unbound"),
        config_root=policy.health_config_root,
    )
    score.update(
        {
            "evaluation_split": "final",
            "health_status": health.status,
            "health_passed": health.eligible,
            "health_gate_results": health.gate_results,
            "health_effective_config_sha256": health.effective_config_sha256,
            "eligible_for_selection": bool(score["scoreable"] and health.eligible),
        }
    )
    score["valid"] = score["eligible_for_selection"]
    if not score["scoreable"] or any(value is None for value in score["file_vector"]):
        raise ValueError("final score must be finite and cover all 20 validation files")
    if not health.eligible:
        raise ValueError(
            "final score refused by task Health: "
            f"health_status={health.status}; no final artifact was written"
        )
    score["winner_candidates"] = winners
    score["score_epoch"] = int(time.time())
    score["score_utc"] = utc_text(score["score_epoch"])
    atomic_write_json(policy.final_score, score)
    policy.final_score.chmod(0o440)
    fsync_directory(policy.final_score.parent)
    _delete_scored_deliverables(deliverables)
    return policy.final_score


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workers", type=int, default=8)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    candidate = subparsers.add_parser("candidate")
    _common(candidate)
    candidate.add_argument("--candidate-source", type=Path, required=True)
    candidate.add_argument("--band", choices=BANDS, required=True)
    candidate.add_argument("--candidate-id", required=True)
    args = parser.parse_args()
    output = score_candidate(args)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Split the PhyTS TESS task into an agent-visible view and a private one.

**Why this exists, and why the SIDERIUS workflow does not need it.**

In a SIDERIUS chain the agent is an LLM that never touches the filesystem:
scopes and targets travel to child processes, and the model sees prompts and
records. A committed manifest carrying validation targets is therefore
harmless there, and necessary — the metric reads truth from the scope.

A coding agent is a different threat model. It has a shell. If the
validation targets are anywhere under a path it can read, the cheapest
winning strategy is to copy them into its predictions and score a perfect
R-squared, and nothing downstream would report an error: the deliverable
would be well formed, scoreable and complete.

So the two views are **deliberately not byte-identical**:

``agent/``      training targets, and validation IDENTITIES with no target
``evaluator/``  the full validation manifest, targets included

The refusal below is the point of the tool. It re-reads what it just wrote
and fails if a validation target reached the agent view, rather than
trusting the writer it is standing next to.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PACK_ROOT / "data" / "manifests" / "rotation_identity.csv"

#: Columns that ARE the answer for the evaluated split.
TARGET_COLUMNS = ("frot", "frot_err")

#: The split the agent is scored on. Its targets are the evaluator's alone.
EVALUATED_SPLIT = "val"

#: The split the agent trains on. Its targets are supervision, not answers.
TRAINING_SPLIT = "train"

IDENTITY_COLUMNS = ("split", "gaia_id", "tic", "sector")

STAGED_FILENAME = "tess_rotation_{split}.npz"


def _rows() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})


def assert_agent_view_is_answer_free(agent_root: Path) -> None:
    """Re-read the written view and refuse if an evaluated target is in it.

    Deliberately a fresh read of the bytes on disk rather than a check of the
    in-memory rows. The failure this guards against is a writer emitting a
    column it was not asked for, and asking that writer whether it did so is
    not evidence.
    """
    offenders: list[str] = []
    for path in sorted(agent_root.rglob("*")):
        if not path.is_file() or path.suffix != ".csv":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if not lines:
            continue
        columns = [column.strip() for column in lines[0].split(",")]
        if not any(column in columns for column in TARGET_COLUMNS):
            continue
        for row in csv.DictReader(lines):
            # A TRAINING row legitimately carries its target; only the
            # evaluated split's targets are answers.
            if row.get("split") == EVALUATED_SPLIT and any(
                row.get(column) for column in TARGET_COLUMNS
            ):
                offenders.append(f"{path}: an {EVALUATED_SPLIT!r} row carries a target")
                break
    if offenders:
        raise SystemExit(
            "REFUSING to publish an agent view containing validation answers:\n  "
            + "\n  ".join(offenders)
        )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data_dir",
        required=True,
        help="A staged run data root (see data/README.md). Must hold both splits.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Fresh directory to create. agent/ and evaluator/ are written inside.",
    )
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"--output must be a fresh, empty directory: {output}")

    rows = _rows()
    training = [row for row in rows if row["split"] == TRAINING_SPLIT]
    evaluated = [row for row in rows if row["split"] == EVALUATED_SPLIT]
    if not training or not evaluated:
        raise SystemExit("the identity manifest is missing one of its splits")

    agent = output / "agent"
    evaluator = output / "evaluator"
    identity = list(IDENTITY_COLUMNS)

    # Agent view: training rows keep their targets, which is supervision.
    # Evaluated rows keep their IDENTITIES so the agent knows what to predict
    # for, and lose every target column.
    _write_csv(
        agent / "manifests" / "train.csv", training, identity + list(TARGET_COLUMNS)
    )
    _write_csv(agent / "manifests" / "predict.csv", evaluated, identity)

    # Evaluator view: the full evaluated manifest, targets included.
    _write_csv(
        evaluator / "manifests" / "val_truth.csv",
        evaluated,
        identity + list(TARGET_COLUMNS),
    )

    # Both views need the light curves; flux is input, not an answer.
    for split in (TRAINING_SPLIT, EVALUATED_SPLIT):
        source = data_dir / STAGED_FILENAME.format(split=split)
        if not source.is_file():
            raise SystemExit(f"staged split not found: {source}")
        shutil.copy2(source, agent / STAGED_FILENAME.format(split=split))

    assert_agent_view_is_answer_free(agent)

    receipt = {
        "identity_manifest_sha256": _digest(MANIFEST),
        "evaluated_split": EVALUATED_SPLIT,
        "agent_view": {
            "train_rows": len(training),
            "predict_rows": len(evaluated),
            "evaluated_targets_present": False,
        },
        "evaluator_view": {"val_truth_rows": len(evaluated)},
        "files": {
            str(path.relative_to(output)): _digest(path)
            for path in sorted(output.rglob("*"))
            if path.is_file()
        },
    }
    (output / "views_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"agent view      : {agent}")
    print(f"  train rows    : {len(training)} (targets present — supervision)")
    print(f"  predict rows  : {len(evaluated)} (identities only — NO targets)")
    print(f"evaluator view  : {evaluator}")
    print(f"  val truth rows: {len(evaluated)}")
    print(f"\nreceipt: {output / 'views_receipt.json'}")
    print("the evaluator view must never be mounted where the agent can read it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

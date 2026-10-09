"""Compare complete synthetic proposer requests before/after the budget fix."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PROFILES = {
    "tess": "paper-early",
    "ligo": "paper-early",
    "project8": "paper-late",
    "tidmad": "paper-tidmad-noprior",
}


def compare(reference: Path, candidate: Path, output: Path) -> dict:
    root = Path(__file__).resolve().parent
    fixture = root / "request-fixtures/proposer-budget-v2.json"
    expected_reference = json.loads(fixture.read_text())["provenance"][
        "source_revision"
    ]
    reference_revision = subprocess.check_output(
        ["git", "-C", str(reference), "rev-parse", "HEAD"], text=True
    ).strip()
    if reference_revision != expected_reference:
        raise ValueError(
            "Reference checkout differs from the fixture's pre-fix source revision"
        )
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for task, prefix in PROFILES.items():
        receipts = {}
        messages = {}
        for label, checkout, version in (
            ("reference", reference, 1),
            ("candidate", candidate, 2),
        ):
            revision = subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
            ).strip()
            target = output / task / label
            process = subprocess.run(
                [
                    str(checkout / ".venv/bin/python"),
                    str(root / "capture_proposer_requests.py"),
                    "--fixture",
                    str(fixture),
                    "--output",
                    str(target),
                    "--expected-revision",
                    revision,
                    "--profile",
                    f"{prefix}-v{version}",
                ],
                cwd=checkout,
                capture_output=True,
                text=True,
                check=False,
            )
            if process.returncode:
                raise RuntimeError(
                    f"{task}/{label}: offline capture failed\n{process.stderr}"
                )
            receipts[label] = json.loads((target / "receipt.json").read_text())
            messages[label] = json.loads((target / "messages.json").read_text())
        results.append(
            {
                "task": task,
                "status": "MATCH"
                if messages["reference"] == messages["candidate"]
                else "DIFFERENCE",
                **receipts,
            }
        )
    report = {
        "scope": "Supplementary synthetic branch witnesses; not recovered historical conversations",
        "comparison_source_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "results": results,
        "provider_calls": 0,
        "training_calls": 0,
    }
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = compare(
        args.reference.resolve(), args.candidate.resolve(), args.output.resolve()
    )
    failures = [row["task"] for row in report["results"] if row["status"] != "MATCH"]
    print(json.dumps({"tasks": len(report["results"]), "failures": failures}))
    raise SystemExit(bool(failures))

"""Compare frozen rendering requests using explicitly supplied infra checkouts."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path

PROFILES = {
    "analysis": "paper-analysis-c0467447-v1",
    "tess": "paper-early-v1",
    "ligo": "paper-early-v1",
    "project8": "paper-late-v1",
    "tidmad": "paper-tidmad-noprior-v1",
}


def compare(candidate: Path, references: dict, output: Path) -> dict:
    root = Path(__file__).parent
    requests = sorted((root / "fixtures").glob("*.json"))
    if not requests:
        raise ValueError("No prompt fixtures found; an empty comparison is not qualification")
    output.mkdir(parents=True, exist_ok=False)
    candidate_revision = subprocess.check_output(
        ["git", "-C", str(candidate), "rev-parse", "HEAD"], text=True
    ).strip()

    def run(request: Path) -> dict:
        case = json.loads(request.read_text())
        task = request.stem.split("-", 1)[0]
        reference = Path(references[task])
        reference_revision = case["provenance"]["reference_infra_revision"]
        results = {}
        for label, checkout, revision in (
            ("reference", reference, reference_revision),
            ("candidate", candidate, candidate_revision),
        ):
            destination = output / request.stem / label
            command = [
                str(checkout / ".venv/bin/python"),
                str(root / "capture.py"),
                "--request",
                str(request),
                "--output",
                str(destination),
                "--expected-revision",
                revision,
            ]
            if label == "candidate":
                command += ["--profile", PROFILES[task]]
            process = subprocess.run(command, cwd=checkout, capture_output=True, text=True)
            if process.returncode:
                return {
                    "case": request.stem,
                    "status": "ERROR",
                    "side": label,
                    "error": process.stderr[-4000:],
                }
            results[label] = json.loads((destination / "receipt.json").read_text())
        equal = results["reference"]["messages"] == results["candidate"]["messages"]
        return {
            "case": request.stem,
            "status": "MATCH" if equal else "DIFFERENCE",
            "scope": case["provenance"]["scope"],
            **results,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(run, requests))
    report = {
        "candidate_revision": candidate_revision,
        "results": rows,
        "api_calls": 0,
        "training_calls": 0,
        "scope": "Declared rendering/producer boundaries; not complete conversation replay",
    }
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = compare(
        args.candidate.resolve(), json.loads(args.references.read_text()), args.output.resolve()
    )
    failures = [row for row in report["results"] if row["status"] != "MATCH"]
    print(json.dumps({"cases": len(report["results"]), "failures": failures}, indent=2))
    raise SystemExit(bool(failures))

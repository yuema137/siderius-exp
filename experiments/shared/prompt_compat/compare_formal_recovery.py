"""Compare cached interpreter requests before and after explicit evidence recovery.

Requests are RecoveryRequest JSON files. Every subprocess uses the selected
checkout's own interpreter. No providers or training are invoked.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path

from recover_formal_evidence import RecoveryRequest

TOOLS = Path(__file__).resolve().parent


def invoke(checkout: Path, tool: str, *arguments: str) -> None:
    result = subprocess.run(
        [str(checkout / ".venv/bin/python"), str(TOOLS / tool), *arguments],
        cwd=checkout,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"{tool} failed: {result.stderr[-3000:]}")


def compare_case(
    request_path: Path,
    checkouts: dict[str, Path],
    revisions: dict[str, str],
    output: Path,
) -> dict:
    request = RecoveryRequest.model_validate_json(request_path.read_bytes())
    root = output / request_path.stem
    recovered_dir = root / "recovered"
    invoke(
        checkouts["candidate"],
        "recover_formal_evidence.py",
        "--request",
        str(request_path),
        "--expected-revision",
        revisions["candidate"],
        "--output",
        str(recovered_dir),
    )
    original = json.loads(request.interpretation.read())
    recovered = json.loads((recovered_dir / "interpretation.json").read_text())
    recovery_receipt = json.loads((recovered_dir / "receipt.json").read_text())
    results = {}
    for side, artifact in (("reference", original), ("candidate", recovered)):
        supplied = {
            "summaries": [],
            "model_knowledge_cache": artifact["model_knowledge_cache"],
            "metric_spec": recovery_receipt["metric_spec"],
            "task_description": "Offline comparison using archived model knowledge and resolved metric; no new scientific instruction.",
        }
        capture_request = {
            "case_id": request_path.stem,
            "boundary": "interpretation.cached_synthesis",
            "arguments": {
                "input": supplied,
                "expected_included": original["scientific_aggregation"]["included"],
            },
            "provenance": {
                "scope": "Reconstructed cached-only input; saved text/stats, not a full archived request envelope",
                "recovery_request": request.model_dump(mode="json"),
            },
        }
        capture_path = root / f"{side}-request.json"
        capture_path.write_text(json.dumps(capture_request, indent=2) + "\n")
        destination = root / side
        invoke(
            checkouts[side],
            "capture.py",
            "--request",
            str(capture_path),
            "--output",
            str(destination),
            "--expected-revision",
            revisions[side],
        )
        results[side] = json.loads((destination / "receipt.json").read_text())
    equal = results["reference"]["messages"] == results["candidate"]["messages"]
    return {
        "case": request_path.stem,
        "status": "MATCH" if equal else "DIFFERENCE",
        "recovery": recovery_receipt,
        **results,
    }


def compare(candidate: Path, reference: Path, requests: Path, output: Path) -> dict:
    paths = sorted(requests.glob("*.json"))
    if not paths:
        raise ValueError(
            "No recovery requests found; an empty comparison is not qualification"
        )
    checkouts = {"candidate": candidate.resolve(), "reference": reference.resolve()}
    revisions = {
        side: subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        for side, root in checkouts.items()
    }
    output.mkdir(parents=True, exist_ok=False)

    def run(path):
        try:
            return compare_case(path, checkouts, revisions, output)
        except (OSError, ValueError) as exc:
            return {"case": path.stem, "status": "ERROR", "error": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(run, paths))
    report = {
        "revisions": revisions,
        "results": rows,
        "api_calls": 0,
        "training_calls": 0,
    }
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "reference", "requests", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.candidate, args.reference, args.requests, args.output)
    failed = [row for row in report["results"] if row["status"] != "MATCH"]
    print(json.dumps({"cases": len(report["results"]), "failures": failed}, indent=2))
    raise SystemExit(bool(failed))

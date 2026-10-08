"""Capture version discriminators with an exact original checkout's interpreter."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from trace_replay import drive_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revision = subprocess.check_output(
        ["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != args.expected_revision or subprocess.check_output(
        ["git", "-C", str(args.checkout), "diff", "HEAD", "--", "src"], text=True
    ):
        raise ValueError("Historical capture requires the exact clean source revision")
    from core.runtime_control import adaptive
    from core.runtime_control.workload import ResolvedPhaseWorkload

    if (
        Path(adaptive.__file__).resolve()
        != (args.checkout / "src/core/runtime_control/adaptive.py").resolve()
    ):
        raise ValueError("Capture must use the historical checkout's own environment")
    fixture = Path(__file__).parent / "fixtures/version-branches-input.json"
    results = []
    for case in json.loads(fixture.read_text())["cases"]:
        verifier = adaptive.AdaptiveUnitVerification(
            "optimizer_step",
            adaptive.AdaptiveVerificationConfig.model_validate(case["config"]),
        )
        observed = drive_trace(verifier, case["segments"])
        workload = ResolvedPhaseWorkload(
            phase="training",
            unit="optimizer_step",
            unit_count=sum(len(s["rates_ms"]) for s in case["segments"]),
        )
        prediction = (
            verifier.prediction(workload, "real_dataset_warmup").model_dump(mode="json")
            if verifier.state == "verified"
            else None
        )
        results.append(
            {
                "case_id": case["case_id"],
                "observed_units": observed,
                "state": verifier.state,
                "measurement": verifier.measurement().model_dump(mode="json"),
                "prediction": prediction,
            }
        )
    args.output.write_text(
        json.dumps(
            {
                "reference_revision": revision,
                "source_sha256": hashlib.sha256(
                    Path(adaptive.__file__).read_bytes()
                ).hexdigest(),
                "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                "capture_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "trace_driver_sha256": hashlib.sha256(
                    (Path(__file__).parent / "trace_replay.py").read_bytes()
                ).hexdigest(),
                "results": results,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

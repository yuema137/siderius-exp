"""Compare complete captured validator requests before retaining compact receipts."""

import argparse
import hashlib
import json
from pathlib import Path


def compare(
    reference,
    candidate,
    reference_revision,
    candidate_revision,
    native_disclosure=False,
):
    if (
        reference["infra_revision"] != reference_revision
        or candidate["infra_revision"] != candidate_revision
    ):
        raise ValueError("Unexpected source pair")
    expected = {
        f"{task}-{kind}"
        for task in ("tess", "ligo", "project8", "tidmad")
        for kind in ("clean", "pytest", "gradient", "absent")
    }
    left = {row["case"]: row for row in reference["rows"]}
    right = {row["case"]: row for row in candidate["rows"]}
    if (
        set(left) != expected
        or set(right) != expected
        or len(reference["rows"]) != 16
        or len(candidate["rows"]) != 16
    ):
        raise ValueError("Incomplete or duplicated comparison corpus")
    results = []
    for case in sorted(expected):
        a, b = left[case], right[case]
        if {k: v for k, v in a.items() if k != "messages"} != {
            k: v for k, v in b.items() if k != "messages"
        }:
            raise ValueError(f"Input/identity mismatch: {case}")
        should_change = native_disclosure and not case.endswith("-absent")
        if a["messages"]["system"] != b["messages"]["system"]:
            raise ValueError(f"System prompt changed: {case}")
        equal = a["messages"]["user"] == b["messages"]["user"]
        if equal == should_change:
            raise ValueError(f"Unexpected user prompt parity: {case}")
        if should_change and "## Declared Input Contract" not in b["messages"]["user"]:
            raise ValueError(f"Missing candidate disclosure: {case}")
        results.append(
            {
                "case": case,
                "expected_change": should_change,
                "reference": {
                    k: hashlib.sha256(v.encode()).hexdigest()
                    for k, v in a["messages"].items()
                },
                "candidate": {
                    k: hashlib.sha256(v.encode()).hexdigest()
                    for k, v in b["messages"].items()
                },
            }
        )
    return {
        "reference": {k: v for k, v in reference.items() if k != "rows"},
        "candidate": {k: v for k, v in candidate.items() if k != "rows"},
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--reference-revision", required=True)
    parser.add_argument("--candidate-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--native-disclosure", action="store_true")
    args = parser.parse_args()
    result = compare(
        json.loads(args.reference.read_text()),
        json.loads(args.candidate.read_text()),
        args.reference_revision,
        args.candidate_revision,
        args.native_disclosure,
    )
    with args.output.open("x") as out:
        json.dump(result, out, indent=2)
        out.write("\n")


if __name__ == "__main__":
    main()

"""Capture whole lookup outcomes from original source without importing old infra.

Run with this exp checkout's frozen Python and --infra-checkout pointing to a
repository retaining the original revisions. Only temporal lookup behavior is
captured: synthetic eligible rows isolate timestamp, unit-time and error inputs.
"""

import argparse
import ast
import hashlib
import json
import math
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from types import SimpleNamespace

REVISIONS = (
    "345c802d82c71f72e1b73a90d2bf702d09d1865d",
    "7689fd58b91d410788e953b51ea69a9dbc528a7d",
    "349b6cd6d9766abbf3d87515b22e1005599a694b",
)
SOURCE = "src/core/runtime_control/observation_store.py"
CASES = [
    {
        "name": "offset_latest",
        "timestamps": ["2026-07-23T12:00:00+1400", "2026-07-23T11:00:00-1200"],
        "errors": [None, None],
    },
    {
        "name": "offset_drift",
        "timestamps": [
            "2026-07-23T12:00:00+1400",
            "2026-07-23T12:01:00+1400",
            "2026-07-23T12:02:00+1400",
            "2026-07-23T11:00:00-1200",
        ],
        "errors": [1.0, 1.0, 1.0, 0.0],
    },
    {
        "name": "equal_instants",
        "timestamps": ["2026-07-23T12:00:00+0200", "2026-07-23T10:00:00Z"],
        "errors": [None, None],
    },
    {
        "name": "malformed_before",
        "timestamps": ["!malformed", "2026-07-23T12:00:00+0000"],
        "errors": [None, None],
    },
    {
        "name": "malformed_after",
        "timestamps": ["2026-07-23T12:00:00+0000", "malformed"],
        "errors": [None, None],
    },
    {
        "name": "malformed_drift",
        "timestamps": ["malformed-a", "malformed-b", "malformed-c"],
        "errors": [1.0, 1.0, 1.0],
    },
    {
        "name": "fractional_offsets",
        "timestamps": [
            "2026-07-23T12:00:00+00:00:00.5",
            "2026-07-23T12:00:00-00:00:00.5",
        ],
        "errors": [None, None],
    },
    {
        "name": "leap_seconds",
        "timestamps": ["2026-07-23T11:59:60+0000", "2026-07-23T11:59:61+0000"],
        "errors": [None, None],
    },
    {
        "name": "naive",
        "timestamps": ["2026-07-23T11:00:00", "2026-07-23T12:00:00"],
        "errors": [None, None],
    },
]


class Result:
    """Capture original constructor arguments without importing its dependencies."""

    def __init__(self, **kwargs):
        self.value = kwargs


def original_lookup(source):
    tree = ast.parse(source)
    owner = next(
        n
        for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == "ObservationStore"
    )
    lookup = next(
        n
        for n in owner.body
        if isinstance(n, ast.FunctionDef) and n.name == "lookup_prior"
    )
    age = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_age_seconds"
    )
    extracted = "\n\n".join(
        textwrap.dedent(ast.get_source_segment(source, n)) for n in (lookup, age)
    )
    namespace = {
        "time": time,
        "math": math,
        "PriorLookup": Result,
        "observation_calibration_key": lambda obs, phase: "synthetic",
        "component_calibration_eligible": lambda obs, phase: True,
        "realized_unit_ms": lambda obs, phase: obs.unit_ms,
    }
    exec("from __future__ import annotations\n" + extracted, namespace)  # noqa: S102 -- reviewed git source oracle
    return extracted, namespace["lookup_prior"]


def evaluate(source):
    extracted, lookup = original_lookup(source)
    rows = []
    for case in CASES:
        observations = [
            SimpleNamespace(
                timestamp=timestamp,
                unit_ms=40.0 + index,
                components={
                    "training": SimpleNamespace(
                        prediction_error=(
                            None if error is None else SimpleNamespace(log_error=error)
                        )
                    )
                },
            )
            for index, (timestamp, error) in enumerate(
                zip(case["timestamps"], case["errors"], strict=True)
            )
        ]
        store = SimpleNamespace(read_all=lambda rows=observations: rows)
        policy = SimpleNamespace(
            drift_consecutive=3, contract_factor=1.5, max_age_days=90.0
        )
        for now in (1784808000.0, 1792584000.0, 1792587600.0):
            result = lookup(store, "synthetic", "training", policy=policy, now=now)
            rows.append({"case": case["name"], "now": now, "result": result.value})
    return extracted, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--infra-checkout", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(evaluate(sys.stdin.read())[1]))
        return
    if args.infra_checkout is None or args.output is None:
        parser.error("--infra-checkout and --output are required")
    if args.output.exists():
        parser.error("refusing to overwrite an existing oracle")
    references = []
    for revision in REVISIONS:
        source = subprocess.check_output(
            ["git", "-C", str(args.infra_checkout), "show", f"{revision}:{SOURCE}"],
            text=True,
        )
        extracted, _ = original_lookup(source)
        zones = []
        for zone in ("UTC", "America/Los_Angeles", "Asia/Shanghai"):
            output = subprocess.check_output(
                [sys.executable, __file__, "--worker"],
                input=source,
                text=True,
                env={**os.environ, "TZ": zone},
            )
            zones.append({"timezone": zone, "outcomes": json.loads(output)})
        references.append(
            {
                "revision": revision,
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "extracted_source": extracted,
                "extracted_sha256": hashlib.sha256(extracted.encode()).hexdigest(),
                "zones": zones,
            }
        )
    args.output.write_text(
        json.dumps(
            {"source": SOURCE, "cases": CASES, "references": references}, indent=2
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

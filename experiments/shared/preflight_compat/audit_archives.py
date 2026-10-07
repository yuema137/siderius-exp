"""Verify declared paper archives without importing models or running training."""

import argparse
import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from siderius_planner_compat.static_preflight_v6 import project_record


def _records(value):
    if isinstance(value, dict):
        if "exp_id" in value and "memory" in value and "status" in value:
            yield value
        for child in value.values():
            yield from _records(child)
    elif isinstance(value, list):
        for child in value:
            yield from _records(child)


def audit(inventory: Path, roots: dict[str, str]):
    declared = json.loads(inventory.read_text())
    cases = []
    for case in declared["cases"]:
        root = Path(roots.get(case["case"], case["archive_root"]))
        records = {}
        for source in case["source_files"]:
            path = root / source["path"]
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise ValueError(f"Archive hash changed: {path}")
            for record in _records(json.loads(raw)):
                records[(record.get("model_type"), record["exp_id"])] = record
        if len(records) != case["unique_record_count"]:
            raise ValueError(f"Record count changed for {case['case']}: {len(records)}")
        for record in records.values():
            before = deepcopy(record)
            if project_record(record) != before or record != before:
                raise ValueError(f"Archived input changed for {case['case']}")
        models = []
        for path in sorted((root / "plugin_source_sentinel").glob("*.py")):
            raw = path.read_bytes()
            tree = ast.parse(raw)
            calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            models.append(
                {
                    "name": path.name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "registers_buffer": "register_buffer" in calls,
                    "constructs_parameter": "Parameter" in calls,
                }
            )
        cases.append(
            {
                "case": case["case"],
                "verified_source_files": len(case["source_files"]),
                "unchanged_records": len(records),
                "archived_model_sources": models,
            }
        )
    return {
        "scope": "Declared archive hashes and record projection; AST model structure coverage only, no model execution or decision replay",
        "inventory_sha256": hashlib.sha256(inventory.read_bytes()).hexdigest(),
        "cases": cases,
        "api_calls": 0,
        "gpu_calls": 0,
        "training_calls": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument(
        "--roots",
        type=Path,
        help="Optional JSON mapping from case name to archive root",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    roots = json.loads(args.roots.read_text()) if args.roots else {}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit(args.inventory, roots), indent=2) + "\n")

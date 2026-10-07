"""Verify explicitly supplied historical checkouts without importing their code."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path


def check(references: dict[str, str]) -> dict:
    package = Path(__file__).parent / "src/siderius_planner_compat"
    matrix = json.loads(
        (package / "fixtures/storage_reference_matrix.json").read_text()
    )
    if set(references) != set(matrix["reference_revisions"]):
        raise ValueError(
            "Supply exactly the five reference names declared in the source matrix"
        )
    results = []
    for name, revision in matrix["reference_revisions"].items():
        root = Path(references[name]).resolve(strict=True)
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        if actual != revision:
            raise ValueError(
                f"{name}: checkout revision differs from the qualified reference"
            )
        source = (root / matrix["reference_source"]).read_bytes()
        if hashlib.sha256(source).hexdigest() != matrix["reference_source_sha256"]:
            raise ValueError(
                f"{name}: provenance source differs from the qualified reference"
            )
        engine = (root / "src/execute_tools/train_engine_sandbox.py").read_text()
        helper = next(
            node
            for node in ast.parse(engine).body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_setup_storage_provenance"
        )
        helper_sha = hashlib.sha256(
            ast.dump(helper, include_attributes=False).encode()
        ).hexdigest()
        if helper_sha != matrix["setup_helper_ast_sha256"]:
            raise ValueError(
                f"{name}: setup physical-byte producer differs from the qualified reference"
            )
        results.append(
            {
                "name": name,
                "revision": revision,
                "source_match": True,
                "setup_helper_match": True,
            }
        )
    return {"references": results, "reference_code_imported": False, "api_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--references",
        type=Path,
        required=True,
        help="JSON mapping the five task names to explicit reference checkouts",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check(json.loads(args.references.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

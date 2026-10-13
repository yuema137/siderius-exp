"""Offline supplementary repair witness; not recovered historical responses."""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--fixtures", type=Path, required=True)
parser.add_argument("--revision", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
os.environ["CUDA_VISIBLE_DEVICES"] = ""
for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(key, None)


def forbidden(*args, **kwargs):
    raise AssertionError("Network disabled during offline repair capture")


socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
socket.create_connection = forbidden
import agent
from agent.schemas.implementor import ImplementorInput
from nodes.ml_model_implementor.ml_model_implementor import _build_repair_prompt

root = Path(agent.__file__).resolve().parents[2]
if Path(sys.prefix).resolve() != (root / ".venv").resolve():
    raise ValueError("Use the selected checkout own frozen environment")
revision = subprocess.check_output(
    ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
).strip()
if revision != args.revision:
    raise ValueError("Executing revision differs from requested revision")
if subprocess.check_output(
    ["git", "-C", str(root), "status", "--porcelain", "--", "src"], text=True
).strip():
    raise ValueError("Commit source changes before capture")
args.output.mkdir(parents=True, exist_ok=False)
rows = []
for task in ("tess", "ligo", "project8", "tidmad"):
    fixture = args.fixtures / f"{task}-implementor-code.json"
    payload = json.loads(fixture.read_text())
    inp = ImplementorInput.model_validate(payload["arguments"]["input"])
    for with_history in (False, True):
        message = _build_repair_prompt(
            {"imports": "import torch", "model": "class Candidate: pass"},
            "Forward pass failed: synthetic regression witness",
            inp,
            [(1, "Earlier synthetic failure")] if with_history else None,
        )
        name = f"{task}-repair-" + ("history" if with_history else "first")
        (args.output / f"{name}.txt").write_text(message)
        rows.append(
            {
                "case": name,
                "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
                "input_fixture_sha256": hashlib.sha256(
                    fixture.read_bytes()
                ).hexdigest(),
            }
        )
(args.output / "receipt.json").write_text(
    json.dumps(
        {
            "infra_revision": revision,
            "scope": "Four recovered inputs with synthetic repair code and errors; no historical conversation replay",
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "api_calls": 0,
            "training_calls": 0,
            "results": rows,
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps({"cases": len(rows), "revision": revision}))

"""Check the four paper configurations against their historical proposer route.

Run with the candidate infra checkout's own Python. This checks construction
and the public routing interface; it does not run the proposal pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

# Historical audit expectations, not launch configuration. The experiment
# files remain the only routing inputs. See proposer-routing-audit.md.
PAPER_CONFIGS = {
    "tess": "experiments/phyts_tess/main_fixed_workflow/agents.json",
    "ligo": "experiments/phyts_ligo/main_fixed_workflow/agents.json",
    "project8": "experiments/phyts_project8/main_fixed_workflow_dual_representation/agents.json",
    "tidmad": "experiments/tidmad/main_fixed_workflow/iclr_official_v1.json",
}
HISTORICAL_REASONING = {
    "provider": "openai",
    "model_id": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "max_retries": None,
}


class RecordingBridge:
    def __init__(self, constructed: list, **settings):
        constructed.append(settings)

    def generate(self, *args, **kwargs):
        raise AssertionError("Construction check must not generate")

    def generate_text(self, *args, **kwargs):
        raise AssertionError("Construction check must not generate")


def check(exp_checkout: Path, expected_revision: str) -> dict:
    import agent
    from nodes.ml_model_proposal_agent import MLModelProposalAgent
    from workflows.llm_config import WorkflowLLMConfig

    infra = Path(agent.__file__).resolve().parents[2]
    if Path(sys.prefix).resolve() != (infra / ".venv").resolve():
        raise ValueError("Use the candidate infra checkout's own Python")
    revision = subprocess.check_output(
        ["git", "-C", str(infra), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != expected_revision:
        raise ValueError("Executing infra differs from --expected-revision")
    dirty = subprocess.check_output(
        ["git", "-C", str(infra), "status", "--porcelain", "--", "src"],
        text=True,
    )
    rows = []
    with TemporaryDirectory(prefix="paper-proposer-routing-") as temporary:
        for case, relative in PAPER_CONFIGS.items():
            source = (exp_checkout / relative).read_bytes()
            config = WorkflowLLMConfig.model_validate_json(source)
            constructed = []

            node = MLModelProposalAgent(
                **config.get("propose"),
                bridge_factory=partial(RecordingBridge, constructed),
                capability_index_path=str(Path(temporary) / f"{case}.json"),
            )
            routes = node.routing.model_dump(mode="json")
            expected = {
                stage: HISTORICAL_REASONING
                for stage in ("comparison", "reasoning", "proposing")
            }
            if routes != expected:
                raise ValueError(
                    f"{case}: effective routes differ from historical reasoning"
                )
            for stage in ("comparison", "causal_reasoning", "proposing"):
                if node.routing.for_stage(stage).model_dump() != HISTORICAL_REASONING:
                    raise ValueError(
                        f"{case}: public stage selection differs for {stage}"
                    )
            if constructed != [HISTORICAL_REASONING]:
                raise ValueError(
                    f"{case}: constructed bridge differs from historical reasoning"
                )
            rows.append(
                {
                    "case": case,
                    "config": relative,
                    "config_sha256": hashlib.sha256(source).hexdigest(),
                    "effective_routes": routes,
                    "constructed_bridges": constructed,
                    "status": "MATCH",
                }
            )
    sources = (
        "src/workflows/llm_config.py",
        "src/nodes/ml_model_proposal_agent/ml_model_proposal_agent.py",
        "src/nodes/ml_model_proposal_agent/routing.py",
    )
    return {
        "scope": "Node construction and public routing interface; not pipeline call dispatch",
        "infra_revision": revision,
        "infra_source_dirty": bool(dirty),
        "infra_source_sha256": {
            path: hashlib.sha256((infra / path).read_bytes()).hexdigest()
            for path in sources
        },
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "historical_reasoning": HISTORICAL_REASONING,
        "results": rows,
        "provider_calls": 0,
        "training_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument(
        "--exp-checkout", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument(
        "--output", type=Path, help="New receipt file; never overwritten"
    )
    args = parser.parse_args()
    report = check(args.exp_checkout.resolve(), args.expected_revision)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output is not None:
        with args.output.open("x") as handle:
            handle.write(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()

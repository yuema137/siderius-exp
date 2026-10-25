"""Offline reconstructed final validator requests; not historical wire captures."""

import argparse
import hashlib
import json
import os
import socket
import subprocess
from contextlib import nullcontext
from pathlib import Path

import yaml


def forbidden(*args, **kwargs):
    raise AssertionError("Offline qualification forbids network/provider effects")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"):
        os.environ.pop(key, None)

    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", required=True, type=Path)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--expected-exp-revision", required=True)
    parser.add_argument("--include-segmentation", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--historical", action="store_true")
    a = parser.parse_args()
    import sys

    import agent
    from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
    from agent.schemas.model_io_contract import ModelIOContract
    from agent.schemas.model_io_resolution import resolve_model_io_contract
    from agent.schemas.validator import ValidatorInput
    from nodes.ml_code_validator_agent.ml_code_validator_agent import (
        MLCodeValidatorAgent,
    )

    checkout = Path(agent.__file__).resolve().parents[2]
    require(
        Path(sys.prefix).resolve() == (checkout / ".venv").resolve(),
        "Checkout environment mismatch",
    )
    require(
        subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip()
        == a.expected_revision,
        "Revision mismatch",
    )
    require(
        not subprocess.check_output(
            ["git", "-C", str(checkout), "status", "--porcelain", "--", "src"],
            text=True,
        ).strip(),
        "Dirty framework source",
    )
    profile_spec = (
        a.exp
        / "experiments/shared/prompt_compat/profiles/paper-constraint-disclosure-v2.json"
    )
    selected = json.loads(profile_spec.read_text())["cases"]
    exp_revision = subprocess.check_output(
        ["git", "-C", str(a.exp), "rev-parse", "HEAD"], text=True
    ).strip()
    require(exp_revision == a.expected_exp_revision, "Experiment revision mismatch")
    sources = {
        str(profile_spec.relative_to(a.exp)): hashlib.sha256(
            profile_spec.read_bytes()
        ).hexdigest()
    }
    rows = []

    class Recorder:
        def __init__(self, **kwargs):
            self.messages = []

        def generate(self, system, user, *, label):
            require(label == "validator.code_review", "Unexpected review boundary")
            self.messages.append({"system": system, "user": user})
            return {
                "spec_alignment": False,
                "trainability_concerns": [],
                "implementation_issues": ["synthetic failure preserved"],
                "passed": False,
                "notes": "offline fixture",
            }

    for task in ("tess", "ligo", "project8", "tidmad"):
        selection = selected[task]
        composition = a.exp / selection["source_task_composition"]
        manifest = yaml.safe_load(composition.read_text())
        config_path = (composition.parent / manifest["task_config"]["config"]).resolve()
        config = yaml.safe_load(config_path.read_text())
        fc = config["forward_contract"]
        contract = resolve_model_io_contract(
            ModelIOContract.model_validate(fc["model_io"]), preset=fc.get("preset")
        )
        fixture = (
            a.exp
            / f"experiments/shared/prompt_compat/fixtures/{task}-implementor-reasoning.json"
        )
        original = json.loads(fixture.read_text())["arguments"]["input"]
        for source in (composition, config_path, fixture):
            sources[str(source.relative_to(a.exp))] = hashlib.sha256(
                source.read_bytes()
            ).hexdigest()

        profile_name = selection["task_composition_overlay"]["prompt_renderer"]
        profile = resolve_prompt_profile(profile_name) if a.historical else None
        for variant in ("clean", "pytest", "gradient", "absent"):
            inp = ValidatorInput(
                model_type="qualification_fixture",
                model_file_path="/fixture/model.py",
                test_file_path="/fixture/test.py",
                description_file_path="/fixture/description.md",
                config_fields={},
                model_description=original["model_description"],
                mathematical_definition=original["mathematical_definition"],
                model_io_contract=None if variant == "absent" else contract,
                expert_advice="Synthetic fixture: inspect declared scientific specification.",
                human_advice="Synthetic fixture: retain runtime failures.",
                constraint_context=None,
            )
            if a.include_segmentation:
                require(
                    "segmentation_applicability" in ValidatorInput.model_fields,
                    "Candidate lacks segmentation transport",
                )
                inp.segmentation_applicability = (
                    None
                    if variant == "absent"
                    else fc.get("segmentation_applicability")
                )
            runner = MLCodeValidatorAgent(bridge_factory=Recorder)
            with bind_prompt_profile(profile) if profile else nullcontext():
                verdict = runner._llm_review(
                    inp,
                    "# Synthetic fixture only; no model execution.\nclass Fixture: pass\n",
                    test_output="SYNTHETIC pytest failure: declared input rejected"
                    if variant == "pytest"
                    else None,
                    inst_err="SYNTHETIC gradient failure: backward graph disconnected"
                    if variant == "gradient"
                    else None,
                )
            require(verdict.passed is False, "Scripted failure was weakened")
            require(
                len(runner.bridge.messages) == 1, "Expected exactly one review request"
            )
            rows.append(
                {
                    "case": f"{task}-{variant}",
                    "profile": profile_name if a.historical else None,
                    "source_config": str(config_path.relative_to(a.exp)),
                    "source_sha256": hashlib.sha256(
                        config_path.read_bytes()
                    ).hexdigest(),
                    "segmentation_applicability": fc.get("segmentation_applicability"),
                    "normalized_contract": contract.model_dump(mode="json"),
                    "messages": runner.bridge.messages[0],
                }
            )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x") as out:
        json.dump(
            {
                "infra_revision": a.expected_revision,
                "exp_revision": exp_revision,
                "exp_worktree_status": subprocess.check_output(
                    ["git", "-C", str(a.exp), "status", "--porcelain"], text=True
                ).splitlines(),
                "source_closure": sources,
                "includes_segmentation": a.include_segmentation,
                "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "scope": "Source-reconstructed final requests through real _llm_review, synthetic plugin/errors/advice; not archived wire or model-execution equivalence",
                "api_calls": 0,
                "training_calls": 0,
                "rows": rows,
            },
            out,
            indent=2,
        )
    print(f"{len(rows)} final requests captured; all scripted failures preserved")


if __name__ == "__main__":
    main()

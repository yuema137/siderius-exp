"""Seal one selected native model, then evaluate held-out files without LLMs.

The native inference child owns model loading and decoding. This entrypoint does
not train, select a winner, change a checkpoint, or feed its result to a workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from agent.schemas.hyperparam_tuning import HyperparamTuningOutput
from core.sandbox_layout import training_checkpoint_path
from pydantic import BaseModel, ConfigDict, Field, field_validator

from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.tidmad.main_fixed_workflow.band_inputs import verify_band_inputs
from tutorials.paper.runner import (
    ROOT,
    child_environment,
    composition_identity,
    disjoint,
    verify_gpu,
)
from tutorials.paper.tidmad.runner import TidmadExperiment, selected_split


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_name: str = Field(pattern=r"^[A-Za-z0-9_]+$")
    exp_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    checkpoint: Path
    run_output_path: Path
    model_config_path: Path
    loss_config_path: Path
    generated_library: Path
    search_completed: bool
    inference_batch_size: int = Field(default=1, ge=1, le=32)

    @field_validator(
        "checkpoint",
        "run_output_path",
        "model_config_path",
        "loss_config_path",
        "generated_library",
    )
    @classmethod
    def absolute(cls, value):
        if not value.is_absolute():
            raise ValueError("candidate paths must be absolute")
        return value.resolve()


def digest(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def candidate_for_record(
    settings: TidmadExperiment,
    run_output_path: Path,
    exp_id: str,
    *,
    search_completed: bool = False,
    inference_batch_size: int = 1,
) -> Candidate:
    """Resolve artifacts for an explicitly chosen successful native attempt.

    The caller chooses using workflow validation/Health. This helper never
    chooses the best record, trains, or reads held-out test arrays.
    """
    path = run_output_path.resolve()
    if not path.is_relative_to(settings.workspace):
        raise ValueError("select a run record inside this experiment's workspace")
    output = HyperparamTuningOutput.model_validate_json(path.read_text())
    matches = [r for r in output.all_records if r.exp_id == exp_id]
    if len(matches) != 1 or matches[0].status != "success":
        raise ValueError("select one successful completed attempt from this run record")
    record = matches[0]
    fingerprint = composition_identity(settings, str(settings.composition))
    if (
        output.task_composition_fingerprint != fingerprint
        or record.task_composition_fingerprint != fingerprint
    ):
        raise ValueError(
            "selected model was not trained under this task/split identity"
        )
    if record.model_type != output.model_type:
        raise ValueError("run and attempt disagree on model identity")

    def config(name):
        files = list(path.parent.rglob(f"{name}_config_{exp_id}.json"))
        if len(files) != 1:
            raise ValueError(f"expected one persisted {name} config for {exp_id}")
        return files[0].resolve()

    sentinels = list(path.parent.rglob(f"_OK_{exp_id}"))
    if len(sentinels) != 1:
        raise ValueError("expected one native training-success marker for this attempt")
    return Candidate(
        model_name=record.model_type,
        exp_id=exp_id,
        run_output_path=path,
        checkpoint=training_checkpoint_path(
            sentinels[0].parent, record.model_type, exp_id
        ),
        model_config_path=config("model"),
        loss_config_path=config("loss"),
        generated_library=settings.workspace / "generated_library",
        search_completed=search_completed,
        inference_batch_size=inference_batch_size,
    )


def evidence(candidate: Candidate, settings: TidmadExperiment):
    if not candidate.search_completed:
        raise ValueError(
            "stop search and choose the model using validation before sealing"
        )
    expected = candidate_for_record(
        settings,
        candidate.run_output_path,
        candidate.exp_id,
        search_completed=candidate.search_completed,
        inference_batch_size=candidate.inference_batch_size,
    )
    if candidate != expected:
        raise ValueError(
            "candidate paths or model identity differ from the selected run record"
        )
    if not candidate.generated_library.is_dir():
        raise ValueError("use the selected run's generated_library directory")
    paths = [
        candidate.checkpoint,
        candidate.run_output_path,
        candidate.model_config_path,
        candidate.loss_config_path,
        *sorted(
            p
            for p in candidate.generated_library.rglob("*")
            if p.is_file() and p.suffix != ".pyc"
        ),
    ]
    if any(not p.is_file() for p in paths):
        raise ValueError("candidate artifacts are missing")
    if any(
        not disjoint(p, repo) for p in paths for repo in (ROOT, settings.infra_checkout)
    ):
        raise ValueError("candidate artifacts must be external")
    sentinel = candidate.checkpoint.parent / f"_OK_{candidate.exp_id}"
    if not sentinel.is_file():
        raise ValueError("native training success sentinel is missing")
    return {str(p): digest(p) for p in [*paths, sentinel, settings.composition]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()
    if args.seal == args.evaluate:
        raise ValueError("choose exactly one of --seal or --evaluate")
    settings = TidmadExperiment.model_validate_json(args.experiment.read_text())
    split = selected_split(settings)
    if split is None:
        raise ValueError("final testing requires a file-holdout task")
    candidate = Candidate.model_validate_json(args.candidate.read_text())
    output = args.output.resolve()
    if any(
        not disjoint(output, p)
        for p in (
            ROOT,
            settings.infra_checkout,
            settings.data_dir,
            settings.workspace,
            candidate.generated_library,
            candidate.checkpoint.parent,
        )
    ):
        raise ValueError(
            "keep final-test output separate from source, raw data, search and candidate artifacts"
        )
    revision = verify_framework_pin(ROOT, settings.infra_checkout)
    verify_installed_framework(revision, ROOT)
    current = {
        "candidate": candidate.model_dump(mode="json"),
        "artifacts": evidence(candidate, settings),
        "experiment_sha256": digest(args.experiment),
        "infra_revision": revision,
        "composition_fingerprint": composition_identity(
            settings, str(settings.composition)
        ),
        "exp_revision": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
    }
    if args.seal:
        output.mkdir(parents=True, exist_ok=False)
        (output / "selection.json").write_text(json.dumps(current, indent=2))
        print(
            f"Sealed selection: {output / 'selection.json'}. No test inference has run."
        )
        return
    if json.loads((output / "selection.json").read_text()) != current:
        raise ValueError("selected model/config/task changed after sealing")
    verify_band_inputs(ROOT, settings.data_dir, "0-3")
    verify_gpu(settings)
    # Exclusive marker prevents retries from quietly becoming model selection.
    with (output / "test-started.json").open("x") as stream:
        json.dump(
            {
                "authority": "diagnostic",
                "health": "not assessed",
                "sample_set": split.population("test"),
            },
            stream,
            indent=2,
        )
    sample_path = output / "test-sample-set.json"
    sample_path.write_text(json.dumps(split.population("test")))
    task = settings.composition.parent.parent
    from workflows.task_composition import compose_run_task_bindings

    composition = compose_run_task_bindings(str(settings.composition))
    model_io_path = output / "model-io.json"
    model_io_path.write_text(
        composition.forward_contract.model_io.model_dump_json(indent=2)
    )
    command = [
        str(settings.infra_checkout / ".venv/bin/python"),
        "-B",
        "-m",
        "execute_tools.inference_single",
        "--mode",
        "agent",
        "--data_dir",
        str(settings.data_dir),
        "--output_dir",
        str(output),
        "--denoising_model",
        candidate.model_name,
        "--model_cfg",
        str(candidate.model_config_path),
        "--loss_cfg",
        str(candidate.loss_config_path),
        "--model_path",
        str(candidate.checkpoint),
        "--exp_id",
        candidate.exp_id,
        "--run_name",
        "final_test",
        "--inference_batch_size",
        str(candidate.inference_batch_size),
        "--model_io_json",
        str(model_io_path),
        "--sample_set_json",
        str(sample_path),
        "--dataset_profile_json",
        str(task / "resolved/dataset_profile.json"),
        "--task_manifest",
        str(settings.composition),
        "--task_data_path_id",
        "tidmad_file_split",
    ]
    env = child_environment(settings)
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(candidate.generated_library)
    # This process does not need credentials; do not pass provider keys to inference.
    for name in tuple(env):
        if name.endswith("_API_KEY"):
            env.pop(name)
    (output / "inference-command.json").write_text(json.dumps(command, indent=2))
    subprocess.run(command, cwd=settings.infra_checkout, env=env, check=True)
    if current["artifacts"] != evidence(candidate, settings):
        raise ValueError("candidate changed during evaluation")
    import math

    from execute_tools.task_data_path import EvaluationReadRequest
    from workflows.task_composition import bind_run_task_composition

    with bind_run_task_composition(
        composition, physical_data_root=str(settings.data_dir)
    ):
        scope = composition.task_data_path.build_final_test_scope()
        payload = composition.task_data_path.read_evaluation_payload(
            EvaluationReadRequest(
                deliverable_dir=str(output),
                model_type=candidate.model_name,
                run_name="final_test",
                exp_id=candidate.exp_id,
            )
        )
        outcome = composition.metric.evaluate(
            payload.deliverables,
            evaluation_payload=payload.value,
            task_scope=scope,
            data_dir=str(settings.data_dir),
        )
    score = getattr(outcome, "scalar", None)
    finite = score is not None and math.isfinite(score)
    (output / "result.json").write_text(
        json.dumps(
            {
                "authority": "diagnostic",
                "health": "not assessed",
                "metric": outcome.metric_id,
                "score": score if finite else None,
                "finite": finite,
                "metric_outcome": json.loads(outcome.model_dump_json()),
                "selection": current,
            },
            indent=2,
            allow_nan=False,
        )
    )
    print(
        f"Final test result: {output / 'result.json'}. Do not feed it back into model selection."
    )


if __name__ == "__main__":
    main()

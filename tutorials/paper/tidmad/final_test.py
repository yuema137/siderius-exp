"""Seal one selected native model, then evaluate held-out frequencies without LLMs.

The native inference child owns model loading and decoding. This entrypoint does
not train, select a winner, change a checkpoint, or feed its result to a workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

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
    model_config_path: Path
    loss_config_path: Path
    generated_library: Path
    search_completed: bool
    inference_batch_size: int = Field(default=1, ge=1, le=32)

    @field_validator(
        "checkpoint", "model_config_path", "loss_config_path", "generated_library"
    )
    @classmethod
    def absolute(cls, value):
        if not value.is_absolute():
            raise ValueError("candidate paths must be absolute")
        return value.resolve()


def digest(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def evidence(candidate: Candidate, settings: TidmadExperiment):
    if not candidate.search_completed:
        raise ValueError(
            "stop search and choose the model using validation before sealing"
        )
    if not candidate.generated_library.is_dir():
        raise ValueError("use the selected run's generated_library directory")
    paths = [
        candidate.checkpoint,
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
    if split is None or not settings.catalog_reviewed:
        raise ValueError("final testing requires a reviewed frequency-holdout task")
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
    data = verify_band_inputs(ROOT, settings.data_dir, "0-3")
    if data["file_sha256"] != split.catalog.source_sha256:
        raise ValueError("held-out catalog source mismatch")
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
        "tidmad_frequency_split",
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
    from execute_tools.dataset_config import load_dataset_profile
    from execute_tools.deliverable_spec import derive_tidmad_deliverable_spec

    from tasks.tidmad.runtime.scoring import coerce_nonfinite_to_none, score_vector

    profile = load_dataset_profile(str(task / "resolved/dataset_profile.json"))
    naming = derive_tidmad_deliverable_spec(profile).naming
    anchors = json.loads((settings.data_dir / "segment_anchors.json").read_text())
    vector, score = score_vector(
        data_dir=str(output),
        raw_data_dir=str(settings.data_dir),
        sample_set=split.population("test"),
        anchor_map=anchors["anchors"],
        s_max=anchors["s_max"],
        profile=profile,
        parallel=False,
        denoised_filename_fn=lambda i: str(
            output
            / naming.name(
                model_type=candidate.model_name,
                run_name="final_test",
                exp_id=candidate.exp_id,
                input_identity=i,
            )
        ),
    )
    import math

    (output / "result.json").write_text(
        json.dumps(
            {
                "authority": "diagnostic",
                "health": "not assessed",
                "metric": "tidmad_denoising_score",
                "score": score if math.isfinite(score) else None,
                "finite": math.isfinite(score),
                "per_file": coerce_nonfinite_to_none(vector),
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

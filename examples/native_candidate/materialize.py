"""Inspect an exported task, then explicitly materialize a candidate-only project.

Copy this recipe and the task assets into the external project before executing
it with the selected framework checkout's own frozen Python. Never imports exp.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from tools.candidate_console import ConsoleConfig
from tools.candidate_console.files import canonical, credential_values
from tools.candidate_console.models import TaskChoice
from tools.candidate_operations import OperationStoreConfig
from tools.candidate_prepare import ReusableCandidatePreparationRequest
from tools.setup_review.composition_check import observe_composition
from tools.setup_review.composition_models import (
    CompositionJob,
    CompositionObservation,
    TaskCheckSettings,
)
from tools.setup_review.composition_transport import manifest_digest
from tools.workflow_authoring.models import Project
from tools.workflow_authoring.service import digest
from workflows.definition import (
    ReusableTaskReferences,
    ReusableWorkflowDocument,
    TaskBinding,
    render_workflow_source,
)
from workflows.llm_config import WorkflowLLMConfig


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    example_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    run_name: str
    package_id: str
    revision: str
    framework_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    asset_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    task_directory: str
    label: str
    workflow: ReusableWorkflowDocument


class Inspection(BaseModel):
    """Unaccepted native observation; not a task release or launch authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    project: Path
    data: Path
    framework: Path
    profile: Profile
    observation: CompositionObservation


def runtime(framework: Path, profile: Profile) -> None:
    """Refuse another checkout's interpreter, imports, or unreviewed framework."""
    from tools.setup_review import composition_check

    if Path(sys.prefix).resolve() != framework / ".venv":
        raise ValueError("use this framework checkout's own frozen .venv/bin/python")
    if (
        Path(composition_check.__file__).resolve()
        != framework / "src/tools/setup_review/composition_check.py"
    ):
        raise ValueError("framework imports do not belong to the selected checkout")
    revision = subprocess.check_output(
        ["git", "-C", str(framework), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(framework), "status", "--porcelain"], text=True
    )
    if revision != profile.framework_revision or dirty:
        raise ValueError(
            "select the exact clean framework revision declared by the example"
        )


def task_paths(project: Path, profile: Profile) -> tuple[Path, Path]:
    task = (project / profile.task_directory).resolve()
    manifest = (project / profile.workflow.definition.task.manifest).resolve()
    if not task.is_relative_to(project) or not manifest.is_relative_to(task):
        raise ValueError("task assets must remain within the external project")
    return task, manifest


def observe(
    project: Path, data: Path, framework: Path, profile: Profile, scratch: Path
) -> CompositionObservation:
    runtime(framework, profile)
    task, manifest = task_paths(project, profile)
    if not data.is_dir() or data.is_relative_to(task) or task.is_relative_to(data):
        raise ValueError("supply an existing data directory separate from task sources")
    config = WorkflowLLMConfig.model_validate_json(
        (project / "llm/agents.json").read_bytes()
    )
    job = CompositionJob(
        manifest=str(manifest),
        manifest_sha256=manifest_digest(str(manifest)),
        planner_strategy=config.get("tune").get("planner_strategy"),
        scratch=str(scratch),
        settings=TaskCheckSettings(timeout_seconds=60),
    )
    result = observe_composition(job, (task,), data_root=data)
    if result.result.outcome != "passed" or result.result.task is None:
        raise ValueError(
            "native task inspection failed; inspect the retained child result"
        )
    return result


def inspect_task(
    project: Path, data: Path, framework: Path, profile_path: Path, output: Path
) -> None:
    """Save native facts without writing a workflow or accepting a task."""
    profile = Profile.model_validate_json(profile_path.read_bytes())
    runtime(framework, profile)
    if not Path(__file__).resolve().is_relative_to(project):
        raise ValueError(
            "copy/export the recipe into your external project before running it"
        )
    if output.exists():
        raise ValueError("choose a fresh inspection output")
    routing = project / "llm/agents.json"
    if not routing.exists():
        content = (framework / "configs/llm/openai_smoke_luna.json").read_bytes()
        WorkflowLLMConfig.model_validate_json(content)
        routing.parent.mkdir(parents=True, exist_ok=True)
        with routing.open("xb") as stream:
            stream.write(content)
    output.parent.mkdir(parents=True, exist_ok=True)
    observation = observe(
        project, data, framework, profile, output.with_suffix(".scratch")
    )
    record = Inspection(
        project=project,
        data=data,
        framework=framework,
        profile=profile,
        observation=observation,
    )
    with output.open("x") as stream:
        stream.write(record.model_dump_json(indent=2) + "\n")
    facts = observation.result.task
    assert facts is not None
    print(
        f"Inspected, NOT accepted: {profile.label}. Primary metric: "
        f"{facts.primary_metric['id']} ({facts.primary_metric['direction']} is better)."
    )
    print(
        f"Read native facts: {output}. No workflow, candidate, training or score was created."
    )


def document(
    profile: Profile, manifest: Path, data: Path, binding: TaskBinding
) -> ReusableWorkflowDocument:
    """Bind the native-validated inert declaration to the checked current snapshot."""
    return profile.workflow.model_copy(
        update={
            "task_binding": binding,
            "definition": profile.workflow.definition.model_copy(
                update={
                    "task": ReusableTaskReferences(
                        manifest=str(manifest), data_root=str(data)
                    ),
                }
            ),
        }
    )


def console_config(
    record: Inspection, binding: TaskBinding, credential_file: Path, port: int
) -> ConsoleConfig:
    """Build inert console policy; credentials stay in the caller-owned private file."""
    project, profile = record.project, record.profile
    task, manifest = task_paths(project, profile)
    runs = str(project / "runs")
    editor = Project(
        project_id=profile.example_id,
        project_root=project,
        source_file=project / "workflow.py",
        recovery_directory=project / "editor-recovery",
    )
    choice = TaskChoice(
        task_id=profile.example_id,
        label=profile.label,
        task_manifest=str(manifest),
        data_root=str(record.data),
        llm_config_file=str(project / "llm/agents.json"),
        task_read_only=(str(task),),
        preparation_root=str(project / "preparations"),
        candidate_root=str(project / "candidates"),
        reusable_runs_root=runs,
        preparation_timeout_seconds=60,
        candidate_timeout_seconds=600,
        candidate_network=True,
        candidate_devices=(),
        candidate_environment_names=("OPENAI_API_KEY",),
        allowed_output_types=profile.workflow.preparation_options.allowed_output_types,
        task_revision=binding,
    )
    return ConsoleConfig(
        operation_store=OperationStoreConfig(
            state_root=str(project / "state"),
            preparation_roots=(choice.preparation_root, runs),
            candidate_roots=(choice.candidate_root, runs),
        ),
        tasks=(choice,),
        editor_projects=(editor,),
        runnable_editor_projects=(profile.example_id,),
        port=port,
        browser_origin=f"http://127.0.0.1:{port}",
        auth_token_file=str(project / "console-token"),
        credential_file=str(credential_file),
    )


def accept_task(
    path: Path, *, accepted: bool, credential_file: Path, port: int
) -> None:
    """Explicitly accept checked current facts; never publish an immutable release."""
    if not accepted:
        raise ValueError("read the inspection, then explicitly supply --accept-task")
    record = Inspection.model_validate_json(path.read_bytes())
    project, profile = record.project, record.profile
    names = (
        "workflow.py",
        "console.json",
        "prepare-request.json",
        "console-token",
        "state",
        "runs",
        "preparations",
        "candidates",
        "editor-recovery",
    )
    if any((project / name).exists() for name in names):
        raise ValueError(
            "project output already exists; do not overwrite source or run evidence"
        )
    previous = record.observation.result.task
    if record.observation.result.outcome != "passed" or previous is None:
        raise ValueError("select a successful unaccepted native inspection")
    binding = TaskBinding(
        package_id=profile.package_id,
        revision=profile.revision,
        semantic_fingerprint=previous.semantic_fingerprint,
        task_data_path_id=previous.task_data_path_id,
    )
    _, manifest = task_paths(project, profile)
    authored = document(profile, manifest, record.data, binding)
    config = console_config(record, binding, credential_file, port)
    try:
        for value in (str(project), str(record.data), str(credential_file)):
            canonical(value)
        credential_values(
            str(credential_file)
        )  # Validate shape/permissions; never log values.
    except (OSError, ValueError):
        raise ValueError(
            "provide a canonical caller-owned mode600 credential JSON file"
        ) from None
    source = project / "workflow.py"
    payload = render_workflow_source(authored).encode()
    choice = config.tasks[0]
    request = ReusableCandidatePreparationRequest(
        source_path=str(source),
        project_root=str(project),
        expected_source_sha256=digest(payload),
        runs_root=str(project / "runs"),
        run_id=uuid4(),
        run_name=profile.run_name,
        **choice.model_dump(
            include={
                "llm_config_file",
                "preparation_timeout_seconds",
                "candidate_timeout_seconds",
                "task_read_only",
                "candidate_network",
                "candidate_devices",
                "candidate_environment_names",
            }
        ),
    )
    files = {
        "workflow.py": payload,
        "console.json": config.model_dump_json(indent=2).encode(),
        "prepare-request.json": request.model_dump_json(indent=2).encode(),
    }
    current = observe(
        project,
        record.data,
        record.framework,
        profile,
        path.with_suffix(".accept-scratch"),
    )
    facts = current.result.task
    assert facts is not None
    if (previous.semantic_fingerprint, previous.task_data_path_id) != (
        facts.semantic_fingerprint,
        facts.task_data_path_id,
    ):
        raise ValueError(
            "task changed after inspection; inspect again before acceptance"
        )
    # All paths/configuration and output bytes are derived before publication.
    for name in ("state", "runs", "preparations", "candidates", "editor-recovery"):
        (project / name).mkdir(mode=0o700)
    for name, content in files.items():
        with (project / name).open("xb") as stream:
            stream.write(content)
    fd = os.open(project / "console-token", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(secrets.token_urlsafe(32))
    print(
        f"Explicitly accepted checked CURRENT SNAPSHOT: {profile.label}. Created {source} and console.json."
    )
    print(
        "No immutable task release, candidate launch, training or score. Prepare and Launch remain separate."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect")
    for name in ("project", "data", "framework", "profile", "output"):
        inspect_parser.add_argument("--" + name, type=Path, required=True)
    accept_parser = commands.add_parser("accept")
    accept_parser.add_argument("--inspection", type=Path, required=True)
    accept_parser.add_argument("--accept-task", action="store_true")
    accept_parser.add_argument("--credential-file", type=Path, required=True)
    accept_parser.add_argument("--port", type=int, default=8740)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            inspect_task(
                *(
                    getattr(args, name).resolve()
                    for name in ("project", "data", "framework", "profile", "output")
                )
            )
        else:
            accept_task(
                args.inspection.resolve(),
                accepted=args.accept_task,
                credential_file=args.credential_file.absolute(),
                port=args.port,
            )
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(2, f"Example refused: {error}\n")


if __name__ == "__main__":
    main()

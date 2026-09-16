"""Run frozen segment models on evaluator-owned validation inputs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .model import FILES_BY_BAND


@dataclass(frozen=True)
class FinalInferenceRuntime:
    """Root-owned execution settings for untrusted candidate predictors."""

    python: Path = Path("/opt/tidmad-inference/venv/bin/python")
    systemd_run: Path = Path("/usr/bin/systemd-run")
    session_root: Path = Path("/var/lib/tidmad-baseline/inference-sessions")
    user: str = "baseline-inference"
    group: str = "baseline-inference"
    timeout_seconds_per_file: int = 1800


def _deliverable_name(task_root: Path, file_index: int) -> str:
    spec = json.loads(
        (task_root / "tasks/tidmad/resolved/deliverable_spec.json").read_text()
    )
    naming = spec["naming"]
    return (
        f"{naming['prefix']}_{file_index:0{int(naming['index_width'])}d}"
        f"{naming['extension']}"
    )


def _seal_for_runner(root: Path, runtime: FinalInferenceRuntime) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        shutil.chown(path, user="root", group=runtime.group)
        path.chmod(0o550 if path.is_dir() else 0o440)
    shutil.chown(root, user="root", group=runtime.group)
    root.chmod(0o550)


def _command(
    *,
    runtime: FinalInferenceRuntime,
    candidate: Path,
    input_path: Path,
    output_path: Path,
    session_root: Path,
    required_output_kind: str | None = None,
) -> list[str]:
    command = [
        str(runtime.systemd_run),
        "--quiet",
        "--wait",
        "--pipe",
        "--collect",
        "--service-type=exec",
        f"--uid={runtime.user}",
        f"--gid={runtime.group}",
        "--property=NoNewPrivileges=yes",
        "--property=PrivateTmp=yes",
        "--property=ProtectHome=yes",
        "--property=ProtectSystem=strict",
        "--property=RestrictAddressFamilies=AF_UNIX",
        "--property=KillMode=control-group",
        f"--property=RuntimeMaxSec={runtime.timeout_seconds_per_file}",
        "--property=TimeoutStopSec=30",
        f"--property=ReadWritePaths={session_root}",
        f"--working-directory={candidate}",
        f"--setenv=HOME={session_root / 'home'}",
        f"--setenv=TMPDIR={session_root / 'tmp'}",
        "--setenv=PYTHONNOUSERSITE=1",
        str(runtime.python),
        "-I",
        "-m",
        "baseline_harness.segment_inference",
        "--candidate",
        str(candidate),
        "--input-file",
        str(input_path),
        "--output-file",
        str(output_path),
    ]
    if required_output_kind is not None:
        command.extend(("--required-output-kind", required_output_kind))
    return command


def run_candidate_inference(
    *,
    winners: dict[str, tuple[str, Path]],
    task_root: Path,
    input_root: Path,
    output_root: Path,
    runtime: FinalInferenceRuntime | None = None,
    files_by_band: Mapping[str, tuple[int, ...]] = FILES_BY_BAND,
    required_output_kind: str | None = None,
) -> Path:
    """Evaluate immutable candidates without exposing validation files to the agent."""

    runtime = runtime or FinalInferenceRuntime()
    if output_root.exists():
        raise FileExistsError(f"final inference output already exists: {output_root}")
    output_root.mkdir(parents=True)
    try:
        for band, (_candidate_id, retained) in winners.items():
            source = retained / "candidate"
            if not (source / "model.pt").is_file():
                raise ValueError(f"winner lacks required model.pt: {source}")
            for file_index in files_by_band[band]:
                input_name = f"abra_validation_{file_index:04d}.h5"
                raw_input = input_root / input_name
                if not raw_input.is_file():
                    raise FileNotFoundError(f"evaluation input missing: {raw_input}")
                with tempfile.TemporaryDirectory(
                    prefix="inference-",
                    dir=runtime.session_root,
                ) as raw_session:
                    session = Path(raw_session)
                    shutil.chown(session, user="root", group=runtime.group)
                    session.chmod(0o750)
                    candidate = session / "candidate"
                    shutil.copytree(source, candidate)
                    _seal_for_runner(candidate, runtime)
                    input_path = session / "input.h5"
                    shutil.copyfile(raw_input, input_path)
                    shutil.chown(input_path, user="root", group=runtime.group)
                    input_path.chmod(0o440)
                    for name in ("home", "tmp", "output"):
                        path = session / name
                        path.mkdir()
                        shutil.chown(path, user=runtime.user, group=runtime.group)
                        path.chmod(0o700)
                    temporary_output = session / "output" / "prediction.h5"
                    command = _command(
                        runtime=runtime,
                        candidate=candidate,
                        input_path=input_path,
                        output_path=temporary_output,
                        session_root=session,
                        required_output_kind=required_output_kind,
                    )
                    subprocess.run(
                        command,
                        check=True,
                        timeout=runtime.timeout_seconds_per_file + 60,
                    )
                    completion_marker = temporary_output.with_suffix(
                        temporary_output.suffix + ".complete"
                    )
                    if not completion_marker.is_file():
                        raise RuntimeError(
                            f"segment-model inference did not complete for file {file_index}"
                        )
                    if temporary_output.is_symlink() or not temporary_output.is_file():
                        raise RuntimeError(
                            f"segment model did not create a regular output for file {file_index}"
                        )
                    destination = output_root / _deliverable_name(
                        task_root, file_index
                    )
                    os.replace(temporary_output, destination)
        return output_root
    except BaseException:
        shutil.rmtree(output_root, ignore_errors=True)
        raise

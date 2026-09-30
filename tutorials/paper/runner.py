"""Preview or launch a fresh TESS teaching run through the native chain.

This adapter owns tutorial settings and a receipt, not a campaign clock.
The historical six-hour supervisor remains a separate entrypoint.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from workflows.llm_config import WorkflowLLMConfig

from experiments.shared.fixed_workflow_config import render_siderius_args
from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.shared.information_treatment import resolve_information_treatment
from experiments.shared.workflow_credentials import required_workflow_api_keys

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "experiments/phyts_tess/main_fixed_workflow/workflow.json"
TREATMENT = (
    ROOT / "experiments/phyts_tess/information_treatments/main-fixed-no-prior.yaml"
)


class TutorialExperiment(BaseModel):
    """One teaching experiment: task selection, run budgets and local bindings.

    Scientific declarations remain owned by the selected task package. This
    adapter selects the existing TESS fixed workflow and NoPrior treatment;
    it is not the repository-wide experiment schema.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["siderius-tess-tutorial-v1"]
    infra_checkout: Path
    data_dir: Path
    workspace: Path
    run_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
    gpu: Literal["RTX 5090", "H100"]
    iterations: int = Field(default=1, ge=1, le=100)
    epochs: int = Field(default=1, ge=1, le=100)
    trial_minutes: float = Field(default=2, gt=0, le=120)
    formal_minutes: float = Field(default=5, gt=0, le=120)
    vram_gib: float = Field(default=8, gt=0, le=80)
    trial_train_fraction: float | None = Field(default=None, ge=0.01, le=1)
    trial_val_fraction: float | None = Field(default=None, ge=0.01, le=1)
    formal_train_fraction: float = Field(default=1.0, ge=0.01, le=1)
    formal_val_fraction: float = Field(default=1.0, ge=0.01, le=1)
    trial_vram_gib: float | None = Field(default=None, gt=0, le=80)
    formal_vram_gib: float | None = Field(default=None, gt=0, le=80)
    composition: Path | None = None
    llm_config: Path | None = None
    # This entrypoint deliberately preserves the NoPrior treatment.
    advice_file: None = None

    @field_validator(
        "infra_checkout", "data_dir", "workspace", "composition", "llm_config"
    )
    @classmethod
    def absolute_path(cls, value: Path | None) -> Path | None:
        if value is not None and not value.is_absolute():
            raise ValueError(
                "use an absolute path; relative paths depend on the notebook cwd"
            )
        return value.resolve() if value is not None else None


class TutorialReceipt(BaseModel):
    """Reviewable launch evidence, with the executable command carried explicitly."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["tess-teaching-demo"] = "tess-teaching-demo"
    scientific_reproduction: Literal[False] = False
    settings: TutorialExperiment
    infra_revision: str
    exp_revision: str
    command: tuple[str, ...]
    required_api_keys: tuple[str, ...]
    api_key_status: dict[str, bool]
    composition_fingerprint: str
    llm_config_sha256: str
    data_sha256: dict[str, str] | None = None
    gpu: str | None = None


def disjoint(left: Path, right: Path) -> bool:
    """Reject equality and either direction of nesting after symlink resolution."""
    left, right = left.resolve(), right.resolve()
    return not (left.is_relative_to(right) or right.is_relative_to(left))


def validate_locations(settings: TutorialExperiment) -> None:
    """Keep source, data, and all run output in separate directory trees."""
    for checkout in (ROOT, settings.infra_checkout):
        if not disjoint(settings.workspace, checkout) or not disjoint(
            settings.data_dir, checkout
        ):
            raise ValueError("workspace and data must be outside both checkouts")
    if not disjoint(settings.workspace, settings.data_dir):
        raise ValueError("workspace and data must be separate")
    if settings.workspace.exists():
        raise ValueError("tutorial launches require a new workspace; choose a new path")
    for external in (settings.composition, settings.llm_config):
        if external is not None:
            if any(
                not disjoint(external, repo) for repo in (ROOT, settings.infra_checkout)
            ):
                raise ValueError(
                    "editable configuration must be outside both checkouts; copy it into your project"
                )
            if not external.is_file():
                raise ValueError(f"missing configuration: {external}")
            if external.is_relative_to(settings.workspace) or external.is_relative_to(
                settings.data_dir
            ):
                raise ValueError(
                    "editable configuration must be outside data and workspace"
                )


def build_command(
    settings: TutorialExperiment,
    *,
    workflow: Path = WORKFLOW,
    treatment_path: Path = TREATMENT,
) -> list[str]:
    """Reuse production workflow/treatment renderers, overriding only demo knobs."""
    validate_locations(settings)
    args = render_siderius_args(
        workflow, repository_root=ROOT, siderius_checkout=settings.infra_checkout
    )
    replacements = {
        "--num_iterations": str(settings.iterations),
        "--max_epochs": str(settings.epochs),
        "--trial_max_epochs": str(settings.epochs),
        "--formal_max_epochs": str(settings.epochs),
        "--trial_time_budget_minutes": str(settings.trial_minutes),
        "--formal_time_budget_minutes": str(settings.formal_minutes),
        "--trial_vram_budget_gb": str(settings.trial_vram_gib or settings.vram_gib),
        "--formal_vram_budget_gb": str(settings.formal_vram_gib or settings.vram_gib),
        "--formal_portion": str(settings.formal_train_fraction),
        "--formal_eval_portion": str(settings.formal_val_fraction),
    }
    if settings.composition is not None:
        replacements["--task_composition"] = str(settings.composition)
    if settings.llm_config is not None:
        replacements["--llm_config"] = str(settings.llm_config)
    for flag, value in replacements.items():
        if flag in args:
            args[args.index(flag) + 1] = value
        else:
            args.extend([flag, value])
    # Explicit Trial fractions become the framework's experiment-fixed lock.
    for flag, value in (
        ("--trial_portion", settings.trial_train_fraction),
        ("--eval_portion", settings.trial_val_fraction),
    ):
        if value is not None:
            args.extend([flag, str(value)])
    treatment = resolve_information_treatment(
        treatment_path,
        repository_root=ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )
    return [
        "bash",
        str(settings.infra_checkout / "scripts/launch/run_chain.sh"),
        "--mode",
        "lilab",
        "--workspace",
        str(settings.workspace),
        "--run_name",
        settings.run_name,
        "--data_dir",
        str(settings.data_dir),
        "--no_auto_resume",
        "--healthgate_mode",
        "blocking",
        "--result_authority",
        "diagnostic",
        *treatment.siderius_args(),
        *args,
    ]


def command_value(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def verify_data(
    data: Path, populations: dict[str, set[str]] | None = None
) -> dict[str, str]:
    """Require exactly the two staged archives and every declared curve key."""
    import numpy as np

    from tasks.phyts_tess.tools.stage_data import STAGED_FILENAME, _manifest_keys

    expected = {STAGED_FILENAME.format(split=split) for split in ("train", "val")}
    if not data.is_dir() or {p.name for p in data.iterdir()} != expected:
        raise ValueError(
            "data_dir must contain only tess_rotation_train.npz and tess_rotation_val.npz"
        )
    hashes = {}
    for split, keys in (
        populations if populations is not None else _manifest_keys()
    ).items():
        path = data / STAGED_FILENAME.format(split=split)
        if path.is_symlink():
            raise ValueError("stage regular archives, not symlinks to a raw data tree")
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != keys:
                raise ValueError(
                    f"{split} archive differs from the task identity manifest"
                )
            for key in archive.files:
                curve = archive[key]
                if curve.ndim != 1 or not curve.size or not np.isfinite(curve).all():
                    raise ValueError(f"{split} archive contains an invalid flux curve")
        with path.open("rb") as stream:
            hashes[path.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return hashes


def verify_gpu(settings: TutorialExperiment) -> str:
    """Require one supported physical GPU and a working CUDA allocation in infra."""
    try:
        probe = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ValueError(
            "NVIDIA GPU detection failed. Run nvidia-smi in this terminal; install/enable the NVIDIA driver "
            "and GPU access for this container/job. AMD and Intel GPUs are unsupported."
        ) from error
    rows = probe.stdout.strip().splitlines()
    if len(rows) != 1 or settings.gpu not in rows[0]:
        raise ValueError(
            f"expected one {settings.gpu}; observed {rows}. Set gpu in your saved experiment JSON to the actual supported device (RTX 5090 or H100). Other NVIDIA devices need the hardware adaptation described in the README; AMD/Intel are unsupported."
        )
    capacity_gib = float(rows[0].rsplit(",", 1)[1].strip()) / 1024
    if (
        max(
            settings.trial_vram_gib or settings.vram_gib,
            settings.formal_vram_gib or settings.vram_gib,
        )
        >= capacity_gib
    ):
        raise ValueError(
            "VRAM budget must be below physical capacity, leaving driver/runtime headroom. Lower vram_gib (and trial_vram_gib/formal_vram_gib if set) in your saved experiment JSON."
        )
    try:
        subprocess.run(
            [
                str(settings.infra_checkout / ".venv/bin/python"),
                "-c",
                (
                    "import torch; assert torch.version.hip is None; "
                    "assert torch.cuda.is_available(); torch.empty(1, device='cuda'); "
                    "torch.cuda.synchronize()"
                ),
            ],
            check=True,
            env=child_environment(settings),
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(
            f"CUDA allocation failed in {settings.infra_checkout}. "
            "Run uv sync --group dev --frozen in the infra checkout, verify its own PyTorch CUDA installation "
            "and NVIDIA driver, and free GPU memory before retrying."
        ) from error
    return rows[0]


def child_environment(settings: TutorialExperiment) -> dict[str, str]:
    """Keep credentials in the environment and bind generated artifacts to this run."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in (
        "PYTHONPATH",
        "SIDERIUS_PLUGIN_DIRS",
        "AGENT_GENERATED_DIR",
        "SIDERIUS_MODEL_PLUGIN_PATH",
        "SIDERIUS_LOSS_PLUGIN_PATH",
        "SIDERIUS_LOSS_DIRS",
    ):
        env.pop(name, None)
    env.update(
        {
            "SIDERIUS_GENERATED_LIBRARY_DIR": str(
                settings.workspace / "generated_library"
            ),
            "SIDERIUS_CHAIN_WORKSPACE": str(settings.workspace),
            "SIDERIUS_CALIBRATION_DIR": str(settings.workspace / "calibration"),
        }
    )
    return env


def composition_identity(settings: TutorialExperiment, manifest: str) -> str:
    """Resolve with the infra environment and run-local plugins, never user defaults."""
    result = subprocess.run(
        [
            str(settings.infra_checkout / ".venv/bin/python"),
            "-c",
            (
                "import sys; "
                "from workflows.task_composition import compose_run_task_bindings; "
                "print(compose_run_task_bindings(sys.argv[1]).semantic_fingerprint)"
            ),
            manifest,
        ],
        cwd=settings.infra_checkout,
        env=child_environment(settings),
        check=True,
        capture_output=True,
        text=True,
    )
    fingerprint = result.stdout.strip().splitlines()[-1]
    if re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise ValueError("composition resolver returned no valid fingerprint")
    return fingerprint


def credential_status(config: Path) -> dict[str, bool]:
    """Report names and presence only, using the selected enabled routing."""
    required = required_workflow_api_keys(
        config, disabled_roles=frozenset({"data_analysis", "lit_review"})
    )
    return {name: bool(os.environ.get(name, "").strip()) for name in sorted(required)}


def inspect(settings: TutorialExperiment, *, launch: bool) -> TutorialReceipt:
    """Validate before any provider call; previews need neither data nor a GPU."""
    command = build_command(settings)
    # Pin checks intentionally require clean source. Notebook outputs/config edits
    # belong outside the checkout so following the tutorial does not dirty it.
    revision = verify_framework_pin(ROOT, settings.infra_checkout)
    verify_installed_framework(revision, ROOT)
    config = Path(command_value(command, "--llm_config"))
    WorkflowLLMConfig.from_json(str(config))
    key_status = credential_status(config)
    required = tuple(key_status)
    composition = command_value(command, "--task_composition")
    fingerprint = composition_identity(settings, composition)
    data_hashes = None
    gpu = None
    if launch:
        if os.geteuid() == 0:
            raise ValueError("run the teaching demo as a normal user, not root")
        missing = [key for key, present in key_status.items() if not present]
        if missing:
            raise ValueError(
                f"required provider keys are absent: {', '.join(missing)}. "
                "Export them in this launching terminal from a trusted external "
                "secret source; never put values in notebook cells or settings JSON."
            )
        from tutorials.paper.task_view import inspect_task

        task = inspect_task(settings)
        data_hashes = verify_data(settings.data_dir, task.populations())
        gpu = verify_gpu(settings)
    return TutorialReceipt(
        settings=settings,
        infra_revision=revision,
        exp_revision=subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        command=tuple(command),
        required_api_keys=required,
        api_key_status=key_status,
        composition_fingerprint=fingerprint,
        llm_config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        data_sha256=data_hashes,
        gpu=gpu,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    settings = TutorialExperiment.model_validate_json(args.experiment.read_text())
    if settings.composition is None or settings.llm_config is None:
        raise ValueError(
            "select your external task composition and LLM config; initialize a user project first"
        )
    experiment_path = args.experiment.resolve()
    if any(
        not disjoint(experiment_path, repo) for repo in (ROOT, settings.infra_checkout)
    ):
        raise ValueError(
            "save the experiment in your external project, not either checkout"
        )
    if experiment_path.is_relative_to(
        settings.workspace
    ) or experiment_path.is_relative_to(settings.data_dir):
        raise ValueError("save the experiment outside data and the run workspace")
    if args.launch:
        from tutorials.paper.preflight import require_ready

        require_ready(settings, task="tess")
    receipt = inspect(settings, launch=args.launch)
    if not args.launch:
        missing = [
            key for key, present in receipt.api_key_status.items() if not present
        ]
        if missing:
            print(
                "WARNING: missing environment variables: "
                + ", ".join(missing)
                + ". Export keys in the launching terminal; --launch will refuse. "
                "Do not save secrets in notebooks or configuration JSON.",
                file=sys.stderr,
            )
        print(receipt.model_dump_json(indent=2))
        return 0
    # A sibling receipt cannot make the fresh workspace appear nonempty.
    receipt_path = settings.workspace.with_name(
        settings.workspace.name + ".tutorial.json"
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("x") as stream:
        stream.write(receipt.model_dump_json(indent=2))
    print(
        f"Teaching run; no six-hour campaign clock. Receipt: {receipt_path}", flush=True
    )
    # Replace this process so terminal signals reach the native chain normally.
    os.execvpe("bash", receipt.command, child_environment(settings))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f"tutorial refused: {exc}")

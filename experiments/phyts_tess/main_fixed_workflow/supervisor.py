"""Run one PhyTS TESS fixed-workflow unit under its immutable UTC deadline.

Deliberately simpler than the TIDMAD supervisor beside it. That one runs
unattended 24-hour units across four bands on a dedicated machine under
systemd; this runs one 6-hour unit on the local development host. What is
NOT dropped is every hard guarantee, because those are what make two units
comparable rather than merely both finished:

* the clock is written once and a restart continues against the SAME
  deadline (``unit_clock``);
* the chain runs in its own process group and that group is SIGKILLed at the
  deadline, so a hung child cannot outlive the budget;
* a permanent framework halt leaves a marker that survives restarts and is
  never erased to retry an invalid chain;
* provider keys and the GPU are checked BEFORE the clock starts, so a
  missing key costs zero minutes of the budget;
* every transition is appended to ``events.jsonl``, which is the record a
  later reader has instead of this process's memory.

The unit directory holds the clock, the logs, the workspace and the
calibration store. It must be outside both checkouts and outside the data
root: a unit that wrote into a checkout would change the revision it claims
to be running.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from experiments.phyts_tess.main_fixed_workflow.unit_clock import (
    UNIT_SECONDS,
    LaunchRecord,
    create_launch_record,
    read_launch_record,
)
from experiments.shared.fixed_workflow_config import render_siderius_args
from experiments.shared.information_treatment import (
    ModuleState,
    ResolvedInformationTreatment,
    resolve_information_treatment,
)
from experiments.shared.workflow_credentials import required_workflow_api_keys

EXP_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = Path(__file__).resolve().parent
WORKFLOW = EXPERIMENT_DIR / "workflow.json"
AGENTS = EXPERIMENT_DIR / "agents.json"
TREATMENTS = EXP_ROOT / "experiments/phyts_tess/information_treatments"

#: The two arms. Both select the same composition and the same workflow
#: parameters; they differ only in what the agent is told.
ARMS = {
    "no-prior": TREATMENTS / "main-fixed-no-prior.yaml",
    "full": TREATMENTS / "main-fixed-full.yaml",
}

#: The development host's accelerator. Checked by name because an 8 GiB VRAM
#: budget measured on one card says nothing about another.
REQUIRED_GPU_SUBSTRING = "RTX 5090"


#: Treatment MODULE name -> the role name the agent-routing config uses.
#: They are not the same vocabulary: the module is `literature_review` while
#: the routing field is `lit_review`, and passing the module name straight
#: through raises `unknown disabled workflow roles` before the run starts. A
#: module with no entry here has no LLM role to disable and contributes none.
_MODULE_TO_LLM_ROLE = {
    "literature_review": "lit_review",
    "data_analysis": "data_analysis",
}


def _disabled_roles(treatment: ResolvedInformationTreatment) -> frozenset[str]:
    """Routing roles the TREATMENT switched off, so their keys are not demanded.

    Derived from the treatment's own module states rather than from a second
    constant. A hardcoded exclusion would keep excluding Data Analysis after
    an arm enabled it, and the run would then start without the key it needs
    and fail after the clock had already begun.
    """
    return frozenset(
        role
        for module, state in treatment.module_states.items()
        if state is ModuleState.DISABLED
        and (role := _MODULE_TO_LLM_ROLE.get(module)) is not None
    )


def _verify_execution_environment(
    treatment: ResolvedInformationTreatment,
) -> dict[str, object]:
    """Name-only key presence and one expected GPU, BEFORE any clock starts.

    Key VALUES are never read, logged or echoed. Presence is not usable
    provider access — a key can be present and rejected — so this check
    bounds the cheap failure, not the expensive one.
    """
    required = required_workflow_api_keys(
        AGENTS, disabled_roles=_disabled_roles(treatment)
    )
    missing = sorted(name for name in required if not os.environ.get(name))
    if missing:
        raise ValueError(f"required provider keys are absent: {', '.join(missing)}")

    probe = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
        check=True,
        capture_output=True,
        text=True,
    )
    observed = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
    if len(observed) != 1 or REQUIRED_GPU_SUBSTRING not in observed[0]:
        raise ValueError(
            f"this unit expects exactly one {REQUIRED_GPU_SUBSTRING}; observed {observed}"
        )
    return {"required_api_keys": sorted(required), "gpu": observed[0]}


def _append_event(path: Path, event: dict[str, object]) -> None:
    """Append-only, fsynced, never through a symlink."""
    data = (json.dumps(event, sort_keys=True) + "\n").encode()
    descriptor = os.open(
        path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _build_command(
    *,
    checkout: Path,
    unit_dir: Path,
    data_dir: Path,
    run_name: str,
    treatment: ResolvedInformationTreatment,
) -> list[str]:
    """The exact argv this unit will run, rendered once and then stored.

    Three authorities, each rendering only what it owns and none duplicating
    another. ``render_siderius_args`` emits the workflow treatment, including
    ``--task_composition`` and ``--llm_config`` from the config's own fields,
    so neither is repeated here. ``treatment.siderius_args()`` emits the arm
    identity, the module switches and — when the arm enables it — the advice
    path with its declared digest. Only the values genuinely belonging to
    THIS launch, where the run writes and reads and what it is called, are
    added below.
    """
    rendered = render_siderius_args(
        WORKFLOW, repository_root=EXP_ROOT, siderius_checkout=checkout
    )
    return [
        "bash",
        str(checkout / "scripts/launch/run_chain.sh"),
        "--mode",
        "lilab",
        "--workspace",
        str(unit_dir / "workspace"),
        "--data_dir",
        str(data_dir),
        "--run_name",
        run_name,
        "--healthgate_mode",
        "blocking",
        "--result_authority",
        "scientific",
        *treatment.siderius_args(),
        *rendered,
    ]


def _run_chain(record: LaunchRecord, unit_dir: Path) -> int:
    """Start or resume the same chain; kill its process group at the deadline."""
    events = unit_dir / "events.jsonl"
    remaining = record.deadline_epoch - time.time()
    if remaining <= 0:
        _append_event(events, {"event": "deadline_already_elapsed"})
        return 0

    # A permanent framework halt must survive service and operator restarts.
    # Never erase the marker or reset the immutable clock to retry an invalid
    # chain: doing so would silently convert a refusal into a retry budget.
    if (unit_dir / "workspace/.chain_halted").exists():
        _append_event(events, {"event": "chain_halt_preserved"})
        return 3

    command = record.preflight["command"]
    if not isinstance(command, list) or not all(
        isinstance(arg, str) for arg in command
    ):
        raise ValueError("stored fixed-workflow command is malformed")

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    # Clear every ambient plugin overlay before binding this unit's own.
    # Setting SIDERIUS_GENERATED_LIBRARY_DIR alone is NOT enough: the plugin
    # loader also honours SIDERIUS_PLUGIN_DIRS and the legacy
    # AGENT_GENERATED_DIR, so a launching shell that happened to carry either
    # would hand this run another experiment's generated models. Observed
    # concretely — with all of these unset the loader still reached the
    # user-level default library at ~/.siderius/generated_library and
    # registered two models from an unrelated housing run. Binding the unit's
    # own directory displaces that default; unsetting the rest closes the
    # inheritance path a 6-hour run cannot afford to discover late.
    for inherited in (
        "SIDERIUS_PLUGIN_DIRS",
        "AGENT_GENERATED_DIR",
        "SIDERIUS_MODEL_PLUGIN_PATH",
        "SIDERIUS_LOSS_PLUGIN_PATH",
        "SIDERIUS_LOSS_DIRS",
    ):
        environment.pop(inherited, None)
    environment["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(
        unit_dir / "workspace/generated_library"
    )
    # A fresh unit cannot inherit host-wide timing evidence; a resume reuses
    # this same path so its calibration continues rather than restarting.
    environment["SIDERIUS_CALIBRATION_DIR"] = str(unit_dir / "calibration")

    logs = unit_dir / "logs"
    if logs.is_symlink():
        raise ValueError("unit log directory must not be a symlink")
    logs.mkdir(mode=0o700, exist_ok=True)
    _append_event(
        events,
        {
            "event": "chain_start",
            "started_epoch": int(time.time()),
            "deadline_epoch": record.deadline_epoch,
        },
    )

    descriptor = os.open(
        logs / "chain.log",
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "ab", buffering=0) as output:
        process = subprocess.Popen(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            # Its own session, so the deadline can kill the whole tree rather
            # than only the launcher that happens to sit on top of it.
            start_new_session=True,
            env=environment,
        )
        try:
            returncode = process.wait(
                timeout=max(0, record.deadline_epoch - time.time())
            )
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            _append_event(
                events, {"event": "deadline_stop", "ended_epoch": int(time.time())}
            )
            return 0

    _append_event(
        events,
        {
            "event": "chain_exit",
            "ended_epoch": int(time.time()),
            "returncode": returncode,
        },
    )
    if returncode == 3 or (unit_dir / "workspace/.chain_halted").exists():
        return 3
    return 0 if returncode == 0 else 1


def run_unit(
    *,
    checkout: Path,
    data_dir: Path,
    unit_dir: Path,
    run_name: str,
    arm: str,
    launch: bool,
) -> int:
    """Preview or supervise one unit, preserving its first clock."""
    checkout = checkout.resolve()
    data_dir = data_dir.resolve()
    unit_dir = unit_dir.resolve()

    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; choose one of {sorted(ARMS)}")
    # Resolving here certifies the treatment manifest, and its advice digest,
    # BEFORE anything else happens — an arm whose advice file has been edited
    # since it was frozen must refuse rather than run with different bytes.
    treatment = resolve_information_treatment(
        ARMS[arm],
        repository_root=EXP_ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )

    if any(
        unit_dir.is_relative_to(source) or source.is_relative_to(unit_dir)
        for source in (EXP_ROOT, checkout, data_dir)
    ):
        raise ValueError(
            "the unit directory must be separate from both checkouts and the data root"
        )
    expected = (EXP_ROOT / "SIDERIUS_REVISION").read_text(encoding="utf-8").strip()
    actual = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual != expected:
        raise ValueError(
            f"SIDERIUS checkout is at {actual}, this experiment pins {expected}"
        )

    command = _build_command(
        checkout=checkout,
        unit_dir=unit_dir,
        data_dir=data_dir,
        run_name=run_name,
        treatment=treatment,
    )
    if not launch:
        print(f"arm: {arm}  ({ARMS[arm].relative_to(EXP_ROOT)})")
        print("treatment receipt:", json.dumps(treatment.receipt(), sort_keys=True))
        print(f"unit budget: {UNIT_SECONDS} s ({UNIT_SECONDS / 3600:.0f} h)")
        print("command:")
        print("  " + " \\\n    ".join(command))
        return 0

    receipt = _verify_execution_environment(treatment)
    unit_dir.mkdir(parents=True, exist_ok=True)
    clock = unit_dir / "launch.json"
    record = read_launch_record(clock)
    if record is None:
        record = create_launch_record(
            clock,
            {
                "command": command,
                "treatment": treatment.receipt(),
                "siderius_revision": actual,
                **receipt,
            },
            int(time.time()),
        )
        _append_event(
            unit_dir / "events.jsonl",
            {"event": "unit_created", "deadline_utc": record.deadline_utc},
        )
    else:
        _append_event(
            unit_dir / "events.jsonl",
            {"event": "unit_resumed", "deadline_utc": record.deadline_utc},
        )
    return _run_chain(record, unit_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--siderius-checkout", required=True, type=Path)
    parser.add_argument("--data_dir", required=True, type=Path)
    parser.add_argument("--unit_dir", required=True, type=Path)
    parser.add_argument("--run_name", required=True)
    parser.add_argument(
        "--arm",
        required=True,
        choices=sorted(ARMS),
        help="Which information treatment this unit runs under.",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Start or resume the unit. Without it, print the command and exit.",
    )
    args = parser.parse_args(argv)
    return run_unit(
        checkout=args.siderius_checkout,
        data_dir=args.data_dir,
        unit_dir=args.unit_dir,
        run_name=args.run_name,
        arm=args.arm,
        launch=args.launch,
    )


if __name__ == "__main__":
    sys.exit(main())

"""Admit a caller's validation scope against the operator's frozen task.

Per-epoch validation is the one place the caller reaches across the boundary:
it submits a scope, and the evaluator — which owns truth — returns admitted
loss observations. So what arrives has to be checked before it is honoured.

The shape is TIDMAD's
(`experiments/tidmad/main_orchestrator/validation_scope.py`): parse the
captured native command, confirm it selected the operator's manifest by path
and digest, confirm the adapter id, verify every captured file against its
recorded digest, then decode the scope through the task's own deserializer
rather than a second parser.

Three of TIDMAD's checks have no TESS counterpart and are deliberately
absent rather than stubbed: segmentation size (TESS fixes 1024 in its
forward contract), PSD divisibility, and band membership (the data path
refuses `subset_ref` outright, so there is no partition vocabulary to
police).

One check exists here that TIDMAD does not need, and it is checked on VALUES
rather than on types. `deserialize_scope` reconstructs the pack's base scope,
never the refusing subclass the caller's data path builds, so the refusal
does not survive a JSON round trip. What does survive is the absence of a
measurement: a caller-side scope carries identities whose targets are not
finite. One that arrives with finite targets is the evaluator's own scope
round-tripped through the caller, or a forgery, and both are refused.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import cast

from execute_tools.task_data_path import ScopeBuildRequest
from pydantic import BaseModel, ConfigDict, Field

from experiments.phyts_tess.main_orchestrator.public_data_path import (
    PUBLIC_TESS_TASK_ID,
    PublicTessTaskDataPath,
)
from experiments.shared.native_training_inputs import CapturedNativeInputs
from tasks.phyts_tess.runtime.tess_data_path import PhytsTessTaskDataPath, TessScope

__all__ = [
    "AdmittedTessValidationScope",
    "admit_captured_validation_scope",
    "admit_validation_scope",
]

#: The only split a caller may ask to be evaluated on. `train` is its own
#: supervision and the held-out `test` population has no row anywhere in the
#: task's declarations.
EVALUATED_SPLIT = "val"


class AdmittedTessValidationScope(BaseModel):
    """A scope the evaluator has agreed to honour."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    payload: str
    rows: int = Field(gt=0)


def _declared_population(task: PublicTessTaskDataPath) -> set[str]:
    """Every curve the evaluated split contains, through the public API."""
    request = ScopeBuildRequest(
        round_kind="formal", selection_strategy="snapshot", portion=1.0
    )
    return set(cast(TessScope, task.build_eval_scope(request)).keys)


def admit_validation_scope(
    payload: str, *, agent_view: Path, truth_manifest: Path
) -> AdmittedTessValidationScope:
    """Decode through the task's own deserializer, then check what arrived.

    `agent_view` is the operator's copy, not the caller's: the caller's
    request is checked against the population the evaluator believes in.
    The ADMITTED scope is then rebuilt from `truth_manifest`, the evaluator's
    identity manifest, so that its rows carry the targets per-epoch
    validation is computed against. That payload lives on the coordinator's
    side only; the caller's rows carry no target and could not serve.
    """
    task = PublicTessTaskDataPath(agent_view=str(agent_view))
    # `deserialize_scope` reconstructs the pack's base type, never the
    # refusing subclass — the refusal lives on the object the caller's data
    # path builds, and it does not survive a JSON round trip. So the check
    # below is on the VALUES, which do.
    scope = cast(TessScope, task.deserialize_scope(payload))

    if scope.split != EVALUATED_SPLIT:
        raise ValueError(
            f"validation scope names split {scope.split!r}; only "
            f"{EVALUATED_SPLIT!r} may be evaluated"
        )

    submitted = set(scope.keys)
    if not submitted:
        raise ValueError("validation scope names no curves")
    unknown = sorted(submitted - _declared_population(task))
    if unknown:
        raise ValueError(
            "validation scope names curves outside the evaluated population: "
            f"{unknown[:5]}"
        )

    # A caller-side scope carries identities and no measurements. One that
    # arrives with finite targets was not built from the caller's view: it is
    # the evaluator's own scope round-tripped through the caller, or a
    # forgery. Either way the evaluator must not treat it as a request.
    measured = sorted(row.key for row in scope.rows if math.isfinite(row.frot))
    if measured:
        raise ValueError(
            f"validation scope carries targets for {len(measured)} curves "
            f"(first: {measured[:3]}); a caller-side scope must not"
        )

    # Rebuild with truth. Every submitted identity must exist in the
    # evaluator's manifest too: the agent view was derived from it, so a
    # curve the manifest lacks means the two views drifted apart.
    truth = PhytsTessTaskDataPath(manifest_path=str(truth_manifest))
    population = cast(
        TessScope,
        truth.build_eval_scope(
            ScopeBuildRequest(
                round_kind="formal", selection_strategy="snapshot", portion=1.0
            )
        ),
    )
    by_key = {row.key: row for row in population.rows}
    unmeasured = sorted(submitted - set(by_key))
    if unmeasured:
        raise ValueError(
            "evaluator manifest carries no target for curves the agent view "
            f"declares: {unmeasured[:5]}"
        )
    rebuilt = TessScope(
        split=scope.split,
        rows=tuple(by_key[key] for key in scope.keys),
        sequence_length=scope.sequence_length,
    )
    return AdmittedTessValidationScope(
        payload=truth.serialize_scope(rebuilt), rows=len(rebuilt.rows)
    )


def admit_captured_validation_scope(
    captured: CapturedNativeInputs,
    *,
    manifest: Path,
    manifest_sha256: str,
    source_cwd: Path,
    agent_view: Path,
    truth_manifest: Path,
    task_data_path_id: str = PUBLIC_TESS_TASK_ID,
) -> AdmittedTessValidationScope:
    """Bind a captured native invocation to the operator's frozen task.

    Checks selection and bytes — not filesystem ownership, and not who the
    caller is. Only the validation leg is authorized here; the caller's
    choice of training data stays its own.
    """
    from execute_tools.scope_artifact import read_scope_artifact
    from execute_tools.training_cli import build_training_parser

    args = build_training_parser().parse_args(captured.command[2:])

    if args.task_manifest is None:
        raise ValueError("validation invocation omitted the operator task manifest")
    selected = Path(args.task_manifest)
    if not selected.is_absolute():
        selected = source_cwd / selected
    if selected.resolve(strict=True) != manifest.resolve(strict=True):
        raise ValueError("validation invocation selected a different task manifest")
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != manifest_sha256:
        raise ValueError("operator task manifest changed after admission")
    if args.task_data_path_id != task_data_path_id:
        raise ValueError(
            f"validation invocation selected adapter {args.task_data_path_id!r}; "
            f"this deployment publishes {task_data_path_id!r}"
        )

    files = {item.argument: item for item in captured.files}

    def read_captured(name: str) -> bytes:
        item = files.get(name)
        if item is None or getattr(args, name) != str(item.captured):
            raise ValueError(f"validation invocation lacks captured {name}")
        payload = item.captured.read_bytes()
        if hashlib.sha256(payload).hexdigest() != item.sha256:
            raise ValueError(f"captured {name} changed before task admission")
        return payload

    read_captured("task_eval_scope_ref")
    payload = read_scope_artifact(args.task_eval_scope_ref, args.task_eval_scope_digest)
    return admit_validation_scope(
        payload, agent_view=agent_view, truth_manifest=truth_manifest
    )

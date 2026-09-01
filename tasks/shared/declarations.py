"""Small constructors for task-owned model-I/O and metric declarations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from agent.schemas.model_io_contract import (
    AxisRole,
    Dimension,
    DtypeAdmissibility,
    ModelIOContract,
    TensorAxis,
    TensorContract,
)
from execute_tools.evaluation_metric import MetricSpec, ScoreabilityContract


def _all_subclasses(
    cls: type[ScoreabilityContract],
) -> list[type[ScoreabilityContract]]:
    found: list[type[ScoreabilityContract]] = []
    for subclass in cls.__subclasses__():
        found.append(subclass)
        found.extend(_all_subclasses(subclass))
    return found


def scoreability_contract_from_declared(
    payload: dict[str, Any],
) -> ScoreabilityContract:
    """Rebuild the declared concrete scoreability contract or fail closed."""
    contract_id = payload.get("contract_id")
    for contract_type in _all_subclasses(ScoreabilityContract):
        default = contract_type.model_fields["contract_id"].default
        if default == contract_id:
            return contract_type(**payload)
    raise ValueError(
        f"no ScoreabilityContract subclass declares contract_id={contract_id!r}"
    )


def metric_spec_from_declared(payload: dict[str, Any]) -> MetricSpec:
    """Build a metric specification from a task-owned JSON declaration."""
    fields = dict(payload)
    fields["scoreability"] = scoreability_contract_from_declared(fields["scoreability"])
    return MetricSpec(**fields)


def batch_axis(symbol: str = "B") -> TensorAxis:
    return TensorAxis(dimension=Dimension(symbolic=symbol), role=AxisRole.BATCH)


def fixed_axis(extent: int, role: AxisRole | None = None) -> TensorAxis:
    return TensorAxis(dimension=Dimension(fixed=extent), role=role)


def tensor_contract(
    axes: Sequence[TensorAxis], dtypes: Sequence[str]
) -> TensorContract:
    return TensorContract(
        axes=tuple(axes), dtype=DtypeAdmissibility(admissible=tuple(dtypes))
    )


def model_io_contract(inp: TensorContract, out: TensorContract) -> ModelIOContract:
    return ModelIOContract(input=inp, output=out)

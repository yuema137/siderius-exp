"""Typed epoch metadata and aggregate-only replies on a native job channel."""

from typing import Annotated, Literal

from agent.schemas.model_io_contract import ModelIOContract
from execute_tools.validation_execution import (
    CompletedTrainingEpoch,
    ValidationExecutionResult,
)
from ml_models.models_format_sandbox import LossConfig
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    StrictBool,
    StrictInt,
)

from experiments.shared.validation_rng import ValidationRngState


class EpochMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sequence: Annotated[StrictInt, Field(ge=0)]


class ValidationEpochMetadata(EpochMessage):
    model_type: str
    configuration: dict[str, JsonValue]
    completed_training: CompletedTrainingEpoch
    model_io: ModelIOContract | None
    loss: LossConfig
    scope_payload: str
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    batch_size: Annotated[StrictInt, Field(gt=0)]
    expected_rows: Annotated[StrictInt, Field(gt=0)]
    model_training: StrictBool
    objective_training: StrictBool
    rng: ValidationRngState


class ValidationBatchProgress(EpochMessage):
    kind: Literal["progress"] = "progress"
    rows: Annotated[StrictInt, Field(gt=0)]
    elapsed_ms: Annotated[FiniteFloat, Field(gt=0)]


class ValidationContinue(EpochMessage):
    kind: Literal["continue"] = "continue"


class ValidationEpochResult(EpochMessage):
    kind: Literal["result"] = "result"
    result: ValidationExecutionResult


class ValidationEpochRefusal(EpochMessage):
    kind: Literal["refused"] = "refused"
    code: Literal["not_admitted", "validation_failed", "deadline_exhausted"]

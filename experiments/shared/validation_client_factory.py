"""Research-side binding for native parent declarations and child epoch exchange.

The task-specific row declaration is public metadata, not admission authority.
The protected launcher independently verifies scope and row count before private
execution and supplies the inherited channel only to its native training child.
"""

import importlib
from typing import Annotated

from execute_tools.task_data_path import (
    resolve_bound_task_data_path,
    resolve_task_scope_capability,
)
from execute_tools.validation_execution import (
    ValidationCallbacks,
    ValidationExecutionRequest,
    ValidationExecutionResult,
)
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StrictInt

from experiments.shared.inherited_validation_client import (
    InheritedClientSettings,
    InheritedValidationClient,
)


class ValidationClientSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_declaration: str = Field(
        pattern=r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$"
    )
    channel_fd: Annotated[StrictInt, Field(ge=0)] | None = None
    deadline_epoch: FiniteFloat
    max_metadata_bytes: Annotated[StrictInt, Field(ge=1024)]
    max_state_bytes: Annotated[StrictInt, Field(gt=0)]


class NativeValidationClient:
    """Do not touch a child-only descriptor while declaring parent workload."""

    def __init__(self, settings: ValidationClientSettings):
        self.settings = settings
        module, name = settings.row_declaration.split(":")
        self._rows = getattr(importlib.import_module(module), name)
        if not callable(self._rows):
            raise TypeError("task row declaration must be callable")
        self._client: InheritedValidationClient | None = None

    def declared_rows(self, scope: object) -> int:
        rows = self._rows(scope)
        if type(rows) is not int or rows <= 0:
            raise ValueError("task row declaration must return positive integer rows")
        return rows

    @staticmethod
    def _serialize_scope(scope: object) -> str:
        capability = resolve_task_scope_capability(resolve_bound_task_data_path())
        return capability.serialize_scope(scope)

    def observe(
        self,
        request: ValidationExecutionRequest,
        callbacks: ValidationCallbacks,
    ) -> ValidationExecutionResult:
        if self.settings.channel_fd is None:
            raise RuntimeError(
                "private validation requires a launcher-owned child channel"
            )
        if self._client is None:
            self._client = InheritedValidationClient(
                InheritedClientSettings.model_validate(
                    self.settings.model_dump(exclude={"row_declaration"})
                ),
                serialize_scope=self._serialize_scope,
                declare_rows=self.declared_rows,
            )
        return self._client.observe(request, callbacks)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()


def create_validation_client(settings: dict) -> NativeValidationClient:
    """Factory for the existing explicit ValidationDeployment contract."""
    return NativeValidationClient(ValidationClientSettings.model_validate(settings))

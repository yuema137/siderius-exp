"""Parent workload declaration must not open a nonexistent child descriptor."""

import sys
import time
from types import ModuleType

import pytest
from execute_tools.validation_execution import (
    ValidationDeployment,
    bind_validation_deployment,
    bound_validation_rows,
    validation_executor_argv,
)


def test_native_parent_binding_declares_rows_without_child_or_data(monkeypatch):
    module = ModuleType("synthetic_public_rows")
    calls = []

    def declare(scope):
        calls.append(scope)
        return 7

    module.declare = declare
    monkeypatch.setitem(sys.modules, module.__name__, module)
    deployment = ValidationDeployment(
        factory="experiments.shared.validation_client_factory:create_validation_client",
        settings={
            "row_declaration": "synthetic_public_rows:declare",
            "deadline_epoch": time.time() + 10,
            "max_metadata_bytes": 1024,
            "max_state_bytes": 1024,
        },
    )
    scope = object()
    with bind_validation_deployment(deployment) as executor:
        assert bound_validation_rows(scope) == 7
        assert calls == [scope]
        transported = ValidationDeployment.model_validate_json(
            validation_executor_argv()[1]
        )
        assert "channel_fd" not in transported.settings
        with pytest.raises(RuntimeError, match="launcher-owned child channel"):
            executor.observe(None, None)
    assert bound_validation_rows(scope) is None

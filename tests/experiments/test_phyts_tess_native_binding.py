"""What can be checked about the native binding without deploying it.

Execution needs a launcher, its namespaces and a protected runner, none of
which exist for TESS yet — `prepare.py` records that as a launch blocker.
These cases cover what does not need them, and each names a defect that
would otherwise surface only once a deployment was running:

* ``test_the_row_declaration_resolves`` — the validation client is handed a
  ``module:symbol`` STRING. A typo in it imports fine, validates fine and
  fails in the middle of the first epoch of a real run.
* ``test_declared_rows_counts_curves`` — one curve is one row for TESS.
  Borrowing TIDMAD's windows-per-file factor would silently inflate every
  declared workload.
* ``test_declared_rows_refuses_a_foreign_payload`` — the declaration
  re-reads the wire form instead of trusting the object it was handed,
  because a file-loaded plugin's class identity differs from an imported
  one.
* ``test_the_policy_refuses_an_unknown_setting`` — deployment settings
  arrive as a dict. A misspelled key would otherwise be dropped, and the
  deployment would run with a default nobody chose.
"""

from __future__ import annotations

import csv
import importlib
from pathlib import Path

import pytest
from execute_tools.task_data_path import ScopeBuildRequest, bind_task_data_path

from experiments.phyts_tess.main_orchestrator.native_handler import (
    ROW_DECLARATION,
    TessNativePolicy,
)
from experiments.phyts_tess.main_orchestrator.public_data_path import (
    PublicTessTaskDataPath,
)
from experiments.phyts_tess.main_orchestrator.validation_rows import declared_rows

IDENTITY = ("split", "gaia_id", "tic", "sector")


@pytest.fixture
def view(tmp_path) -> Path:
    manifests = tmp_path / "agent" / "manifests"
    manifests.mkdir(parents=True)
    with (manifests / "train.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*IDENTITY, "frot", "frot_err"])
        writer.writeheader()
        writer.writerow(
            {
                "split": "train",
                "gaia_id": "1",
                "tic": "2",
                "sector": "20",
                "frot": "0.5",
                "frot_err": "0.01",
            }
        )
    with (manifests / "predict.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(IDENTITY))
        writer.writeheader()
        for index in range(5):
            writer.writerow(
                {
                    "split": "val",
                    "gaia_id": str(200 + index),
                    "tic": str(800 + index),
                    "sector": "21",
                }
            )
    return manifests.parent


def test_the_row_declaration_resolves():
    """A `module:symbol` string that is wrong fails mid-epoch, not here."""
    module_name, symbol = ROW_DECLARATION.split(":")
    module = importlib.import_module(module_name)
    assert callable(getattr(module, symbol)), (
        f"{ROW_DECLARATION} does not name a callable; the validation client "
        "would fail inside a real run rather than at deployment"
    )


def test_declared_rows_counts_curves(view):
    """One curve is one row. TESS has no windows-per-file factor."""
    task = PublicTessTaskDataPath(agent_view=str(view))
    scope = task.build_eval_scope(
        ScopeBuildRequest(
            round_kind="formal", selection_strategy="snapshot", portion=1.0, seed=0
        )
    )
    with bind_task_data_path(task):
        assert declared_rows(scope) == len(scope.rows) == 5


def test_declared_rows_refuses_a_foreign_payload(view):
    """The declaration re-reads the wire form rather than trusting the object."""
    task = PublicTessTaskDataPath(agent_view=str(view))

    class Foreign:
        """Shaped like a scope, from nothing the task recognises."""

        rows = ("a", "b", "c")

    # Refused by the task's own serializer, which is the authority the
    # declaration routes through rather than an isinstance check here.
    with (
        bind_task_data_path(task),
        pytest.raises(TypeError, match="requires TessScope"),
    ):
        declared_rows(Foreign())


def test_the_policy_refuses_an_unknown_setting():
    """Settings arrive as a dict; a misspelled key must not be dropped."""
    with pytest.raises(Exception) as excinfo:
        TessNativePolicy.model_validate(
            {
                "runtime": {},
                "manifest": "/tmp/manifest.yaml",
                "manifest_sha256": "0" * 64,
                "profile": {},
                "agent_view": "/tmp/agent",
                "truth_manifest": "/tmp/evaluator/rotation_identity.csv",
                "truth_manifest_sha256": "0" * 64,
                "validation_data": "/tmp/data",
                "agent_veiw": "/tmp/typo",
            }
        )
    assert "agent_veiw" in str(excinfo.value)

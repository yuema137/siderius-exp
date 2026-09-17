"""Task-owned metric fixture for Gold Stage-3 qualification tests."""

from functools import lru_cache
from pathlib import Path

from execute_tools.evaluation_metric import MetricSpec
from execute_tools.task_registration_scope import run_registration_scope
from workflows.task_composition import compose_run_task_bindings


@lru_cache(maxsize=1)
def load_declared_tidmad_metric_spec() -> MetricSpec:
    """Load the exact metric bound by the external TIDMAD composition."""
    repository_root = Path(__file__).resolve().parents[4]
    manifest = (
        repository_root
        / "tasks"
        / "tidmad"
        / "compositions"
        / "bounded_qualification.yaml"
    )
    with run_registration_scope():
        return compose_run_task_bindings(str(manifest)).metric.spec

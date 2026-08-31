"""Scientific secondary-metric parity for the three migrated task packages.

SIDERIUS owns how secondary metrics compose and bind. This repository owns
which scientific metrics each real task declares, their directions, and their
manifest order. Each case runs in a fresh subprocess against one explicitly
selected SIDERIUS checkout so task registrations cannot leak between cases.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[1]
TASK_MANIFESTS = {
    "tidmad": EXP_ROOT / "tasks/tidmad/workflows/qualification/composition.yaml",
    "oxford_iiit_pet": EXP_ROOT
    / "tasks/oxford_iiit_pet/compositions/bounded_qualification.yaml",
    "davis_future_prediction": EXP_ROOT
    / "tasks/davis_future_prediction/composition.yaml",
}
EXPECTED = {
    "tidmad": {
        "primary": ["tidmad_denoising_score", "higher"],
        "secondaries": [],
    },
    "oxford_iiit_pet": {
        "primary": ["accuracy", "higher"],
        "secondaries": [["macro_f1", "higher"], ["log_loss", "lower"]],
    },
    "davis_future_prediction": {
        "primary": ["mse", "lower"],
        "secondaries": [["psnr", "higher"], ["mae", "lower"]],
    },
}

CHILD = textwrap.dedent(
    """
    import json
    import os
    import sys
    from pathlib import Path

    checkout = Path(sys.argv[1]).resolve()
    manifest = Path(sys.argv[2]).resolve()
    sys.path.insert(0, str(checkout))
    os.chdir(checkout)

    from workflows import task_composition as composition_module
    from workflows.task_composition import compose_run_task_bindings

    source = Path(composition_module.__file__).resolve()
    if not source.is_relative_to(checkout):
        raise RuntimeError(
            f"source-authority violation: imported {source}, expected checkout {checkout}"
        )

    composition = compose_run_task_bindings(str(manifest))
    declaration_paths = [
        value
        for key, value in composition.provenance.source_paths.items()
        if key.startswith("secondary_metric_declaration")
    ]
    print(
        json.dumps(
            {
                "primary": [composition.metric.spec.id, composition.metric.spec.direction],
                "secondaries": [
                    [metric.spec.id, metric.spec.direction]
                    for metric in composition.secondary_metrics
                ],
                "declaration_paths": declaration_paths,
                "source_checkout": str(checkout),
            },
            sort_keys=True,
        )
    )
    """
)


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        pytest.fail(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    checkout = Path(configured).resolve()
    if not (checkout / "workflows/task_composition.py").is_file():
        pytest.fail(f"SIDERIUS_CHECKOUT is not a SIDERIUS checkout: {checkout}")
    return checkout


@pytest.mark.parametrize("task_id", TASK_MANIFESTS)
def test_real_task_secondary_metric_declarations(task_id: str) -> None:
    """Fail when a migrated task's scientific metric roster or order drifts."""
    checkout = _siderius_checkout()
    completed = subprocess.run(
        [sys.executable, "-c", CHILD, str(checkout), str(TASK_MANIFESTS[task_id])],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout.splitlines()[-1])
    assert receipt["primary"] == EXPECTED[task_id]["primary"]
    assert receipt["secondaries"] == EXPECTED[task_id]["secondaries"]
    assert len(receipt["declaration_paths"]) == len(receipt["secondaries"])
    assert all(Path(path).is_file() for path in receipt["declaration_paths"])
    assert Path(receipt["source_checkout"]) == checkout

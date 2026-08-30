"""External-task regressions for task-owned sampling and Health decoding."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


EXP_ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_pets_health_view_consumes_task_decoded_payload_not_indexed_naming() -> None:
    """Catches the 2026-08-29 external Pets Health naming failure."""
    module = _load(
        EXP_ROOT / "tasks/oxford_iiit_pet/plugins/_pets_health_views.py",
        "siderius_exp_test_pets_health",
    )

    class _Context:
        def load_evaluation_payload(self):
            return {"pet-b": 2, "pet-a": 1}

        def get_denoised_path(self, _index):
            raise AssertionError(
                "a task-owned payload provider must not resolve indexed naming"
            )

    view = module.PetsPredictionViews().materialize(
        "categorical_predictions", _Context()
    )

    np.testing.assert_array_equal(view.payload.symbols, np.array([1, 2]))


def test_davis_health_view_consumes_task_decoded_payload_not_indexed_naming() -> None:
    """Catches the same coupling for a different external artifact layout."""
    module = _load(
        EXP_ROOT / "tasks/davis_future_prediction/plugins/_davis_health_views.py",
        "siderius_exp_test_davis_health",
    )

    class _Context:
        def load_evaluation_payload(self):
            return {"clip-b": np.array([3.0]), "clip-a": np.array([1.0, 2.0])}

        def get_denoised_path(self, _index):
            raise AssertionError(
                "a task-owned payload provider must not resolve indexed naming"
            )

    # Unequal clip shapes are legal evaluation payloads but cannot form one
    # rectangular Health stream, so use equal-shaped values for this boundary
    # witness and leave structural refusal to the provider's dedicated tests.
    context = _Context()
    context.load_evaluation_payload = lambda: {
        "clip-b": np.array([3.0, 4.0]),
        "clip-a": np.array([1.0, 2.0]),
    }
    view = module.DavisSampleViews().materialize("continuous_samples", context)

    np.testing.assert_array_equal(view.payload.samples, np.array([1.0, 2.0, 3.0, 4.0]))

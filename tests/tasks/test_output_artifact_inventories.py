"""Real task codecs enumerate only their own attempt's temporary outputs."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from importlib import import_module
from pathlib import Path
from types import ModuleType

import pytest
from execute_tools.model_output_retention import apply_output_retention

from execute_tools.dataset_config import DatasetProfile
from execute_tools.deliverable_spec import derive_tidmad_deliverable_spec
from execute_tools.task_data_path import EvaluationReadRequest
from execute_tools.task_registration_scope import run_registration_scope


@pytest.fixture
def isolated_task_import() -> Iterator[Callable[[str], ModuleType]]:
    """Task-plugin imports must not persist registrations into other tests."""
    with run_registration_scope():
        yield import_module


def _request(root: Path, *, exp_id: str = "attempt-a") -> EvaluationReadRequest:
    return EvaluationReadRequest(
        deliverable_dir=str(root),
        run_name="run-a",
        exp_id=exp_id,
        model_type="model-a",
    )


@pytest.mark.parametrize(
    ("module_name", "class_name"),
    [
        ("tasks.davis_future_prediction.runtime.davis_data_path", "DavisTaskDataPath"),
        ("tasks.majorana_low_avse.plugins._majorana_task", "MajoranaTaskDataPath"),
        ("tasks.supernemo_signal_background.plugins._supernemo_task", "SuperNemoTaskDataPath"),
    ],
)
def test_single_file_tasks_retire_only_exact_attempt(
    tmp_path: Path,
    module_name: str,
    class_name: str,
    isolated_task_import: Callable[[str], ModuleType],
) -> None:
    module = isolated_task_import(module_name)
    task = getattr(module, class_name)()
    naming = module.deliverable_name
    request = _request(tmp_path)
    own = tmp_path / naming(request)
    neighbor = tmp_path / naming(_request(tmp_path, exp_id="attempt-b"))
    own.write_bytes(b"own")
    neighbor.write_bytes(b"neighbor")

    receipt = apply_output_retention(task=task, request=request, retain_model_outputs=False)

    assert receipt.status == "completed"
    assert [item.relative_path for item in receipt.artifacts] == [own.name]
    assert not own.exists()
    assert neighbor.read_bytes() == b"neighbor"


def test_pets_inventory_includes_probability_sidecar(
    tmp_path: Path, isolated_task_import: Callable[[str], ModuleType]
) -> None:
    module = isolated_task_import("tasks.oxford_iiit_pet.runtime.pets_data_path")
    request = _request(tmp_path)
    own = [
        tmp_path / module.deliverable_name(request),
        tmp_path / module.probabilities_sidecar_name(request),
    ]
    neighbor = tmp_path / module.deliverable_name(_request(tmp_path, exp_id="attempt-b"))
    for path in own:
        path.write_bytes(b"own")
    neighbor.write_bytes(b"neighbor")

    receipt = apply_output_retention(
        task=module.PetsTaskDataPath(), request=request, retain_model_outputs=False
    )

    assert receipt.status == "completed"
    assert {item.relative_path for item in receipt.artifacts} == {path.name for path in own}
    assert all(not path.exists() for path in own)
    assert neighbor.read_bytes() == b"neighbor"


def test_cancer_inventory_includes_partial_nested_arrays(
    tmp_path: Path, isolated_task_import: Callable[[str], ModuleType]
) -> None:
    module = isolated_task_import("tasks.cancer_gene_identification.plugins._cancer_gene_task")
    request = _request(tmp_path)
    manifest = tmp_path / module.deliverable_name(request)
    partial = tmp_path / manifest.stem / "mtg" / "predictions.npy"
    partial.parent.mkdir(parents=True)
    partial.write_bytes(b"partial")
    neighbor = tmp_path / module.deliverable_name(_request(tmp_path, exp_id="attempt-b"))
    neighbor.write_bytes(b"neighbor")

    receipt = apply_output_retention(
        task=module.CancerGeneTaskDataPath(), request=request, retain_model_outputs=False
    )

    assert receipt.status == "completed"
    assert [item.relative_path for item in receipt.artifacts] == [
        str(partial.relative_to(tmp_path))
    ]
    assert not partial.exists()
    assert neighbor.read_bytes() == b"neighbor"


def test_tidmad_inventory_reuses_exact_scoring_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    isolated_task_import: Callable[[str], ModuleType],
) -> None:
    tidmad_module = isolated_task_import("tasks.tidmad.runtime.tidmad_data_path")
    profile_path = (
        Path(__file__).resolve().parents[2]
        / "tasks"
        / "tidmad"
        / "resolved"
        / "dataset_profile.json"
    )
    profile = DatasetProfile.model_validate_json(profile_path.read_text())
    monkeypatch.setattr(tidmad_module, "resolve_dataset_profile", lambda: profile)
    naming = derive_tidmad_deliverable_spec(profile).naming
    request = _request(tmp_path)
    own = tmp_path / naming.name(
        model_type=request.model_type,
        run_name=request.run_name,
        exp_id=request.exp_id,
        input_identity=4,
    )
    neighbor = tmp_path / naming.name(
        model_type=request.model_type,
        run_name=request.run_name,
        exp_id="attempt-b",
        input_identity=4,
    )
    own.write_bytes(b"own")
    neighbor.write_bytes(b"neighbor")

    receipt = apply_output_retention(
        task=tidmad_module.TidmadTaskDataPath(),
        request=request,
        retain_model_outputs=False,
    )

    assert receipt.status == "completed"
    assert [item.relative_path for item in receipt.artifacts] == [own.name]
    assert not own.exists()
    assert neighbor.read_bytes() == b"neighbor"

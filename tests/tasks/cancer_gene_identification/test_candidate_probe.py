"""Strict graph models must be checked with legal task-owned packed records."""

from pathlib import Path

import pytest
import torch
from agent.schemas.model_probe import ModelProbeRequest
from agent.skills.task_model_probe import task_model_probe_cases
from agent.skills.validator_probe_worker import run_bounded_probe
from execute_tools.task_registration_scope import run_registration_scope
from nodes.ml_code_validator_agent.ml_code_validator_agent import (
    _check_instantiation_and_gradient,
    _run_tests,
)
from nodes.ml_model_implementor.ml_model_implementor import (
    _assemble_test,
    _smoke_test_plugin,
)
from workflows.task_composition import (
    build_task_composition_ref,
    compose_run_task_bindings,
)

PACK = Path(__file__).resolve().parents[3] / "tasks/cancer_gene_identification"


@pytest.fixture
def composition():
    with run_registration_scope():
        yield compose_run_task_bindings(str(PACK / "compositions/cpdb_tutorial.yaml"))


@pytest.mark.parametrize("records", [1, 2, 3, 7, 64, 65])
def test_fixture_obeys_graph_contract_without_dataset(composition, records):
    request = ModelProbeRequest(
        model_io_contract=composition.forward_contract.model_io,
        input_shape=(1, records, 68),
        dtype="float32",
    )
    task = composition.task_data_path
    packed = task.model_validation_input(request)
    assert torch.equal(packed, task.model_validation_input(request))
    assert packed.shape == (1, records, 68)
    assert packed.dtype == torch.float32 and packed.device.type == "cpu"
    assert torch.isfinite(packed).all()
    graph = packed[0]
    marker = graph[:, 0]
    assert torch.all((marker == 0) | (marker == 1))
    nodes = int(marker.sum())
    assert (
        nodes >= 1 and torch.all(marker[:nodes] == 1) and torch.all(marker[nodes:] == 0)
    )
    assert torch.equal(graph[:nodes, 1], torch.arange(nodes).float())
    assert torch.all(graph[:nodes, 2] == 0)
    mask = graph[:, 3]
    assert torch.all((mask == 0) | (mask == 1)) and mask[:nodes].sum() >= 1
    assert torch.all(graph[nodes:, 3:] == 0)
    edges = graph[nodes:, 1:3]
    assert torch.equal(edges, edges.round())
    assert torch.all((edges >= 0) & (edges < nodes))
    assert torch.all(edges[:, 0] != edges[:, 1])
    assert len(torch.unique(edges, dim=0)) == len(edges)


STRICT_GRAPH_MODEL = """import torch
from torch import nn
from pydantic import BaseModel
PLUGIN_MODEL_TYPE = "strict_graph_probe"
PLUGIN_OUTPUT_TYPE = "regressor"
class Config(BaseModel):
    segmentation_size: int = 64
class Model(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.head = nn.Linear(64, 1)
    def forward(self, x):
        if x.shape[0] != 1:
            raise ValueError("one graph per batch")
        rows = x[0]
        marker = rows[:, 0]
        if not torch.all((marker == 0) | (marker == 1)):
            raise ValueError("invalid node markers")
        n = int(marker.sum())
        if n < 1 or not torch.all(marker[:n] == 1) or not torch.all(marker[n:] == 0):
            raise ValueError("nodes must form the leading segment")
        if not torch.equal(rows[:n, 1], torch.arange(n).float()):
            raise ValueError("invalid node identifiers")
        endpoints = rows[n:, 1:3]
        if not torch.equal(endpoints, endpoints.round()) or not torch.all((endpoints >= 0) & (endpoints < n)):
            raise ValueError("edge endpoints must identify existing nodes")
        logits = self.head(x[..., 4:]).squeeze(-1)
        return torch.stack([x[..., 0], x[..., 3], logits], dim=-1)
PLUGIN_CONFIG_CLASS = Config
PLUGIN_MODEL_CLASS = Model
"""


def test_strict_graph_passes_all_native_consumers(composition, tmp_path):
    contract = composition.forward_contract.model_io
    context = build_task_composition_ref(composition).model_probe_context
    assert context is not None
    assert [
        case.input.shape[0]
        for case in task_model_probe_cases(context, contract, "regressor")
    ] == [1]
    assert (
        _smoke_test_plugin(STRICT_GRAPH_MODEL, "strict_graph_probe", contract)
        is not None
    )
    assert (
        _smoke_test_plugin(
            STRICT_GRAPH_MODEL,
            "strict_graph_probe",
            contract,
            model_probe_context=context,
        )
        is None
    )
    models = tmp_path / "models"
    models.mkdir()
    path = models / "strict_graph_probe.py"
    path.write_text(STRICT_GRAPH_MODEL)
    assert all(
        _check_instantiation_and_gradient(
            str(path), contract, model_probe_context=context
        )[:3]
    )
    assert all(run_bounded_probe(str(path), contract, model_probe_context=context)[:3])
    tests = tmp_path / "tests"
    tests.mkdir()
    test_file = tests / "test_model.py"
    test_file.write_text(
        _assemble_test("strict_graph_probe", contract, model_probe_context=context)
    )
    passed, output = _run_tests(str(test_file), context)
    assert passed, output

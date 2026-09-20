"""Research-side export to the serialized-model format used by CLI evaluators.

This module executes model code. Invoke it inside the research worker's resource
and filesystem boundary, never as a privileged evaluator. It does not load task
data, construct native models, choose examples, or decide scientific eligibility.
"""

import copy
import io
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import torch
from pydantic import BaseModel, ConfigDict

from experiments.shared.checksum_manifest import sha256_file


class ScriptedExportReceipt(BaseModel):
    """Evidence for serialization only; no claim of score or scientific validity."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    model_sha256: str
    weights_sha256: str
    example_count: int
    serialization_method: Literal["script", "trace"] = "script"
    format: str = "torchscript-with-matching-state-dict-v1"
    execution_devices: tuple[str, ...] = ()


def _check_state(expected: dict[str, torch.Tensor], model: torch.nn.Module) -> None:
    actual = model.state_dict()
    if actual.keys() != expected.keys():
        raise ValueError("scripted export changed state_dict keys")
    for name, tensor in expected.items():
        other = actual[name]
        if (
            other.shape != tensor.shape
            or other.dtype != tensor.dtype
            or not torch.equal(other.cpu(), tensor)
        ):
            raise ValueError(f"scripted export changed parameter or buffer: {name}")


def _serialize(model, examples, method):
    if method == "script":
        try:
            return torch.jit.script(model)
        except Exception as error:
            raise ValueError(
                "model cannot be scripted for the evaluator; no trace fallback was used"
            ) from error
    if method != "trace":
        raise ValueError("serialization method must be script or trace")
    if len(examples) < 2:
        raise ValueError("explicit tracing needs at least two comparison examples")
    try:
        return torch.jit.trace(
            model,
            example_inputs=examples[0],
            check_inputs=list(examples[1:]),
            check_trace=True,
            strict=True,
        )
    except Exception as error:
        raise ValueError("explicit trace qualification failed") from error


def _check_execution_devices(model, scripted, examples, devices, snapshot) -> None:
    """Exercise the evaluator's CPU-load then device-move on isolated copies."""
    if not devices:
        return
    serialized = io.BytesIO()
    torch.jit.save(scripted, serialized)
    for device in devices:
        device = torch.device(device)
        try:
            eager = copy.deepcopy(model).eval().to(device)
            serialized.seek(0)
            restored = torch.jit.load(serialized, map_location="cpu").eval().to(device)
            with torch.inference_mode():
                for args in examples:
                    inputs = tuple(value.to(device) for value in args)
                    torch.testing.assert_close(
                        restored(*inputs), eager(*inputs), rtol=1e-5, atol=1e-6
                    )
                    _check_state(snapshot, restored)
                    _check_state(snapshot, eager)
        except Exception as error:
            raise ValueError(
                f"scripted model fails evaluator CPU-load/device-move on {device}: "
                f"{str(error)[-2000:]}"
            ) from error


def qualify_scripted_model(
    model: torch.nn.Module,
    examples: Sequence[tuple[torch.Tensor, ...]],
    *,
    method: Literal["script", "trace"] = "script",
    execution_devices: Sequence[torch.device | str] = (),
) -> torch.jit.ScriptModule:
    """Check scripting, example-output parity and absence of state mutation.

    Call before training to reject unsupported implementations cheaply, and
    again on restored trained weights before export. Examples are explicit
    caller inputs; their coverage is not inferred from a successful check.
    """
    if not examples:
        raise ValueError("scripted export requires explicit comparison examples")
    if any(module.training for module in model.modules()):
        raise ValueError("scripted export requires an evaluation-mode model")
    state = model.state_dict()
    if not state or any(not isinstance(x, torch.Tensor) for x in state.values()):
        raise ValueError("scripted export requires a nonempty tensor state_dict")
    if any(x.device.type != "cpu" for x in state.values()):
        raise ValueError("scripted export requires an explicit CPU model copy")
    snapshot = {name: value.detach().clone() for name, value in state.items()}
    scripted = _serialize(model, examples, method)
    _check_state(snapshot, model)
    _check_state(snapshot, scripted)
    with torch.inference_mode():
        for args in examples:
            expected = model(*args)
            actual = scripted(*args)
            try:
                torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)
            except AssertionError as error:
                raise ValueError(
                    "scripted output differs from native output"
                ) from error
            _check_state(snapshot, model)
            _check_state(snapshot, scripted)
    _check_execution_devices(model, scripted, examples, execution_devices, snapshot)
    return scripted


def export_scripted_model(
    model: torch.nn.Module,
    *,
    examples: Sequence[tuple[torch.Tensor, ...]],
    destination: Path,
    method: Literal["script", "trace"] = "script",
    execution_devices: Sequence[torch.device | str] = (),
) -> ScriptedExportReceipt:
    """Write a fresh model/weights pair and verify its serialized round trip.

    The caller owns native-artifact reconstruction and certification. A complete
    candidate still needs its task-specific metadata/source and evaluator replay.
    Existing destinations are never overwritten; failures remove only the new
    directory created by this call. No files are written before qualification.
    """
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    scripted = qualify_scripted_model(
        model, examples, method=method, execution_devices=execution_devices
    )
    expected = {k: v.detach().clone() for k, v in model.state_dict().items()}
    destination.mkdir(mode=0o700)
    try:
        model_path, weights_path = destination / "model.pt", destination / "weights.pth"
        torch.jit.save(scripted, str(model_path))
        torch.save(expected, weights_path)
        restored = torch.jit.load(str(model_path), map_location="cpu").eval()
        _check_state(expected, restored)
        with torch.inference_mode():
            for args in examples:
                torch.testing.assert_close(
                    restored(*args), model(*args), rtol=1e-5, atol=1e-6
                )
                _check_state(expected, restored)
                _check_state(expected, model)
        receipt = ScriptedExportReceipt(
            model_sha256=sha256_file(model_path),
            weights_sha256=sha256_file(weights_path),
            example_count=len(examples),
            serialization_method=method,
            execution_devices=tuple(
                str(torch.device(device)) for device in execution_devices
            ),
        )
        (destination / "export_receipt.json").write_text(
            receipt.model_dump_json(indent=2) + "\n"
        )
        return receipt
    except BaseException:
        shutil.rmtree(destination)
        raise

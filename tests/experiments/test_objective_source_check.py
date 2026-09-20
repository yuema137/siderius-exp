"""Obvious loss side effects are refused without executing submitted code."""

import pytest

from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial
from experiments.shared.objective_source_check import inspect_objective_source


def check(source):
    material = ObjectiveReviewMaterial(
        sources={"loss.py": source},
        effective_parameters={},
        dependency_declaration="fixture",
    )
    result = inspect_objective_source(
        material, allowed_import_roots=frozenset({"torch", "math", "pydantic"})
    )
    assert result.material_sha256 == material.sha256
    return result


@pytest.mark.parametrize(
    "source",
    [
        "import os as harmless\nharmless.system('x')",
        "import torch as t\nf = t.save\nf(target, 'x')",
        "from torch import load as harmless\nharmless('x')",
        "print(target)",
        "eval('payload')",
        "getattr(torch, 'sa'+'ve')",
        "torch.__dict__['save'](target,'x')",
        "from torch import *",
        "from .hidden import run",
        "def bad(:",
    ],
)
def test_known_side_effect_paths_fail(source):
    result = check(source)
    assert not result.passed
    assert all(
        finding.reason and finding.file == "loss.py" for finding in result.findings
    )


def test_normal_robust_and_spectral_arithmetic_passes():
    assert check("""import torch
class Loss(torch.nn.Module):
    def __init__(self):
        super().__init__()
    def forward(self, prediction, target):
        time = torch.nn.functional.smooth_l1_loss(prediction, target)
        spectrum = (torch.fft.rfft(prediction)-torch.fft.rfft(target)).abs().mean()
        return time + spectrum
""").passed


def test_clean_source_check_does_not_claim_semantic_safety():
    # The actual purpose-review stage rejects this; syntax checking is insufficient.
    assert check("def loss(p,t): return ((p-t)**2).mean()+t.mean()").passed


def test_source_is_never_executed(tmp_path):
    marker = tmp_path / "must-not-exist"
    assert not check(f"open({str(marker)!r}, 'w').write('executed')").passed
    assert not marker.exists()

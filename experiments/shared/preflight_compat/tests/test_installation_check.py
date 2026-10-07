"""Normal merge ancestry must not invalidate byte-identical qualified code."""

import json
from pathlib import Path

import pytest

registry = pytest.importorskip("core.preflight_estimation")

from siderius_preflight_compat import historical_profile

from experiments.shared.preflight_compat import check_installation


@pytest.fixture
def checkout():
    root = Path(registry.__file__).resolve().parents[2]
    if not (root / ".git").exists():
        pytest.skip(
            "Installation verification requires the candidate checkout's own environment"
        )
    return root


def test_merge_revision_reuses_qualified_source_without_changing_plugin_identity(
    monkeypatch, checkout
):
    before = historical_profile().identity()
    original = check_installation.subprocess.check_output
    successor = "f" * 40

    def output(command, **kwargs):
        if command[-2:] == ["rev-parse", "HEAD"]:
            return successor + "\n"
        return original(command, **kwargs)

    monkeypatch.setattr(check_installation.subprocess, "check_output", output)
    receipt = check_installation.check(checkout)
    assert receipt["infra_revision"] == successor
    assert successor not in receipt["qualified_reference_revisions"]
    assert receipt["selected_checkout_assembly_match"] is True
    assert receipt["child_identity_match"] is True
    assert historical_profile().identity() == before


@pytest.mark.parametrize("changed", ["assembly", "registry"])
def test_checker_rejects_different_selected_environment(monkeypatch, changed, checkout):
    original = check_installation.subprocess.check_output

    def output(command, **kwargs):
        result = original(command, **kwargs)
        if len(command) == 3 and "'registry':" in command[-1]:
            payload = json.loads(result)
            payload[changed] = (
                "0" * 64 if changed == "assembly" else "/different/registry.py"
            )
            return json.dumps(payload)
        return result

    monkeypatch.setattr(check_installation.subprocess, "check_output", output)
    with pytest.raises(
        ValueError, match="another source installation|assembly differs"
    ):
        check_installation.check(checkout)

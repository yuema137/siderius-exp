"""A v2 qualification must not silently grant the v1 selector new behavior."""

import json
from pathlib import Path

import pytest
import siderius_prompt_compat as installed
from agent.prompt_rendering import resolve_prompt_profile


@pytest.mark.parametrize(
    "prefix",
    [
        "paper-early",
        "paper-late",
        "paper-tidmad-noprior",
        "paper-analysis-c0467447",
    ],
)
def test_versioned_entry_points_keep_assembly_qualification_separate(
    monkeypatch, prefix
):
    root = Path(installed.__file__).parent
    old = json.loads((root / "qualification.json").read_text())["assembly_sha256"]
    new = json.loads((root / "qualification-v2.json").read_text())["assembly_sha256"]
    monkeypatch.setattr(installed, "rendering_assembly_digest", lambda: old)
    historical = resolve_prompt_profile(f"{prefix}-v1")
    assert "proposal.time_budget_context" not in historical.renderers
    with pytest.raises(ValueError, match="not been qualified"):
        resolve_prompt_profile(f"{prefix}-v2")
    monkeypatch.setattr(installed, "rendering_assembly_digest", lambda: new)
    current = resolve_prompt_profile(f"{prefix}-v2")
    assert current.version == "2"
    assert "proposal.time_budget_context" in current.renderers
    assert "proposal.template" in current.renderers
    with pytest.raises(ValueError, match="not been qualified"):
        resolve_prompt_profile(f"{prefix}-v1")
    monkeypatch.setattr(installed, "rendering_assembly_digest", lambda: "0" * 64)
    for version in (1, 2):
        with pytest.raises(ValueError, match="not been qualified"):
            resolve_prompt_profile(f"{prefix}-v{version}")

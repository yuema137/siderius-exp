"""Historical profiles suppress one new boundary without changing existing requests."""

import json
from pathlib import Path

import pytest
import siderius_prompt_compat as installed


@pytest.mark.parametrize(
    "factory",
    [
        installed.early,
        installed.late,
        installed.tidmad_noprior,
        installed.analysis,
        installed.early_v2,
        installed.late_v2,
        installed.tidmad_noprior_v2,
        installed.analysis_v2,
    ],
)
def test_historical_disclosure_is_explicit_and_does_not_mutate_context(
    monkeypatch, factory
):
    root = Path(installed.__file__).parent
    filename = (
        "qualification-v2.json"
        if factory.__name__.endswith("_v2")
        else "qualification.json"
    )
    digest = json.loads((root / filename).read_text())["assembly_sha256"]
    monkeypatch.setattr(installed, "rendering_assembly_digest", lambda: digest)
    profile = factory()
    context = {"constraints": ["unchanged nested evidence"]}
    original = json.dumps(context, sort_keys=True)
    with pytest.raises(ValueError, match="disclose_execution_constraints=False"):
        profile.renderers["constraints.disclosure"](context)
    with pytest.raises(ValueError, match="new workspace"):
        profile.renderers["constraints.disclosure"]({})
    assert profile.renderers["constraints.disclosure"](None) == ""
    assert json.dumps(context, sort_keys=True) == original
    assert "proposal.template" in profile.renderers
    assert (
        "proposal.time_budget_context" in profile.renderers
    ) == factory.__name__.endswith("_v2")
    monkeypatch.setattr(installed, "rendering_assembly_digest", lambda: "0" * 64)
    with pytest.raises(ValueError, match="not been qualified"):
        factory()


def test_historical_analysis_refuses_populated_context_before_rendering():
    from types import SimpleNamespace

    context = {"workflow_rules": {"train_config.epochs": {"exact": 7}}}
    inp = SimpleNamespace(constraint_context=context)
    original = json.dumps(context, sort_keys=True)

    def renderer(**kwargs):
        pytest.fail(
            "A conflicting analysis input must fail before historical rendering"
        )

    with pytest.raises(ValueError, match="disclose_execution_constraints=False"):
        installed._analysis_view(renderer)(analysis_input=inp)
    assert json.dumps(context, sort_keys=True) == original

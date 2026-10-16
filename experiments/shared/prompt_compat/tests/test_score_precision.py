"""Historical profiles preserve score text without changing native precision."""

import pytest
from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
from agent.prompt_templates.interpretation.rendering import format_interpretation_score


@pytest.mark.parametrize(
    "name",
    [
        "paper-early-v2",
        "paper-late-v2",
        "paper-tidmad-noprior-v2",
        "paper-analysis-c0467447-v2",
    ],
)
@pytest.mark.parametrize(
    "score, old",
    [
        (0.0000123456789012345, "0.0000"),
        (-0.0000123456789012345, "-0.0000"),
        (None, "skipped"),
        (0.0, "0.0000"),
    ],
)
def test_explicit_profile_preserves_old_expression_without_leaking(name, score, old):
    native = "skipped" if score is None else repr(score)
    assert format_interpretation_score(score) == native
    with bind_prompt_profile(resolve_prompt_profile(name)):
        assert format_interpretation_score(score) == old
    assert format_interpretation_score(score) == native

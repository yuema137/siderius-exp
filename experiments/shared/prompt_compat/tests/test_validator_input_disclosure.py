"""Historical omission is explicit and preserves the live typed input contract."""

import pytest
from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
from agent.schemas.model_io_contract import ModelIOContract


@pytest.mark.parametrize(
    "profile",
    [
        "paper-early-v2",
        "paper-late-v2",
        "paper-tidmad-noprior-v2",
        "paper-analysis-c0467447-v2",
    ],
)
@pytest.mark.parametrize("applicability", [None, "temporal", "not_applicable"])
def test_historical_input_omission_does_not_mutate_declared_facts(
    profile, applicability
):
    renderer = pytest.importorskip("nodes.ml_code_validator_agent.input_contract")
    contract = ModelIOContract.model_validate(
        {
            "input": {
                "axes": [
                    {"role": "batch", "dimension": {"symbolic": "B"}},
                    {"dimension": {"fixed": 1}},
                    {"dimension": {"fixed": 1024}},
                ],
                "dtype": {"admissible": ["float32", "float64"]},
            },
            "output": {
                "axes": [
                    {"role": "batch", "dimension": {"symbolic": "B"}},
                    {"dimension": {"fixed": 1}},
                ],
                "dtype": {"admissible": ["float32"]},
            },
        }
    )
    before = contract.model_dump_json()
    native = renderer.render_input_contract(contract, applicability)
    assert "Declared input shape: [B, 1, 1024]" in native
    with bind_prompt_profile(resolve_prompt_profile(profile)):
        assert renderer.render_input_contract(contract, applicability) == ""
    assert contract.model_dump_json() == before
    assert renderer.render_input_contract(contract, applicability) == native

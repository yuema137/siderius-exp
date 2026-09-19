"""A Full-only provider must be required; NoPrior must not demand its key."""

import json
from pathlib import Path

import pytest

from experiments.shared.workflow_credentials import required_workflow_api_keys
from experiments.tidmad.main_fixed_workflow.supervisor import _required_api_keys


def test_analysis_only_provider_is_required_for_full_but_excluded_for_no_prior(
    tmp_path,
):
    source = (
        Path(__file__).resolve().parents[2]
        / "experiments/tidmad/main_fixed_workflow/iclr_official_v1.json"
    )
    payload = json.loads(source.read_text())
    payload["data_analysis"]["provider"] = "gemini"
    payload["data_analysis"]["model_id"] = "test-only"
    payload["data_analysis"].pop("reasoning_effort", None)
    config = tmp_path / "models.json"
    config.write_text(json.dumps(payload))
    assert required_workflow_api_keys(config) == {"OPENAI_API_KEY", "GEMINI_API_KEY"}
    assert _required_api_keys(config) == {"OPENAI_API_KEY"}
    with pytest.raises(ValueError, match="unknown disabled workflow roles"):
        required_workflow_api_keys(config, disabled_roles=frozenset({"data_analyis"}))

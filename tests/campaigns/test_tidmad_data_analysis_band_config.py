"""The experiment-owned raw-data characterization covers the declared full band."""

from pathlib import Path

import yaml
from agent.schemas.data_analysis.assets import LegacyPartitionScope
from workflows.data_analysis_composition import DataAnalysisWorkflowConfig

ROOT = Path(__file__).resolve().parents[2]
TREATMENT = ROOT / "campaigns/tidmad_data_analysis/task_composition_raw_characterization.yaml"


def test_data_analysis_treatment_is_experiment_owned_and_covers_full_band() -> None:
    manifest = yaml.safe_load(TREATMENT.read_text(encoding="utf-8"))
    assert manifest["data_analysis"] == {
        "enabled": True,
        "config": "data_analysis_high_band_raw.yaml",
    }
    config_path = TREATMENT.parent / manifest["data_analysis"]["config"]
    config = DataAnalysisWorkflowConfig.model_validate(
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
    )
    assert len(config.available_assets) == 1
    asset = config.available_assets[0]
    assert isinstance(asset.authorized_scope, LegacyPartitionScope)
    assert asset.authorized_scope.data_scope.file_indices == [15, 16, 17, 18, 19]
    assert config.resource_envelope.sampling_policy.max_items >= 5

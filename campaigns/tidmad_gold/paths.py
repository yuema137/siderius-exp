"""Path authorities for the external TIDMAD Gold campaign package."""

from pathlib import Path


CAMPAIGN_ROOT = Path(__file__).resolve().parent
EXPERIMENT_ROOT = CAMPAIGN_ROOT.parents[1]
TIDMAD_TASK_ROOT = EXPERIMENT_ROOT / "tasks" / "tidmad"
REFERENCE_DATA_ROOT = TIDMAD_TASK_ROOT / "reference_data"
RESOLVED_TASK_ROOT = TIDMAD_TASK_ROOT / "resolved"
ANCHOR_MAP_PATH = REFERENCE_DATA_ROOT / "segment_anchors.json"
DATASET_PROFILE_PATH = RESOLVED_TASK_ROOT / "dataset_profile.json"
DELIVERABLE_SPEC_PATH = RESOLVED_TASK_ROOT / "deliverable_spec.json"
GOLD_HEALTH_CONFIG_PATH = CAMPAIGN_ROOT / "task" / "health_checks_effective_gold.yaml"
GOLD_TASK_HEALTH_CONFIG_PATH = CAMPAIGN_ROOT / "task" / "task_health_regression.yaml"
GOLD_STAGE3_TASK_COMPOSITION_PATH = CAMPAIGN_ROOT / "task" / "task_composition_stage3.yaml"

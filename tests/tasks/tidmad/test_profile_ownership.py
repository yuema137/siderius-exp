"""Task-owned TIDMAD topology contract independent of framework defaults."""

import json
from pathlib import Path

from execute_tools.dataset_config import DatasetProfile
from tasks.tidmad.runtime.profile import tidmad_topology

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"


def test_resolved_profile_drives_the_task_owned_topology() -> None:
    """Catches task tools falling back to a framework-shipped TIDMAD profile."""
    raw = json.loads((TASK_ROOT / "resolved" / "dataset_profile.json").read_text())
    profile = DatasetProfile.model_validate(raw)

    topology = tidmad_topology(profile)

    assert topology.dataset.psd_segment_length == 10_000_000
    assert topology.dataset.segments_per_file == 200
    assert topology.dataset.num_files == 20
    assert topology.dataset.training_file_name(3) == "abra_training_0003.h5"
    assert topology.dataset.validation_file_name(17) == "abra_validation_0017.h5"
    assert topology.channels.model_dump() == {
        "input_channel": "channel0001",
        "target_channel": "channel0002",
    }
    assert topology.encoding.model_dump() == {
        "storage_dtype": "int8",
        "compute_dtype": "int16",
        "value_offset": 128,
        "num_classes": 256,
    }
    assert 40_000 in topology.dataset.valid_segmentation_sizes()


def test_profile_without_tidmad_sections_refuses() -> None:
    """Catches a task-owned decoder inventing TIDMAD topology for another task."""
    profile = DatasetProfile(
        partition_count=1,
        topology={},
        anchor_selection_files=[0],
        health_peek_files=[0],
    )

    try:
        tidmad_topology(profile)
    except ValueError as exc:
        assert "missing ['dataset', 'channels', 'encoding']" in str(exc)
    else:
        raise AssertionError("a profile without TIDMAD topology was accepted")

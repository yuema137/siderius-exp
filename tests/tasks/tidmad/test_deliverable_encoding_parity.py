"""Step-05c C0/C4/C5 logical-artifact witnesses, owned by the external task.

The historical instrument attributes and byte-boundary samples are literals,
not regenerated goldens. HDF5 allocation details are deliberately not compared.
"""

from contextvars import Context
from pathlib import Path

import h5py
import numpy as np
import pytest
from execute_tools.dataset_config import (
    DatasetProfile,
    DatasetProfileBindingError,
    bind_dataset_profile,
)
from execute_tools.task_data_path import (
    DeliverableSourceContext,
    DeliverableWriteRequest,
)

from tasks.tidmad.runtime import tidmad_data_path as codec

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"
INPUT = [-128, -1, 0, 1, 127, -128, 63, -64]
TARGET = [127, 1, 0, -1, -128, 127, -64, 63]
ATTRS = {
    "file_first_sample_index": 100000000000000,
    "input_coupling": 0,
    "input_impedance_ohm": 50,
    "sampling_frequency": 10000000,
    "voltage_range_mV": 80,
}


@pytest.fixture
def profile():
    return DatasetProfile.model_validate_json(
        (TASK_ROOT / "resolved" / "dataset_profile.json").read_text()
    )


def _inspect(path):
    groups, datasets, attrs = [], {}, {}
    with h5py.File(path, "r") as handle:
        assert dict(handle.attrs) == {}

        def visit(name, node):
            if isinstance(node, h5py.Group):
                groups.append(name)
                if node.attrs:
                    attrs[name] = {
                        key: node.attrs[key].item() for key in sorted(node.attrs)
                    }
            else:
                datasets[name] = {
                    "dtype": str(node.dtype),
                    "shape": tuple(node.shape),
                    "values": node[:].tolist(),
                }
                assert dict(node.attrs) == {}

        handle.visititems(visit)
    return {"groups": sorted(groups), "datasets": datasets, "attrs": attrs}


def _expected(
    channels=("channel0001", "channel0002"), dtype="int8", values=(INPUT, TARGET)
):
    paths = [f"timeseries/{channel}" for channel in channels]
    return {
        "groups": ["timeseries", *paths],
        "datasets": {
            f"{path}/timeseries": {"dtype": dtype, "shape": (8,), "values": samples}
            for path, samples in zip(paths, values, strict=True)
        },
        "attrs": {path: ATTRS for path in paths},
    }


@pytest.mark.parametrize("bind_profile", [False, True])
def test_full_logical_artifact_matches_the_pre05c_capture(
    tmp_path, profile, bind_profile
):
    output = tmp_path / "deliverable.h5"
    storage = codec.derive_tidmad_deliverable_spec(profile).storage
    assert storage.value_offset == 128 and storage.storage_dtype == "int8"
    if bind_profile:
        with bind_dataset_profile(profile):
            codec.create_abra_file(
                str(output),
                np.array(INPUT, dtype=np.int8),
                np.array(TARGET, dtype=np.int8),
                indexed=False,
            )
    else:
        codec.create_abra_file(
            str(output),
            np.array(INPUT, dtype=np.int8),
            np.array(TARGET, dtype=np.int8),
            indexed=False,
            storage=storage,
        )
    assert _inspect(output) == _expected()


def test_absent_target_does_not_create_an_empty_channel(tmp_path, profile):
    output = tmp_path / "single.h5"
    codec.create_abra_file(
        str(output),
        np.array(INPUT, dtype=np.int8),
        indexed=False,
        storage=codec.derive_tidmad_deliverable_spec(profile).storage,
    )
    assert _inspect(output) == _expected(channels=("channel0001",), values=(INPUT,))


def test_indexed_default_and_invalid_extension_keep_their_existing_rules(
    tmp_path, profile
):
    storage = codec.derive_tidmad_deliverable_spec(profile).storage
    invalid = tmp_path / "invalid.txt"
    assert (
        codec.create_abra_file(str(invalid), np.array(INPUT), storage=storage) is None
    )
    assert list(tmp_path.iterdir()) == []
    codec.create_abra_file(
        str(tmp_path / "indexed.h5"), np.array(INPUT, dtype=np.int8), storage=storage
    )
    assert not (tmp_path / "indexed.h5").exists()
    assert _inspect(tmp_path / "indexed_0.h5") == _expected(
        channels=("channel0001",), values=(INPUT,)
    )


def test_missing_profile_and_storage_cannot_select_a_scientific_default(tmp_path):
    # A fresh Context makes this independent of any caller's profile binding.
    with pytest.raises(DatasetProfileBindingError):
        Context().run(
            codec.create_abra_file, str(tmp_path / "unowned.h5"), np.array(INPUT)
        )
    assert list(tmp_path.iterdir()) == []


def test_contrast_storage_controls_every_persisted_value_and_reuse(tmp_path, profile):
    storage = codec.DeliverableStorage(
        input_channel_group="sensor_a",
        target_channel_group="sensor_b",
        storage_dtype="int16",
        value_offset=32768,
    )
    values = [-32768, -1, 0, 1, 32767, -32768, 257, -258]
    output = tmp_path / "contrast.h5"
    codec.create_abra_file(
        str(output),
        np.array(values, dtype=np.int16),
        np.array(values[::-1], dtype=np.int16),
        indexed=False,
        storage=storage,
    )
    assert _inspect(output) == _expected(
        channels=("sensor_a", "sensor_b"), dtype="int16", values=(values, values[::-1])
    )
    assert codec.is_complete_trial_output(str(output), 8, storage)
    assert not codec.is_complete_trial_output(str(output), 7, storage)
    assert not codec.is_complete_trial_output(
        str(output), 8, codec.derive_tidmad_deliverable_spec(profile).storage
    )
    wrong_dtype = storage.model_copy(update={"storage_dtype": "int8"})
    assert not codec.is_complete_trial_output(str(output), 8, wrong_dtype)


def test_streamed_writer_decodes_contrast_offset_and_persists_exact_artifact(
    tmp_path, profile
):
    payload = profile.to_wire()
    payload["dataset"].update(num_files=1, psd_segment_length=8, segments_per_file=1)
    payload["channels"].update(input_channel="sensor_a", target_channel="sensor_b")
    payload["encoding"].update(
        storage_dtype="int16",
        compute_dtype="int32",
        value_offset=32768,
        num_classes=65536,
    )
    payload["anchor_selection_files"] = [0]
    payload["health_peek_files"] = [0]
    contrast = DatasetProfile.model_validate(payload)
    source = tmp_path / "source"
    source.mkdir()
    values = [-32768, -1, 0, 32767, 32767, 0, -1, -32768]
    with h5py.File(source / "abra_validation_0000.h5", "w") as handle:
        for channel in ("sensor_a", "sensor_b"):
            handle.create_dataset(
                f"timeseries/{channel}/timeseries",
                data=np.array(values, dtype=np.int16),
            )
    output = tmp_path / "output"
    output.mkdir()
    scope = codec.TidmadScope(sample_set={0: [0]}, seg_size=4, profile=contrast)

    def predictions():
        for classes in ([0, 32767, 32768, 65535], [65535, 32768, 32767, 0]):
            logits = np.zeros((65536, 4), dtype=np.float32)
            logits[classes, np.arange(4)] = 1
            yield logits

    codec.TidmadTaskDataPath().write_deliverable(
        predictions(),
        DeliverableWriteRequest(
            output_dir=str(output),
            model_type="classifier",
            run_name="parity",
            exp_id="case",
            task_scope=scope,
            source_context=DeliverableSourceContext(
                data_dir=str(source), sample_count=2
            ),
        ),
    )
    files = list(output.glob("*.h5"))
    assert [file.name for file in files] == [
        "abra_validation_denoised_classifier_parity_case_0000.h5"
    ]
    assert _inspect(files[0]) == _expected(
        channels=("sensor_a", "sensor_b"), dtype="int16", values=(values, values)
    )

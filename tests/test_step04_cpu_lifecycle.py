"""Small real CPU lifecycle witnesses for the two event-classification tasks.

These deliberately run the installed framework children (train, inference and
score); fixtures contain only the task-format arrays needed by the declared
task readers and live outside this checkout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np

EXP_ROOT = Path(__file__).resolve().parents[1]


def _workspace(name: str, root: Path) -> Path:
    return root / f"step04_{name}"


def _supernemo_data(root: Path) -> None:
    (root / "event_indexes").mkdir(parents=True)
    for process_index, process in enumerate(("0nubb", "2nubb", "Bi214", "Tl208")):
        starts = np.arange(4, dtype=np.int64) * 2
        features = np.tile(np.array([[100, 10, 20, 30, 40]], dtype=np.float32), (4, 1))
        np.savez(
            root / "event_indexes" / f"{process}_event_index.npz",
            splits=np.array([0, 0, 1, 1], dtype=np.uint8),
            event_ids=np.arange(process_index * 100, process_index * 100 + 4),
            row_starts=starts,
            hit_counts=np.full(4, 2, dtype=np.int32),
            event_features=features,
            energy_sum=np.full(4, 110, dtype=np.float32),
        )
        with h5py.File(
            root
            / {
                "0nubb": "data_0nubb_merged.h5",
                "2nubb": "data_2nubb_merged.h5",
                "Bi214": "data_Bi214_merged.h5",
                "Tl208": "data_Tl208_merged.h5",
            }[process],
            "w",
        ) as handle:
            for key in ("tX", "tY", "tZ", "tR"):
                handle[key] = np.ones(8, dtype=np.float32)


def _majorana_data(root: Path) -> None:
    for partition, count in (("Train", 16), ("Test", 6)):
        for index in range(count):
            with h5py.File(root / f"MJD_{partition}_{index}.hdf5", "w") as handle:
                waveforms = np.zeros((2, 3800), dtype=np.float32)
                waveforms[1, 600 + index] = 1.0
                handle["raw_waveform"] = waveforms
                offset = 0 if partition == "Train" else 10_000
                handle["id"] = np.array(
                    [offset + index * 10, offset + index * 10 + 1], dtype=np.int64
                )
                handle["energy_label"] = np.array([100.0, 100.0], dtype=np.float32)
                handle["psd_label_low_avse"] = np.array([0, 1], dtype=np.uint8)


def _run(task: str, make_data, root: Path) -> dict:
    workspace = _workspace(task, root)
    data = workspace / "data"
    data.mkdir(parents=True)
    make_data(data)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        {
            "CUDA_VISIBLE_DEVICES": "",
            "OMP_NUM_THREADS": "2",
            "MKL_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
            "PYTHON_DOTENV_DISABLED": "1",
        }
    )
    for key in ("SIDERIUS_PLUGIN_DIRS", "SIDERIUS_LOSS_DIRS"):
        env.pop(key, None)
    driver = EXP_ROOT / "tests/step04_cpu_driver.py"
    result = subprocess.run(
        [
            str(Path(sys.executable)),
            "-I",
            str(driver),
            str(EXP_ROOT),
            task,
            str(workspace),
            str(data),
        ],
        env=env,
        cwd=EXP_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    (workspace / "raw_stdout.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((workspace / "cpu_witness_receipt.json").read_text())


def test_supernemo_cpu_lifecycle(tmp_path: Path):
    _run("supernemo_signal_background", _supernemo_data, tmp_path)


def test_majorana_cpu_lifecycle(tmp_path: Path):
    _run("majorana_low_avse", _majorana_data, tmp_path)

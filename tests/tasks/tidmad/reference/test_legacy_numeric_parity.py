"""Optional real-data parity for the task-owned legacy TIDMAD scorer.

This is scientific reference evidence owned by the TIDMAD task package, not a
framework integration default.  The data root is explicit: an unconfigured
optional lane skips visibly, while a configured-invalid resource fails before
the scorer or worker pool can run.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
from types import ModuleType

import pytest

from tasks.tidmad.runtime.scoring import score_vector

_DATA_ENV = "TIDMAD_DATA_DIR"
_FILE = "abra_validation_0000.h5"
_PARITY_TOL = 1e-10


def _load_legacy_reference() -> ModuleType:
    path = Path(__file__).with_name("_legacy_scoring_reference.py")
    spec = importlib.util.spec_from_file_location(
        "tidmad_legacy_scoring_reference", path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load legacy TIDMAD scoring reference from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _configured_data_root() -> Path:
    raw = os.environ.get(_DATA_ENV)
    if raw is None:
        pytest.skip(f"optional legacy TIDMAD parity requires {_DATA_ENV}")
    if not raw.strip():
        pytest.fail(f"{_DATA_ENV} is configured but blank")

    configured = Path(raw).expanduser()
    if not configured.is_absolute():
        pytest.fail(f"{_DATA_ENV} must be an absolute directory: {raw!r}")
    if not configured.exists():
        pytest.fail(f"{_DATA_ENV} does not exist: {configured}")
    if not configured.is_dir():
        pytest.fail(f"{_DATA_ENV} is not a directory: {configured}")

    root = configured.resolve()
    required = configured / _FILE
    if not required.exists():
        pytest.fail(f"{_DATA_ENV} is missing required file: {_FILE}")
    if not required.is_file():
        pytest.fail(f"required TIDMAD resource is not a file: {required}")
    if not required.resolve().is_relative_to(root):
        pytest.fail(f"required TIDMAD resource escapes {_DATA_ENV}: {required}")
    return root


class TestConfiguredResourceContract:
    def test_absent_optional_resource_skips(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(_DATA_ENV, raising=False)
        with pytest.raises(pytest.skip.Exception, match=_DATA_ENV):
            _configured_data_root()

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_explicit_blank_fails(
        self, monkeypatch: pytest.MonkeyPatch, raw: str
    ) -> None:
        monkeypatch.setenv(_DATA_ENV, raw)
        with pytest.raises(pytest.fail.Exception, match="configured but blank"):
            _configured_data_root()

    def test_relative_root_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DATA_ENV, "relative/data")
        with pytest.raises(pytest.fail.Exception, match="absolute directory"):
            _configured_data_root()

    def test_missing_root_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_DATA_ENV, str(tmp_path / "missing"))
        with pytest.raises(pytest.fail.Exception, match="does not exist"):
            _configured_data_root()

    def test_non_directory_root_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        candidate = tmp_path / "file"
        candidate.write_text("not a directory", encoding="utf-8")
        monkeypatch.setenv(_DATA_ENV, str(candidate))
        with pytest.raises(pytest.fail.Exception, match="not a directory"):
            _configured_data_root()

    def test_missing_required_file_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv(_DATA_ENV, str(tmp_path))
        with pytest.raises(pytest.fail.Exception, match="missing required file"):
            _configured_data_root()

    def test_required_file_cannot_escape_root(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside.h5"
        outside.write_bytes(b"not opened")
        (root / _FILE).symlink_to(outside)
        monkeypatch.setenv(_DATA_ENV, str(root))
        with pytest.raises(pytest.fail.Exception, match="escapes"):
            _configured_data_root()


@pytest.mark.real_data
def test_task_scorer_reproduces_the_fine_legacy_scalar(bound_tidmad_profile) -> None:
    data_root = _configured_data_root()
    legacy = _load_legacy_reference()
    args = argparse.Namespace(coarse=False, parallel=True, num_workers=8)
    expected = legacy.calculateBenchmark(str(data_root), [_FILE], args)

    _, actual = score_vector(
        data_dir=str(data_root),
        sample_set={0: list(range(200))},
        anchor_map=None,
        s_max=None,
        denoised_filename_fn=lambda _index: _FILE,
        raw_data_dir=str(data_root),
        parallel=True,
        num_workers=8,
        legacy_mode=True,
    )

    delta = abs(actual - expected)
    assert delta < _PARITY_TOL, (
        f"task scorer legacy parity failed: actual={actual!r}, "
        f"expected={expected!r}, |delta|={delta:.3e}"
    )

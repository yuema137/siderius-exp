"""Task-owned anchor-map behavior and live-tool ownership contracts."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tasks.tidmad.runtime import anchor_map

_TOOLS = (
    "tasks.tidmad.tools.run_comparison",
    "tasks.tidmad.tools.compute_raw_baseline",
    "tasks.tidmad.tools.score_tidmad_official_banded",
    "tasks.tidmad.tools.score_tidmad_official_wavenet",
)
_CANONICAL_S_MAX = 295715680.14248306


def test_default_and_explicit_paths_load_the_requested_json(tmp_path: Path) -> None:
    """A lost explicit override or task-local default could select another ruler."""
    default_path = Path(anchor_map.resolve_anchor_map_path(None))
    assert default_path == Path(anchor_map.__file__).resolve().parents[1] / (
        "reference_data/segment_anchors.json"
    )
    assert anchor_map.load_anchor_map(str(default_path))["s_max"] == _CANONICAL_S_MAX

    explicit_path = tmp_path / "explicit.json"
    explicit_path.write_text(
        '{"s_max": 7.5, "anchors": {"4": [2.0]}}\n', encoding="utf-8"
    )
    assert anchor_map.resolve_anchor_map_path(str(explicit_path)) == str(explicit_path)
    assert anchor_map.load_anchor_map(str(explicit_path)) == {
        "s_max": 7.5,
        "anchors": {"4": [2.0]},
    }


def test_missing_anchor_map_refuses_instead_of_falling_back(tmp_path: Path) -> None:
    """A missing explicit file must not silently load the canonical task artifact."""
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError, match="segment anchor map not found"):
        anchor_map.load_anchor_map(str(missing))


@pytest.mark.parametrize(
    ("content", "message"),
    (
        ("{not-json", "malformed JSON"),
        ('{"s_max": 1.0}', "missing required keys"),
    ),
)
def test_malformed_or_incomplete_anchor_map_refuses(
    tmp_path: Path, content: str, message: str
) -> None:
    """Invalid JSON and a plausible incomplete map are distinct read-time failures."""
    path = tmp_path / "invalid.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        anchor_map.load_anchor_map(str(path))


def test_builder_owns_enumeration_string_keys_and_global_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial scan or local maximum would generate a scientifically different ruler."""
    calls: list[tuple[int, int, str]] = []

    def fake_compute(file_index: int, segment_index: int, data_dir: str):
        calls.append((file_index, segment_index, data_dir))
        return file_index, segment_index, float(file_index * 10 + segment_index)

    monkeypatch.setattr(anchor_map, "NUM_FILES", 2)
    monkeypatch.setattr(anchor_map, "SEGMENTS_PER_FILE", 3)
    monkeypatch.setattr(anchor_map, "_compute_ch2_snr", fake_compute)

    assert anchor_map.build_anchor_map("/not-read") == {
        "s_max": 12.0,
        "segments_per_file": 3,
        "num_files": 2,
        "anchors": {"0": [0.0, 1.0, 2.0], "1": [10.0, 11.0, 12.0]},
    }
    assert calls == [
        (0, 0, "/not-read"),
        (0, 1, "/not-read"),
        (0, 2, "/not-read"),
        (1, 0, "/not-read"),
        (1, 1, "/not-read"),
        (1, 2, "/not-read"),
    ]


@pytest.mark.parametrize("module_name", _TOOLS)
def test_live_tools_bind_the_task_owned_loader(module_name: str) -> None:
    """A reverted import would restore the soon-to-be-retired framework owner."""
    module = importlib.import_module(module_name)
    assert module.load_anchor_map is anchor_map.load_anchor_map


def test_live_tools_import_when_the_old_framework_anchor_module_is_blocked() -> None:
    """Fresh imports must not need the retired framework anchor module to exist."""
    script = f"""
import importlib
import importlib.abc
import sys

class BlockOldAnchorModule(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "execute_tools.build_anchor_map":
            raise ImportError("old framework anchor module is blocked")
        return None

sys.meta_path.insert(0, BlockOldAnchorModule())
from tasks.tidmad.runtime import anchor_map
for module_name in {_TOOLS!r}:
    module = importlib.import_module(module_name)
    assert module.load_anchor_map is anchor_map.load_anchor_map, module_name
"""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[4],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

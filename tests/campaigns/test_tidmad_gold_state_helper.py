"""Campaign-owned checks for persisted Gold band and Stage-2 state."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


EXP_ROOT = Path(__file__).resolve().parents[2]
STATE_HELPER = (
    EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts" / "gold_campaign_state.py"
)


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _run(*args: str, checkout: Path | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if checkout is None:
        env.pop("SIDERIUS_CHECKOUT", None)
    else:
        env["SIDERIUS_CHECKOUT"] = str(checkout)
    return subprocess.run(
        [sys.executable, str(STATE_HELPER), *args],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def test_state_helper_uses_the_explicit_framework_checkout(tmp_path: Path) -> None:
    """Catch derivation of a nonexistent framework root from the external script path."""
    workspace = tmp_path / "empty_band"
    output = tmp_path / "state.json"

    completed = _run(
        "band-state",
        "--workspace",
        str(workspace),
        "--horizon",
        "20",
        "--band",
        "0-3",
        "--out",
        str(output),
        checkout=_siderius_checkout(),
    )

    assert completed.returncode == 0, completed.stderr
    state = json.loads(output.read_text(encoding="utf-8"))
    assert state["next_iter"] == 1
    assert state["committed_count"] == 0
    assert state["terminal"] is False


def test_state_helper_refuses_an_implicit_framework_checkout() -> None:
    """Catch silent imports from an ambient or path-derived SIDERIUS clone."""
    completed = _run("--help", checkout=None)

    assert completed.returncode != 0
    assert "SIDERIUS_CHECKOUT" in completed.stderr

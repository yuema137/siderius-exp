"""Campaign-owned runtime-profile checks for TIDMAD Gold Stage 1."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts" / "run_gold_campaign.sh"
PROFILE_PATH = "/persistent/qualification/runtime_profiles_h100.json"
PROFILE_KEY = "nvidia_h100_80gb_hbm3/single"
PROFILE_SHA256 = "c" * 64


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _run(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)

    return subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--siderius-checkout",
            str(_siderius_checkout()),
            "--workspace_root",
            str(workspace),
            "--stage",
            "1",
            "--arm",
            "blindpod",
            "--fcnet_reference_json",
            str(fcnet_reference),
            "--stagger-seconds",
            "0",
            "--dry-run",
            *extra,
        ],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def _band_commands(stdout: str) -> list[list[str]]:
    return [
        shlex.split(line)
        for line in stdout.splitlines()
        if "sdsc_submission_scripts/run_chain.sh" in line
    ]


def _pairs(command: list[str]) -> dict[str, str]:
    return {
        command[index]: command[index + 1]
        for index in range(len(command) - 1)
        if command[index].startswith("--")
    }


def test_declared_runtime_profile_is_visible_and_reaches_every_band(
    tmp_path: Path,
) -> None:
    """The operator-visible declaration and all four child argv must agree."""
    completed = _run(
        tmp_path,
        "--gold_required_runtime_profile_path",
        PROFILE_PATH,
        "--gold_required_runtime_profile",
        PROFILE_KEY,
        "--gold_required_runtime_profile_sha256",
        PROFILE_SHA256,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _band_commands(completed.stdout)
    assert len(commands) == 4
    for command in commands:
        pairs = _pairs(command)
        assert pairs["--required_runtime_profile_path"] == PROFILE_PATH
        assert pairs["--required_runtime_profile"] == PROFILE_KEY
        assert pairs["--required_runtime_profile_sha256"] == PROFILE_SHA256
        assert command.index("--no-cleanup_denoised") > command.index(
            "--required_runtime_profile_sha256"
        )

    row = next(
        line
        for line in completed.stdout.splitlines()
        if "supplied required_runtime_profile=" in line
    )
    assert PROFILE_PATH in row
    assert PROFILE_KEY in row
    assert PROFILE_SHA256 in row


def test_undeclared_runtime_profile_is_explicit_and_emits_no_child_tokens(
    tmp_path: Path,
) -> None:
    """An unqualified campaign must say the profile is absent and bind none."""
    completed = _run(tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _band_commands(completed.stdout)
    assert len(commands) == 4
    for command in commands:
        assert "--required_runtime_profile_path" not in command
        assert "--required_runtime_profile" not in command
        assert "--required_runtime_profile_sha256" not in command
    assert "supplied required_runtime_profile=(none" in completed.stdout


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        (("--gold_required_runtime_profile", PROFILE_KEY), "INCOMPLETE"),
        (("--gold_required_runtime_profile_sha256", PROFILE_SHA256), "INCOMPLETE"),
        (("--gold_required_runtime_profile_path", PROFILE_PATH), "INCOMPLETE"),
        (
            (
                "--gold_required_runtime_profile",
                PROFILE_KEY,
                "--gold_required_runtime_profile_sha256",
                PROFILE_SHA256,
            ),
            "INCOMPLETE",
        ),
        (
            (
                "--gold_required_runtime_profile_path",
                PROFILE_PATH,
                "--gold_required_runtime_profile",
                "h100",
                "--gold_required_runtime_profile_sha256",
                PROFILE_SHA256,
            ),
            "is not '<gpu_slug>/<regime>'",
        ),
        (
            (
                "--gold_required_runtime_profile_path",
                PROFILE_PATH,
                "--gold_required_runtime_profile",
                PROFILE_KEY,
                "--gold_required_runtime_profile_sha256",
                "deadbeef",
            ),
            "is not 64 lowercase",
        ),
        (
            (
                "--gold_required_runtime_profile_path",
                "qualification/profiles.json",
                "--gold_required_runtime_profile",
                PROFILE_KEY,
                "--gold_required_runtime_profile_sha256",
                PROFILE_SHA256,
            ),
            "is not ABSOLUTE",
        ),
    ],
)
def test_incomplete_or_malformed_runtime_profile_refuses_before_dispatch(
    tmp_path: Path,
    extra: tuple[str, ...],
    expected: str,
) -> None:
    """Invalid declarations must fail once at the campaign boundary."""
    completed = _run(tmp_path, *extra)

    assert completed.returncode != 0
    assert expected in completed.stderr
    assert "run_chain argv" not in completed.stdout


@pytest.mark.parametrize(
    "flag",
    [
        "--required_runtime_profile_path",
        "--required_runtime_profile",
        "--required_runtime_profile_sha256",
    ],
)
def test_chain_level_runtime_profile_override_is_refused(
    tmp_path: Path, flag: str
) -> None:
    """A last-wins child spelling must not bypass the Gold declaration."""
    completed = _run(tmp_path, flag, "unapproved")

    assert completed.returncode != 0
    assert flag in completed.stderr
    assert "GOLD_RESERVED_PASSTHROUGH" in completed.stderr

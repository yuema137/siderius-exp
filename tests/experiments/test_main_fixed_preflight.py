"""NoPrior launch resolution refuses mixed revisions and treatment drift."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from experiments.shared.framework_pin import verify_framework_pin
from experiments.tidmad.main_fixed_workflow import preflight

ROOT = Path(__file__).resolve().parents[2]


def test_framework_pin_requires_dependency_and_checkout_identity(tmp_path: Path) -> None:
    checkout = tmp_path / "infra"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(checkout),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        check=True,
    )
    revision = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    repository = tmp_path / "exp"
    repository.mkdir()
    (repository / "SIDERIUS_REVISION").write_text(revision + "\n")
    (repository / "pyproject.toml").write_text(
        '[project]\ndependencies = ["siderius @ git+https://example.com/SIDERIUS.git@'
        + revision
        + '"]\n'
    )
    (repository / "uv.lock").write_text(
        '[[package]]\nname = "siderius"\n'
        f'source = {{ git = "https://example.com/SIDERIUS.git?rev={revision}#{revision}" }}\n'
    )
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        check=True,
    )
    assert verify_framework_pin(repository, checkout) == revision

    (repository / "pyproject.toml").write_text(
        '[project]\ndependencies = ["siderius @ git+https://example.com/SIDERIUS.git@'
        + "0" * 40
        + '"]\n'
    )
    subprocess.run(["git", "-C", str(repository), "add", "pyproject.toml"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "change pin",
        ],
        check=True,
    )
    with pytest.raises(ValueError, match=r"pyproject\.toml"):
        verify_framework_pin(repository, checkout)


def test_no_prior_preflight_binds_existing_treatment_and_band(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(preflight, "verify_framework_pin", lambda *_: "a" * 40)
    monkeypatch.setattr(preflight, "verify_installed_framework", lambda *_: None)
    monkeypatch.setattr(
        preflight,
        "verify_band_inputs",
        lambda *_: {"band": "4-9", "data_scope": "4-9", "health_gate_files": "4-9"},
    )
    checkout = tmp_path / "infra"
    launcher = checkout / "scripts/launch/run_chain.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/bash\n")
    receipt = preflight.resolve_no_prior_launch(
        ROOT,
        checkout,
        band="4-9",
        data_dir=tmp_path / "data",
        workspace=tmp_path / "workspace",
        run_name="reviewed-run-name",
    )
    command = receipt["command"]
    assert "--no-data_analysis_enabled" in command
    assert "--ml_lit_review_enabled" in command
    assert "--advice" not in command
    assert command[command.index("--data_scope") + 1] == "4-9"
    assert command[command.index("--health_gate_files") + 1] == "4-9"
    assert command[command.index("--formal_eval_portion") + 1] == "1.0"
    assert "--trial_portion" not in command
    assert "--train_portion" not in command

"""Offline regressions for the Pet acquisition destination boundary."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[3]
FETCH_MODULE = "tasks.oxford_iiit_pet.tools.fetch_oxford_iiit_pet"


@pytest.fixture
def relocated_checkout(tmp_path: Path) -> Path:
    """Exercise production files from an unrelated checkout path with spaces."""
    checkout = tmp_path / "relocated checkout"
    for relative in (
        "tasks/oxford_iiit_pet/tools/fetch_oxford_iiit_pet.py",
        "tasks/shared/archive_fetch.py",
    ):
        target = checkout / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EXP_ROOT / relative, target)
    return checkout


def _verify(checkout: Path, destination: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            FETCH_MODULE,
            "--dest",
            str(destination),
            "--no-download",
        ],
        cwd=checkout,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize("relative", ["data/pets", "tasks/data/pets"])
def test_in_repository_destination_is_rejected_before_creation(
    relocated_checkout: Path, relative: str
) -> None:
    """The old tasks-only guard let data/pets reach archive I/O and mkdir."""
    destination = relocated_checkout / relative

    completed = _verify(relocated_checkout, destination)

    assert completed.returncode == 2, completed.stdout + completed.stderr
    assert "is inside the repository" in completed.stderr
    assert not destination.parent.exists()
    assert not destination.exists()
    assert "[fetch]" not in completed.stdout


def test_external_destination_reaches_existing_archive_verification(
    relocated_checkout: Path, tmp_path: Path
) -> None:
    """A valid external path must reach checksum verification without downloading."""
    destination = tmp_path / "external data"
    destination.mkdir()
    archive = destination / "images.tar.gz"
    archive.write_bytes(b"deliberately corrupt local archive")

    completed = _verify(relocated_checkout, destination)

    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "ArchiveIntegrityError" in completed.stderr
    assert "does not match the pinned" in completed.stderr
    assert "is inside the repository" not in completed.stderr
    assert "[fetch]" not in completed.stdout
    assert archive.read_bytes() == b"deliberately corrupt local archive"

"""Preparation refuses before it writes anything.

`prepare()` emits a bundle an external caller will run against. Every
condition it checks is checked *before* the output directory exists, so a
refusal leaves nothing half-written for someone to pick up and deploy.

Each case names a defect nothing else would catch:

* ``test_an_existing_output_is_refused`` — reusing a directory silently
  mixes two deployments, and the receipt of the second would describe files
  from the first.
* ``test_a_bundle_inside_a_repository_is_refused`` — both repositories carry
  the private scoring code, so a bundle written inside one is a bundle that
  cannot be handed over.
* ``test_a_leaky_agent_view_is_refused`` — the separation is verified again
  at publication, because the tool that built the view and the bundle that
  ships it are separated by however long the operator took in between.
* ``test_a_missing_agent_view_names_the_tool`` — an operator who has not
  built the view yet must be told which tool builds it.

The happy path is not a unit test: `verify_framework_pin` requires a
committed tree, which a working copy under test is not. It is exercised by
running the command, and its receipt is the evidence.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from experiments.phyts_tess.main_orchestrator.prepare import (
    LAUNCH_BLOCKERS,
    assert_view_is_publishable,
    prepare,
)

EXP_ROOT = Path(__file__).resolve().parents[2]
IDENTITY = ("split", "gaia_id", "tic", "sector")


def _agent_view(tmp_path: Path, *, leaky: bool = False) -> Path:
    agent = tmp_path / "view" / "agent"
    (agent / "manifests").mkdir(parents=True)
    columns = [*IDENTITY, "frot", "frot_err"]
    with (agent / "manifests" / "train.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow(
            {
                "split": "train",
                "gaia_id": "1",
                "tic": "2",
                "sector": "20",
                "frot": "0.5",
                "frot_err": "0.01",
            }
        )
    evaluated = {"split": "val", "gaia_id": "3", "tic": "4", "sector": "21"}
    predict_columns = list(IDENTITY)
    if leaky:
        predict_columns += ["frot"]
        evaluated["frot"] = "1.25"
    with (agent / "manifests" / "predict.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=predict_columns)
        writer.writeheader()
        writer.writerow(evaluated)
    return agent


def _checkout() -> Path:
    import os

    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        pytest.skip(
            "SIDERIUS_CHECKOUT is not set. Skipped means UNVERIFIED, not passed."
        )
    return Path(configured)


def test_an_existing_output_is_refused(tmp_path):
    existing = tmp_path / "bundle"
    existing.mkdir()
    with pytest.raises(ValueError, match="new directory"):
        prepare(EXP_ROOT, _checkout(), _agent_view(tmp_path), existing)


def test_a_bundle_inside_a_repository_is_refused(tmp_path):
    inside = EXP_ROOT / "build" / "never-created"
    with pytest.raises(ValueError, match="outside both repositories"):
        prepare(EXP_ROOT, _checkout(), _agent_view(tmp_path), inside)
    assert not inside.exists(), "a refusal must leave nothing behind"


def test_a_leaky_agent_view_is_refused(tmp_path):
    """Checked again at publication, not only when the view was built.

    Asserted against the contract `prepare()` calls rather than through a
    whole preparation: the pin check runs first and needs a committed tree,
    which a working copy under test is not.
    """
    with pytest.raises(ValueError) as excinfo:
        assert_view_is_publishable(_agent_view(tmp_path, leaky=True))
    assert "target" in str(excinfo.value).lower()
    assert "refusing to publish" in str(excinfo.value).lower()


def test_a_missing_agent_view_names_the_tool(tmp_path):
    with pytest.raises(ValueError, match="build_views.py"):
        assert_view_is_publishable(tmp_path / "absent")


def test_a_clean_view_reports_its_digests(tmp_path):
    """The receipt must pin what was published, not merely that it passed."""
    receipt = assert_view_is_publishable(_agent_view(tmp_path))
    assert receipt["evaluated_targets_present"] is False
    assert len(receipt["train_manifest_sha256"]) == 64
    assert len(receipt["predict_manifest_sha256"]) == 64


def test_the_blockers_keep_the_receipt_from_reading_as_permission():
    """A bundle is not an authorization, and must say so in its own terms."""
    assert LAUNCH_BLOCKERS, "a receipt with no blockers reads as launch-ready"
    joined = " ".join(LAUNCH_BLOCKERS).lower()
    for unresolved in ("native training binding", "complete evaluator", "budget"):
        assert unresolved in joined, (
            f"{unresolved!r} is not named as outstanding; the receipt would "
            "imply it is settled"
        )

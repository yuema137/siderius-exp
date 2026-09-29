"""What the caller's published runtime may and may not contain.

The task's research-side modules and its operator-side modules live in the
SAME directory. That is why the published set is an explicit list rather
than a copy of it, and why these cases check the list itself as well as the
result:

* ``test_operator_modules_are_never_published`` — a census over the list.
  `prepare.py`, `public_task_tree.py`, `verify_launcher_policy.py`,
  `native_handler.py` and `validation_scope.py` sit beside `validation_rows`,
  and publishing any of them hands the caller the deployment's own controls.
* ``test_publishing_from_the_evaluator_view_is_refused`` — the two views are
  written as siblings, so pointing at the wrong one is an ordinary slip
  rather than an exotic mistake, and it would publish the scorer.
* ``test_a_failed_publication_leaves_nothing`` — a half-written runtime is
  something an operator can pick up and deploy.
* ``test_the_receipt_pins_both_revisions`` — a published runtime that cannot
  say which revisions produced it cannot be reproduced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.phyts_tess.main_orchestrator.public_runtime import (
    OPERATOR_ONLY_MODULES,
    PUBLIC_MODULES,
    publish_public_runtime,
)

EXP_ROOT = Path(__file__).resolve().parents[2]


def _caller_view(tmp_path: Path, *, with_scorer: bool = False) -> Path:
    view = tmp_path / ("evaluator" if with_scorer else "caller")
    runtime = view / "tasks" / "phyts_tess" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "tess_data_path.py").write_text("", encoding="utf-8")
    if with_scorer:
        (runtime / "scoring.py").write_text("", encoding="utf-8")
    return view


def test_operator_modules_are_never_published():
    """The list is the boundary; check the list, not only its output."""
    published = set(PUBLIC_MODULES)
    leaked = published & set(OPERATOR_ONLY_MODULES)
    assert not leaked, (
        f"the published runtime would hand the caller {sorted(leaked)}, which "
        "are the deployment's own controls"
    )
    # Each operator-only module must actually exist, or the census is
    # guarding a name nothing answers to.
    for relative in OPERATOR_ONLY_MODULES:
        assert (EXP_ROOT / relative).is_file(), f"{relative} does not exist"


def test_publishing_from_the_evaluator_view_is_refused(tmp_path):
    with pytest.raises(ValueError, match="private scorer"):
        publish_public_runtime(
            EXP_ROOT,
            _caller_view(tmp_path, with_scorer=True),
            tmp_path / "runtime",
        )


def test_an_existing_destination_is_refused(tmp_path):
    destination = tmp_path / "runtime"
    destination.mkdir()
    with pytest.raises(ValueError, match="must be new"):
        publish_public_runtime(EXP_ROOT, _caller_view(tmp_path), destination)


def test_a_failed_publication_leaves_nothing(tmp_path):
    """A half-written runtime is something someone can pick up and deploy."""
    view = tmp_path / "caller"
    view.mkdir()  # no tasks/ inside, so publication fails after validation
    destination = tmp_path / "runtime"
    with pytest.raises(ValueError):
        publish_public_runtime(EXP_ROOT, view, destination)
    assert not destination.exists()


def test_the_receipt_pins_both_revisions(tmp_path):
    receipt = publish_public_runtime(
        EXP_ROOT, _caller_view(tmp_path), tmp_path / "runtime"
    )
    assert len(receipt["exp_revision"]) == 40
    assert len(receipt["infra_revision"]) == 40
    assert receipt["environment_installed"] is False
    assert receipt["host_access_qualified"] is False
    # Every published file is digested, so the caller's copy can be checked
    # against what was published rather than trusted.
    assert len(receipt["source_sha256"]) >= len(PUBLIC_MODULES)

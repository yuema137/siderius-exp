"""Step 12 / PR-12bc — B6: scope transport + child rehydration.

Design:
``docs/design/generic_framework_upgrade/step_12_external_extensibility_graduation/
pr_12bc_generic_task_boundary_closure.md`` §D.2, §M / B6; ledger §Q.B6
(D-BC-14).

**This is the commit that closes the pairing gap**, and this module is the
permanent owner of the corrected property — B0's inverted guard (a) was
RETIRED here rather than twinned (R-11-10).

The gap, precisely: the training child already transported a BINDING
(`--task_data_path_id`) but never a SCOPE, so `main()` handed
`run_experiment_streaming` none of its three scope parameters, the engine fell
into its regime-A branch and built a `TidmadScope`, and a non-TIDMAD
implementation then refused it with a `TypeError`. Binding transport and scope
transport were structurally unpaired.

What this module owns:

* **un-composed argv is byte-identical** — the emitter yields nothing, and the
  default `shuffle` path still emits no ordering flags;
* **a composed run's argv gains exactly the scope flags and nothing else new**;
* **the payload never rides argv** — only a path and a digest do;
* **the child verifies BEFORE it deserializes**, and a half-supplied pair is
  refused rather than proceeding on whichever half arrived;
* **the composed child never reaches the regime-A `TidmadScope` branches** —
  D-BC-14's replacement for the retired parent-side spy, and a stronger claim
  because it is measured where the scope actually executes.
"""

from __future__ import annotations

import json
import os
import pathlib
from unittest.mock import MagicMock, patch

import pytest

# PR-12d seam C RELOCATED the emitter beside the ABI it writes (R-11-11:
# extract the responsibility rather than grow the launch consumer). Same
# function, same body; aliased so every assertion below is unchanged.
from core.sandbox_executor import TidmadSandbox
from execute_tools.scope_artifact import ScopeArtifactError, scope_digest
from execute_tools.scope_artifact import task_scope_argv as _task_scope_argv
from execute_tools.task_data_path import bind_task_data_path
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath
from nodes.ml_hyperparameter_tune_agent.scope_acquisition import AttemptScopes

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
ENGINE = REPO_ROOT / "execute_tools" / "train_engine_sandbox.py"

MODEL_CFG = {"model_type": "fcnet", "segmentation_size": 10000, "latent_dims": [100, 10]}
TRAIN_CFG = {"lr": 1e-4, "epochs": 1, "batch_size": 1, "device": "cpu"}
LOSS_CFG = {"loss_type": "ce"}
EXP_ID = "b6_exp"
RUN_NAME = "b6_run"
SAMPLE_SET = {0: [1, 2], 3: [0, 4]}

SCOPE_FLAGS = (
    "--task_scope_ref",
    "--task_scope_digest",
    "--task_eval_scope_ref",
    "--task_eval_scope_digest",
)


@pytest.fixture
def sandbox(tmp_path):
    return TidmadSandbox(run_name=RUN_NAME, workspace=str(tmp_path), progress_bar=False)


def _train_success(sb, exp_id):
    def _side_effect(*_a, **_k):
        os.makedirs(sb.dirs["models"], exist_ok=True)
        with open(os.path.join(sb.dirs["models"], f"_OK_{exp_id}"), "wb"):
            pass
        result = MagicMock()
        result.returncode = 0
        result.stdout = "done\n"
        result.stderr = ""
        return result, None

    return _side_effect


def _scopes() -> AttemptScopes:
    return AttemptScopes(
        training=TidmadScope(sample_set={0: [1, 2]}, seg_size=10_000),
        evaluation=TidmadScope(sample_set={3: [0]}, seg_size=10_000),
    )


def _value(cmd: list[str], flag: str) -> str | None:
    return cmd[cmd.index(flag) + 1] if flag in cmd else None


#: Rows the stubbed validation dataset reports, so the declared count is a
#: value this test CHOSE rather than one the environment happened to supply.
_STUB_VALIDATION_ROWS = 7


class _SizedStub:
    """A ``Sized`` stand-in for a materialized validation dataset."""

    def __len__(self) -> int:
        return _STUB_VALIDATION_ROWS


def _stub_validation_materialization():
    """Keep the training spawn off the real TIDMAD files.

    Step 12 / PR-12d, F-12d-35. These two tests acquire an EVALUATION scope,
    and since F-12d-27 hoisted ``validation_rows_argv`` to the training spawn
    the PARENT now calls ``TaskDataPath.validation_dataset`` while building
    argv — which for TIDMAD constructs a ``TIDMADEpochDataset`` over real
    ``.h5`` files and FAILS CLOSED when materialized != requested.

    So these tests silently began requiring a machine with the TIDMAD dataset
    installed. They passed locally and failed on CI, which is exactly the
    failure mode CLAUDE.md's portability rule describes: *local success is not
    evidence of portability when a test touches datasets.* Stubbing the
    materialization removes the dependency AND lets the row count be asserted
    against a value the test owns, instead of whatever the local disk holds.
    """
    return patch.object(TidmadTaskDataPath, "validation_dataset", return_value=_SizedStub())


# ======================================================================
# The emitter
# ======================================================================


class TestTheEmitterIsComposedOnly:
    def test_it_yields_nothing_when_no_scopes_were_acquired(self, tmp_path):
        """The R-11-1 precedent. An un-composed run's command line predates
        scope transport and must not change.
        """
        assert _task_scope_argv(str(tmp_path), EXP_ID, AttemptScopes()) == []
        assert _task_scope_argv(str(tmp_path), EXP_ID, None) == []

    def test_it_emits_a_path_and_a_digest_per_leg(self, tmp_path):
        with bind_task_data_path(TidmadTaskDataPath()):
            fragment = _task_scope_argv(str(tmp_path), EXP_ID, _scopes())
        assert [fragment[0], fragment[2], fragment[4], fragment[6]] == list(SCOPE_FLAGS)

    def test_the_payload_NEVER_rides_argv(self, tmp_path):
        """Frozen (§5.5): scope payloads are attempt-varying and unbounded, so
        raw JSON on argv would eventually meet ``ARG_MAX``. Asserted on the
        emitted tokens, not on intent.
        """
        with bind_task_data_path(TidmadTaskDataPath()):
            fragment = _task_scope_argv(str(tmp_path), EXP_ID, _scopes())
        for token in fragment:
            assert "sample_set" not in token
            assert not token.startswith("{")

    def test_the_digest_it_emits_is_the_digest_of_what_it_wrote(self, tmp_path):
        impl = TidmadTaskDataPath()
        with bind_task_data_path(impl):
            fragment = _task_scope_argv(str(tmp_path), EXP_ID, _scopes())
        ref, digest = fragment[1], fragment[3]
        with open(ref, encoding="utf-8") as fh:
            assert scope_digest(fh.read()) == digest

    def test_the_bytes_are_the_TASKS_own_serialization(self, tmp_path):
        """The framework writes what the implementation produced, verbatim —
        it does not re-canonicalize a payload it cannot read.
        """
        impl = TidmadTaskDataPath()
        scopes = _scopes()
        with bind_task_data_path(impl):
            fragment = _task_scope_argv(str(tmp_path), EXP_ID, scopes)
        with open(fragment[1], encoding="utf-8") as fh:
            assert fh.read() == impl.serialize_scope(scopes.training)

    def test_a_training_scope_with_no_eval_leg_emits_only_the_training_pair(self, tmp_path):
        with bind_task_data_path(TidmadTaskDataPath()):
            fragment = _task_scope_argv(
                str(tmp_path),
                EXP_ID,
                AttemptScopes(training=TidmadScope(sample_set={0: [1]}, seg_size=64)),
            )
        assert "--task_scope_ref" in fragment
        assert "--task_eval_scope_ref" not in fragment

    def test_scopes_without_a_binding_are_a_named_contradiction(self, tmp_path):
        with pytest.raises(ValueError, match="no task data path is bound"):
            _task_scope_argv(str(tmp_path), EXP_ID, _scopes())


# ======================================================================
# Parent argv
# ======================================================================


class TestTheChildRehydrates:
    def test_an_absent_pair_leaves_regime_A_alone(self):
        # PR-12d seam C (B6) RELOCATED this reader beside its writer, so the
        # inference child reuses the SAME verify-before-deserialize
        # implementation instead of copying it. The order it enforces, and
        # every assertion below, are unchanged.
        from execute_tools.scope_artifact import (
            load_transported_scope as _load_transported_scope,
        )

        assert _load_transported_scope(None, None, leg="training") is None

    @pytest.mark.parametrize(("ref", "digest"), [("/some/path", None), (None, "a" * 64)])
    def test_a_half_supplied_pair_is_refused(self, ref, digest):
        """A path without its digest could not be verified; a digest without a
        path names nothing. Proceeding on whichever half arrived is exactly the
        partial-wiring failure the design names.
        """
        # PR-12d seam C (B6) RELOCATED this reader beside its writer, so the
        # inference child reuses the SAME verify-before-deserialize
        # implementation instead of copying it. The order it enforces, and
        # every assertion below, are unchanged.
        from execute_tools.scope_artifact import (
            load_transported_scope as _load_transported_scope,
        )

        with pytest.raises(ValueError, match="half-supplied"):
            _load_transported_scope(ref, digest, leg="training")

    def test_it_verifies_then_deserializes(self, tmp_path):
        # PR-12d seam C (B6) RELOCATED this reader beside its writer, so the
        # inference child reuses the SAME verify-before-deserialize
        # implementation instead of copying it. The order it enforces, and
        # every assertion below, are unchanged.
        from execute_tools.scope_artifact import (
            load_transported_scope as _load_transported_scope,
        )

        impl = TidmadTaskDataPath()
        scope = TidmadScope(sample_set={0: [1, 2]}, seg_size=10_000)
        payload = impl.serialize_scope(scope)
        path = tmp_path / "task_scope_x.json"
        path.write_text(payload, encoding="utf-8")
        with bind_task_data_path(impl):
            got = _load_transported_scope(str(path), scope_digest(payload), leg="training")
        assert got == scope

    def test_a_tampered_artifact_is_refused_before_the_parser_runs(self, tmp_path):
        """The spy: `deserialize_scope` must never be reached. If verification
        ever moves after parsing, this fails.
        """
        # PR-12d seam C (B6) RELOCATED this reader beside its writer, so the
        # inference child reuses the SAME verify-before-deserialize
        # implementation instead of copying it. The order it enforces, and
        # every assertion below, are unchanged.
        from execute_tools.scope_artifact import (
            load_transported_scope as _load_transported_scope,
        )

        impl = TidmadTaskDataPath()
        payload = impl.serialize_scope(TidmadScope(sample_set={0: [1]}, seg_size=64))
        path = tmp_path / "task_scope_x.json"
        path.write_text(payload, encoding="utf-8")
        good = scope_digest(payload)
        path.write_text(payload.replace('"seg_size":64', '"seg_size":32'), encoding="utf-8")

        reached: list[str] = []

        class _Spy(TidmadTaskDataPath):
            def deserialize_scope(self, payload):  # pragma: no cover - must not run
                reached.append(payload)
                raise AssertionError("the parser was reached on a tampered artifact")

        with bind_task_data_path(_Spy()):
            with pytest.raises(ScopeArtifactError, match="does not match the digest"):
                _load_transported_scope(str(path), good, leg="training")
        assert reached == []

    def test_a_foreign_scope_payload_is_refused_by_the_implementation(self, tmp_path):
        """The pairing RULE, preserved: the binding and the scope must come
        from the same task. B6 closes the GAP without softening this.
        """
        # PR-12d seam C (B6) RELOCATED this reader beside its writer, so the
        # inference child reuses the SAME verify-before-deserialize
        # implementation instead of copying it. The order it enforces, and
        # every assertion below, are unchanged.
        from execute_tools.scope_artifact import (
            load_transported_scope as _load_transported_scope,
        )

        payload = json.dumps({"kind": "pets_scope_v1", "rows": [1, 2]})
        path = tmp_path / "task_scope_x.json"
        path.write_text(payload, encoding="utf-8")
        with bind_task_data_path(TidmadTaskDataPath()):
            with pytest.raises(ValueError, match="declares kind 'pets_scope_v1'"):
                _load_transported_scope(str(path), scope_digest(payload), leg="training")


# ======================================================================
# The pairing gap is CLOSED  (D-BC-14's replacement for the retired spy)
# ======================================================================

"""A drafted launcher policy is checked before it is ever launched.

`draft_launcher_policy.py` constructs one from the deployment, and a
root-owned wrapper reads it under sudo — so a mistake surfaces as a
permission error, or as a run against the wrong task, with the clock
already going.

Each case names a defect that would otherwise appear only then:

* ``test_a_shared_uid_is_refused`` — the launcher requires a separate
  coordinator account and refuses at `authorize_native_caller`. Catching it
  here costs nothing; catching it there costs a launch.
* ``test_a_foreign_handler_is_refused`` — the framework's own pattern admits
  any ``experiments.*:name``, which is right for the framework and far too
  broad for a deployment that knows which task it is.
* ``test_a_stale_manifest_digest_is_refused`` — the policy pins the manifest
  it was drafted against. If the manifest moved afterwards, the run would
  compose something other than what was reviewed.
* ``test_an_adjacent_evaluator_view_is_refused`` — `build_views.py` writes
  the two views as siblings. Correct while the operator holds both; a leak
  the moment one of them is what the caller reads.
* ``test_a_foreign_entrypoint_is_refused`` — the first hand-written policy
  named the caller's entry script. Capture requires `argv[1]` to be the
  framework's `train_engine_sandbox.py`, so that policy verified and would
  have refused every real launch with the probe's own PASS message.
* ``test_an_empty_namespace_is_refused`` — bubblewrap mounts no host root
  implicitly; the same policy declared `mounts: []` three times.
* ``test_a_cwd_without_the_entry_module_is_refused`` — the protected
  relaunch is `python -m experiments.shared.native_training_entry` from
  `policy.cwd`; a cwd that does not contain it fails at the first epoch.
* ``test_a_truth_manifest_inside_the_agent_view_is_refused`` — the caller
  would be reading validation targets.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.phyts_tess.main_orchestrator.verify_launcher_policy import (
    EXPECTED_HANDLER,
    verify_launcher_policy,
)


def _files(tmp_path: Path) -> dict[str, Path]:
    """The host files a runtime policy points at, laid out as a deployment."""
    root = tmp_path / "deployment"
    layout = {
        "python": root / "python" / "bin" / "python3.12",
        "entrypoint": root
        / "framework"
        / "src"
        / "execute_tools"
        / "train_engine_sandbox.py",
        "entry_module": root
        / "runtime"
        / "experiments"
        / "shared"
        / "native_training_entry.py",
    }
    for path in layout.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    layout["root"] = root
    layout["runtime"] = root / "runtime"
    return layout


def _namespace(root: Path, cwd: Path) -> dict:
    """A `ValidationNamespace` exposing the whole deployment root read-only.
    Note `bubblewrap`: confinement is a binary the deployment must provide."""
    return {
        "bubblewrap": "/usr/bin/bwrap",
        "cwd": str(cwd),
        "mounts": [{"source": str(root), "target": str(root), "mode": "read"}],
    }


def _runtime_settings(files: dict[str, Path]) -> dict:
    """Shaped for NativeRuntimePolicy over the synthetic deployment layout."""
    namespace = _namespace(files["root"], files["runtime"])
    return {
        "python": str(files["python"]),
        "entrypoint": str(files["entrypoint"]),
        "readable_roots": [str(files["runtime"])],
        "job_parent": "/var/lib/tess-native",
        "probe_namespace": namespace,
        "training_namespace": namespace,
        "worker_namespace": namespace,
        "child_environment": {},
        "device": "cuda:0",
        "constructor_sha256": "1" * 64,
        "builtin_model_sha256": "2" * 64,
        "builtin_objective_sha256": "3" * 64,
        "max_snapshot_bytes": 1048576,
    }


@pytest.fixture
def drafted(tmp_path):
    """A policy that verifies, plus the knobs each case breaks."""
    files = _files(tmp_path)
    manifest = tmp_path / "caller" / "composition.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("task_data_path: {}\n", encoding="utf-8")
    agent_view = tmp_path / "views" / "agent"
    (agent_view / "manifests").mkdir(parents=True)
    truth = tmp_path / "evaluator" / "manifests" / "rotation_identity.csv"
    truth.parent.mkdir(parents=True)
    truth.write_text("split,gaia_id,tic,sector,frot,frot_err\n", encoding="utf-8")
    data = tmp_path / "rundata"
    data.mkdir()

    def draft(**overrides) -> Path:
        runtime = _runtime_settings(files)
        runtime.update(overrides.pop("runtime", {}))
        settings = {
            "runtime": runtime,
            "manifest": str(manifest),
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "profile": json.loads(
                (
                    Path(__file__).resolve().parents[2]
                    / "tasks/phyts_tess/declared/dataset_profile.json"
                ).read_text(encoding="utf-8")
            ),
            "agent_view": str(agent_view),
            "truth_manifest": str(truth),
            "truth_manifest_sha256": hashlib.sha256(truth.read_bytes()).hexdigest(),
            "validation_data": str(data),
        }
        settings.update(overrides.pop("settings", {}))
        payload = {
            "caller_uid": 1001,
            "caller_gid": 1001,
            "coordinator_uid": 1002,
            "cwd": str(files["runtime"]),
            "handler": EXPECTED_HANDLER,
            "settings": settings,
            "environment": {},
            "deadline_epoch": 4102444800.0,
            **overrides,
        }
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    draft.manifest = manifest  # type: ignore[attr-defined]
    draft.agent_view = agent_view  # type: ignore[attr-defined]
    draft.truth = truth  # type: ignore[attr-defined]
    draft.files = files  # type: ignore[attr-defined]
    return draft


def test_a_well_formed_policy_verifies(drafted):
    """The check has to pass the thing it exists to admit."""
    receipt = verify_launcher_policy(drafted())
    assert receipt["handler"] == EXPECTED_HANDLER
    assert receipt["task_data_path_id"] == "phyts_tess_rotation_public"
    assert len(receipt["manifest_sha256"]) == 64


def test_a_shared_uid_is_refused(drafted):
    with pytest.raises(ValueError, match="separate coordinator account"):
        verify_launcher_policy(drafted(coordinator_uid=1001))


def test_a_foreign_handler_is_refused(drafted):
    with pytest.raises(ValueError, match="this deployment is"):
        verify_launcher_policy(
            drafted(handler="experiments.tidmad.main_orchestrator.native_handler:run")
        )


def test_a_stale_manifest_digest_is_refused(drafted):
    policy = drafted()
    drafted.manifest.write_text("task_data_path: {changed: true}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after drafting"):
        verify_launcher_policy(policy)


def test_an_adjacent_evaluator_view_is_refused(drafted):
    policy = drafted()
    (Path(drafted.agent_view).parent / "evaluator").mkdir()
    with pytest.raises(ValueError, match="still beside the agent view"):
        verify_launcher_policy(policy)


def test_a_foreign_entrypoint_is_refused(drafted):
    foreign = drafted.files["entry_module"]
    with pytest.raises(ValueError, match="must be the framework's"):
        verify_launcher_policy(drafted(runtime={"entrypoint": str(foreign)}))


def test_an_empty_namespace_is_refused(drafted):
    empty = {
        "bubblewrap": "/usr/bin/bwrap",
        "cwd": str(drafted.files["runtime"]),
        "mounts": [],
    }
    with pytest.raises(ValueError, match="declares no mounts"):
        verify_launcher_policy(drafted(runtime={"training_namespace": empty}))


def test_a_cwd_without_the_entry_module_is_refused(drafted):
    with pytest.raises(ValueError, match="does not exist; point cwd"):
        verify_launcher_policy(drafted(cwd="/var/lib/tess-native/work"))


def test_a_truth_manifest_inside_the_agent_view_is_refused(drafted):
    leaked = drafted.agent_view / "manifests" / "rotation_identity.csv"
    leaked.write_bytes(drafted.truth.read_bytes())
    with pytest.raises(ValueError, match="inside the agent view"):
        verify_launcher_policy(drafted(settings={"truth_manifest": str(leaked)}))


def test_a_namespace_hiding_an_interpreter_symlink_hop_is_refused(drafted):
    """Mounting the resolved interpreter is not mounting the path bwrap follows."""
    files = drafted.files
    real = files["root"] / "pyroot" / "cpython-3.12.13-linux"
    (real / "bin").mkdir(parents=True)
    (real / "bin" / "python3.12").write_text("", encoding="utf-8")
    (files["root"] / "pyroot" / "cpython-3.12-linux").symlink_to(real)
    linked = files["root"] / "framework" / ".venv" / "bin" / "python"
    linked.parent.mkdir(parents=True)
    linked.symlink_to(
        files["root"] / "pyroot" / "cpython-3.12-linux" / "bin" / "python3.12"
    )
    namespace = _namespace(files["root"], files["runtime"])
    namespace["mounts"] = [
        {
            "source": str(files["runtime"]),
            "target": str(files["runtime"]),
            "mode": "read",
        },
        {
            "source": str(files["entrypoint"].parent),
            "target": str(files["entrypoint"].parent),
            "mode": "read",
        },
        {
            "source": str(files["root"] / "framework"),
            "target": str(files["root"] / "framework"),
            "mode": "read",
        },
        {"source": str(real), "target": str(real), "mode": "read"},
    ]

    with pytest.raises(ValueError, match="symlink hop"):
        verify_launcher_policy(
            drafted(runtime={"python": str(linked), "training_namespace": namespace})
        )


def test_gpu_device_nodes_without_sys_are_refused(drafted):
    """Every /dev/nvidia* node was bound and CUDA still reported no device.

    The driver enumerates GPUs through /sys; the first host probe failed
    with `Error 304` for exactly this omission.
    """
    namespace = _namespace(drafted.files["root"], drafted.files["runtime"])
    namespace["mounts"].append(
        {"source": "/dev/null", "target": "/dev/nvidia0", "mode": "device"}
    )
    with pytest.raises(ValueError, match="but not /sys"):
        verify_launcher_policy(drafted(runtime={"training_namespace": namespace}))


def test_a_writable_work_dir_outside_readable_roots_is_refused(drafted):
    """Capture reads the tuner's own config files from where training writes.

    A work directory that is writable but not a readable root passes every
    other check and refuses the first real launch at input capture.
    """
    files = drafted.files
    work = files["root"] / "caller-work"
    work.mkdir()
    namespace = _namespace(files["root"], files["runtime"])
    namespace["mounts"].append(
        {"source": str(work), "target": str(work), "mode": "write"}
    )
    with pytest.raises(ValueError, match="not a readable root"):
        verify_launcher_policy(drafted(runtime={"training_namespace": namespace}))

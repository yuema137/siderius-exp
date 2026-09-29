"""Enter the policy's training namespace and import what native training needs.

`probe_authorization.sh` proves the sudo route up to input capture. This
proves the next thing: that inside the bubblewrap namespace the policy
declares, the deployment interpreter starts, the framework and the caller's
published runtime import from the policy's `cwd`, and CUDA is visible. With
`mounts: []` a namespace sees only `/proc`, `/dev` and `/tmp`, so a policy
can verify perfectly and still have nothing to run — that is the defect this
probe exists to find before a clock is running.

Run it as the coordinator, because that is who the wrapper runs the child as:

    sudo -u tess-coordinator <framework-python> \\
        experiments/phyts_tess/main_orchestrator/machine/probe_namespace.py \\
        /etc/tess-native/policy.json

It trains nothing, reads no task data, and writes only to the namespace's
private `/tmp`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_IMPORT_CHECK = """
import importlib, json, sys
report = {"executable": sys.executable, "cwd": __import__("os").getcwd()}
for name in ("core.sandbox_executor", "execute_tools.train_engine_sandbox",
             "experiments.shared.native_training_entry",
             "experiments.phyts_tess.main_orchestrator.validation_rows", "torch"):
    try:
        module = importlib.import_module(name)
        report[name] = getattr(module, "__file__", "<namespace>")
    except Exception as error:  # noqa: BLE001 - the report IS the diagnosis
        report[name] = f"IMPORT FAILED: {type(error).__name__}: {error}"
try:
    import torch
    report["cuda_available"] = torch.cuda.is_available()
    report["cuda_device_count"] = torch.cuda.device_count()
except Exception as error:  # noqa: BLE001
    report["cuda_available"] = f"FAILED: {error}"
print(json.dumps(report, indent=2))
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    parser.add_argument(
        "--namespace",
        choices=("probe", "training", "worker"),
        default="training",
    )
    args = parser.parse_args(argv)
    # Imported here so the module is runnable by path with the deployment's
    # interpreter, which has the framework and this checkout's `experiments`
    # on its path only once the entry script's root is added.
    root = Path(__file__).resolve().parents[4]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from experiments.shared.native_launcher import NativeLauncherPolicy
    from experiments.shared.native_runtime import NativeRuntimePolicy

    policy = NativeLauncherPolicy.model_validate_json(args.policy.read_bytes())
    runtime = NativeRuntimePolicy.model_validate(policy.settings["runtime"])
    namespace = getattr(runtime, f"{args.namespace}_namespace")
    command = [*namespace.prefix(), str(runtime.python), "-c", _IMPORT_CHECK]
    print("namespace:", args.namespace)
    print("cwd inside:", namespace.cwd)
    print("mounts:", len(namespace.mounts))
    completed = subprocess.run(
        command,
        cwd=policy.cwd,
        env=dict(runtime.child_environment),
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        print(f"FAIL: exit {completed.returncode}", file=sys.stderr)
        return 1
    failed = (
        "IMPORT FAILED" in completed.stdout
        or '"cuda_available": false' in completed.stdout
    )
    print(
        "FAIL: see report above"
        if failed
        else "PASS: namespace can run native training"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

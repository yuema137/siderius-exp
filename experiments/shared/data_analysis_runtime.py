"""Qualify generated analysis in the framework environment before a run clock."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class AnalysisSandboxReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: StrictBool
    protocol_id: Literal["siderius.generated-analysis-sandbox.v1"]
    bubblewrap_path: str | None
    unshare_path: str | None
    reason: str | None = None


class AnalysisRuntimeReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    python_prefix: Path
    sandbox: AnalysisSandboxReceipt


# Run the existing framework authority in the same environment as run_chain.
# A command lookup alone cannot detect namespace, mount or import failures.
_PROBE = """
import json, sys
from dataclasses import asdict
from agent.data_analysis.analysis_code_sandbox import AnalysisCodeSandbox
receipt = AnalysisCodeSandbox().probe()
print(json.dumps({"python_prefix": sys.prefix, "sandbox": asdict(receipt)}))
"""


def require_generated_analysis_runtime(checkout: Path) -> AnalysisRuntimeReceipt:
    """Check the current UID/environment; never read task data or call a model.

    Readiness is a live host observation, not part of a frozen scientific
    identity. Call on previews and real starts, including reviewed continuations.
    """
    environment = checkout.resolve() / ".venv"
    python = environment / "bin/python"
    if not python.is_file():
        raise ValueError(f"Data Analysis framework environment is missing: {python}")
    try:
        completed = subprocess.run(
            [str(python), "-I", "-B", "-c", _PROBE],
            cwd=checkout,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(
            "Data Analysis runtime qualification could not complete"
        ) from exc
    if completed.returncode:
        # Arbitrary child stderr may contain host details; preserve it for the
        # caller without treating unvalidated output as a readiness receipt.
        raise ValueError(
            "Data Analysis runtime qualification failed "
            f"(exit {completed.returncode}): {completed.stderr[-1000:]}"
        )
    receipt = AnalysisRuntimeReceipt.model_validate_json(completed.stdout)
    if receipt.python_prefix.resolve() != environment:
        raise ValueError("Data Analysis probe used a foreign framework environment")
    if not receipt.sandbox.available:
        raise ValueError(
            "Data Analysis generated-code runtime is unavailable: "
            f"{receipt.sandbox.reason or 'sandbox probe refused'}. "
            "Install bubblewrap and util-linux on the execution host, then qualify "
            "the namespace sandbox under the actual service user and environment. "
            "No experiment clock has been started by this check."
        )
    return receipt


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--siderius-checkout", required=True, type=Path)
    arguments = parser.parse_args()
    print(
        json.dumps(
            require_generated_analysis_runtime(arguments.siderius_checkout).model_dump(
                mode="json"
            )
        )
    )

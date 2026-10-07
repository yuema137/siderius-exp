"""Verify the installed compatibility package and its qualification refusal.

Invoke with the candidate infra checkout's own Python. This checks package
provenance and loader behavior without contacting providers or executing data.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch


def check() -> dict:
    import siderius_prompt_compat as installed

    import agent
    from agent.prompt_rendering import resolve_prompt_profile

    source = Path(__file__).parent / "src/siderius_prompt_compat"
    target = Path(installed.__file__).parent
    checkout = Path(agent.__file__).resolve().parents[2]
    files = sorted(p for p in source.rglob("*") if p.suffix in {".py", ".md", ".json"})
    expected = {str(p.relative_to(source)): p.read_bytes() for p in files}
    actual = {
        str(p.relative_to(target)): p.read_bytes()
        for p in target.rglob("*")
        if p.suffix in {".py", ".md", ".json"}
    }
    if actual != expected:
        raise AssertionError("Installed package differs from the reviewed source package")
    rows = json.loads((source / "source-inventory.json").read_text())
    for row in rows:
        original = subprocess.check_output(
            ["git", "-C", str(checkout), "show", f"{row['revision']}:{row['source']}"]
        )
        if hashlib.sha256(original).hexdigest() != row["source_sha256"]:
            raise AssertionError("Historical source inventory drift")
        if hashlib.sha256(expected[row["packaged_file"]]).hexdigest() != row["packaged_sha256"]:
            raise AssertionError("Frozen packaged renderer drift")
    names = (
        "paper-early-v1",
        "paper-late-v1",
        "paper-tidmad-noprior-v1",
        "paper-analysis-c0467447-v1",
    )
    identities = [resolve_prompt_profile(name).identity().model_dump(mode="json") for name in names]
    with patch.object(installed, "rendering_assembly_digest", return_value="0" * 64):
        for name in names:
            try:
                resolve_prompt_profile(name)
            except ValueError as exc:
                if "not been qualified" not in str(exc):
                    raise
            else:
                raise AssertionError("Unqualified assembly was accepted")
    return {
        "installed_source_files": len(files),
        "frozen_source_entries": len(rows),
        "profiles": identities,
        "unqualified_assembly_refusals": len(names),
        "api_calls": 0,
        "training_calls": 0,
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))

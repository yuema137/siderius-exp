"""Check installed sources, real provider discovery and child identity offline."""

import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


def check(infra_checkout: Path) -> dict:
    import core.preflight_estimation as registry
    import siderius_preflight_compat as installed
    from core.planner_strategy_identity import source_fingerprint

    source = Path(__file__).parent / "src/siderius_preflight_compat"
    target = Path(installed.__file__).parent
    expected = {
        p.name: p.read_bytes() for p in source.iterdir() if p.suffix in {".py", ".json"}
    }
    actual = {
        p.name: p.read_bytes() for p in target.iterdir() if p.suffix in {".py", ".json"}
    }
    if actual != expected:
        raise ValueError("Installed preflight package differs from reviewed source")
    revision = subprocess.check_output(
        ["git", "-C", str(infra_checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if subprocess.check_output(
        ["git", "-C", str(infra_checkout), "diff", "HEAD", "--", "src"], text=True
    ):
        raise ValueError("Infra source checkout is modified")
    if (
        Path(registry.__file__).read_bytes()
        != (infra_checkout / "src/core/preflight_estimation.py").read_bytes()
    ):
        raise ValueError("Installed preflight registry differs from selected checkout")
    profile = registry.resolve_preflight_estimator(installed.SELECTION)
    identity = profile.identity()
    checkout_probe = json.loads(
        subprocess.check_output(
            [
                str(infra_checkout / ".venv/bin/python"),
                "-c",
                (
                    "import json; import core.preflight_estimation as r; "
                    "print(json.dumps({'registry': r.__file__, "
                    "'assembly': r.estimation_assembly_digest()}))"
                ),
            ],
            text=True,
        )
    )
    if (
        Path(checkout_probe["registry"]).resolve()
        != (infra_checkout / "src/core/preflight_estimation.py").resolve()
    ):
        raise ValueError(
            "Selected checkout environment loads another source installation"
        )
    if checkout_probe["assembly"] != identity.assembly_sha256:
        raise ValueError(
            "Selected checkout assembly differs from the invoking environment"
        )
    qualification = json.loads(expected["qualification.json"])
    references = sorted(
        {
            row["infra_revision"]
            for row in qualification["assemblies"]
            if row["assembly_sha256"] == identity.assembly_sha256
        }
    )
    if not references:
        raise ValueError("Selected clean assembly is not explicitly qualified")
    expected_hash = source_fingerprint(
        {name: expected[name] for name in installed.source_files()}
    )
    if identity.content_sha256 != expected_hash:
        raise ValueError("Installed identity differs from reviewed package sources")
    child_code = (
        "import json; from core.preflight_estimation import resolve_preflight_estimator; "
        f"print(resolve_preflight_estimator({installed.SELECTION!r}).identity().model_dump_json())"
    )
    child = json.loads(
        subprocess.check_output([sys.executable, "-c", child_code], text=True)
    )
    if child != identity.model_dump(mode="json"):
        raise ValueError("Parent/child installed estimator identities differ")
    with patch.object(registry, "estimation_assembly_digest", return_value="0" * 64):
        try:
            registry.resolve_preflight_estimator(installed.SELECTION)
        except ValueError as exc:
            if "has not qualified" not in str(exc):
                raise
        else:
            raise ValueError("Unknown assembly was accepted")
    return {
        "infra_revision": revision,
        "qualified_reference_revisions": references,
        "selected_checkout_assembly_match": True,
        "installed_source_files": len(expected),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("siderius-preflight-compat", "siderius-planner-compat")
        },
        "identity": identity.model_dump(mode="json"),
        "child_identity_match": True,
        "unknown_assembly_refused": True,
        "api_calls": 0,
        "gpu_calls": 0,
        "training_calls": 0,
        "scope": "Normal installed sources, profile discovery and subprocess identity; no data or training execution",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--infra-checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(check(args.infra_checkout.resolve()), indent=2) + "\n"
    )

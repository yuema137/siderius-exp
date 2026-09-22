"""Materialize frozen Full inputs outside source checkouts; never start a run."""

import argparse
import json
from pathlib import Path

import yaml

from experiments.tidmad.information_treatments.frozen_prior import frozen_prior
from experiments.tidmad.information_treatments.prior_binding import (
    Prior,
    composition_overlay,
    resolve_da_only,
    resolve_prior,
)
from experiments.tidmad.main_fixed_workflow.full_binding import (
    verify_full_analysis_binding,
)


def prepare_full(
    root: Path, band: str, output: Path, *, model_advice: bool = True
) -> dict[str, object]:
    """Create a fresh deployment input directory and return verified identities."""
    root, output = root.resolve(), output.resolve()
    if output.is_relative_to(root):
        raise ValueError("Full deployment inputs must be outside the checkout")
    treatment = resolve_prior(root, Prior.ON) if model_advice else resolve_da_only(root)
    manifest = frozen_prior(root)
    if band not in manifest.analysis_policies:
        raise ValueError(f"no frozen Full policy for band {band!r}")
    source = manifest.analysis_policies[band].verify(root)
    output.mkdir(parents=True, exist_ok=False)
    policy = output / "analysis-policy.yaml"
    policy.write_bytes(source.read_bytes())
    composition = output / "composition.yaml"
    composition.write_text(yaml.safe_dump(composition_overlay(root, policy)))
    receipt = verify_full_analysis_binding(
        root,
        band=band,
        policy_path=policy,
        policy_sha256=manifest.analysis_policies[band].sha256,
        composition_path=composition,
        model_advice=model_advice,
    )
    receipt.update(
        {
            "prior_version": manifest.version,
            "band": band,
            "advice_path": str(treatment.advice_path) if model_advice else None,
            "advice_sha256": manifest.advice.sha256 if model_advice else None,
        }
    )
    (output / "binding-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--band", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--condition", choices=("full", "da-only"), default="full")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    print(
        json.dumps(
            prepare_full(
                root, args.band, args.output_dir, model_advice=args.condition == "full"
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

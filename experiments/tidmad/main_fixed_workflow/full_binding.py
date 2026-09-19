"""Validate explicit Full analysis inputs without changing task declarations."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field
from workflows.data_analysis_composition import DataAnalysisWorkflowConfig

from experiments.shared.checksum_manifest import sha256_file
from experiments.tidmad.information_treatments.prior_binding import (
    candidate_analysis_policy,
    composition_overlay,
)


class FullAnalysisInputs(BaseModel):
    """Operator-supplied Full files; the digest is explicit, never discovered."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    policy_path: Path
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    composition_path: Path

    def require_external_to(self, *directories: Path) -> None:
        """Keep operator inputs outside source, data and mutable run directories."""
        for path in (self.policy_path, self.composition_path):
            if any(
                path.resolve().is_relative_to(root.resolve()) for root in directories
            ):
                raise ValueError(
                    "Full analysis inputs must be outside checkouts, data and run directories"
                )


def verify_full_analysis_binding(
    root: Path,
    *,
    band: str,
    policy_path: Path,
    policy_sha256: str,
    composition_path: Path,
) -> dict[str, str]:
    """Verify operator-selected bytes and the common input-only data boundary.

    This checks a supplied policy; it does not select a time budget or declare
    that an operator has approved formal Full. The policy constructor owns
    access declarations and can also be consumed by orchestration preparation.
    """
    root, policy_path, composition_path = (
        path.resolve() for path in (root, policy_path, composition_path)
    )
    if policy_path.is_relative_to(root) or composition_path.is_relative_to(root):
        raise ValueError(
            "Full launch artifacts must be outside the experiment checkout"
        )
    if sha256_file(policy_path) != policy_sha256:
        raise ValueError(
            "Full analysis policy differs from the explicitly bound digest"
        )
    policy = DataAnalysisWorkflowConfig.model_validate(
        yaml.safe_load(policy_path.read_text())
    )
    access_authority = candidate_analysis_policy(root, band)
    for field in ("available_assets", "declared_scope", "access_policy"):
        if getattr(policy, field) != getattr(access_authority, field):
            raise ValueError(
                f"Full analysis {field} differs from the common band input-only boundary"
            )
    actual = yaml.safe_load(composition_path.read_text())
    expected = composition_overlay(root, policy_path)
    if actual != expected:
        raise ValueError(
            "Full composition must be the frozen task plus the bound analysis policy"
        )
    return {
        "analysis_policy_path": str(policy_path),
        "analysis_policy_sha256": policy_sha256,
        "composition_path": str(composition_path),
        "composition_sha256": sha256_file(composition_path),
    }

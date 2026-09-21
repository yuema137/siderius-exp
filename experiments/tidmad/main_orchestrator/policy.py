"""Policy bindings for the shared prior and orchestrator-only strategy advice."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from experiments.shared.checksum_manifest import sha256_file
from experiments.tidmad.information_treatments.prior_binding import (
    Prior,
    candidate_analysis_policy,
    composition_overlay,
    resolve_prior,
)

__all__ = ["Prior", "candidate_analysis_policy", "composition_overlay", "resolve_prior"]


CONTROLLER_STRATEGY_RELATIVE_PATH = Path(
    "experiments/tidmad/information_treatments/controller-work-strategy-v2.md"
)
CONTROLLER_STRATEGY_SHA256 = (
    "2c0f22319c8f68fc55a7cf87c02fbecffc0eff40d2d82afc3788e5f5519dc30a"
)


@dataclass(frozen=True)
class ControllerStrategyBinding:
    """Identity and routing for the additional outer-controller advice layer."""

    artifact: str
    sha256: str
    recipients: tuple[str, ...] = ("outer_controller",)
    layering: str = "on_top_of_model_research_advice"

    def receipt(self) -> dict[str, object]:
        """Return the JSON-safe deployment declaration."""
        return {
            "artifact": self.artifact,
            "sha256": self.sha256,
            "recipients": list(self.recipients),
            "layering": self.layering,
        }


def materialize_controller_strategy(
    root: Path, output: Path
) -> ControllerStrategyBinding:
    """Verify and copy the frozen controller-only strategy into a Full output."""
    source = (root / CONTROLLER_STRATEGY_RELATIVE_PATH).resolve()
    root = root.resolve()
    if not source.is_relative_to(root):
        raise ValueError("controller strategy must stay inside its repository")
    actual_sha256 = sha256_file(source)
    if actual_sha256 != CONTROLLER_STRATEGY_SHA256:
        raise ValueError(
            "controller strategy checksum mismatch: "
            f"expected {CONTROLLER_STRATEGY_SHA256}, got {actual_sha256}"
        )
    artifact = "controller-work-strategy.md"
    (output / artifact).write_bytes(source.read_bytes())
    return ControllerStrategyBinding(artifact=artifact, sha256=actual_sha256)


__all__ += [
    "CONTROLLER_STRATEGY_RELATIVE_PATH",
    "CONTROLLER_STRATEGY_SHA256",
    "ControllerStrategyBinding",
    "materialize_controller_strategy",
]

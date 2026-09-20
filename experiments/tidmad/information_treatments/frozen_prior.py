"""Read the shared, content-pinned Full treatment without launching a run."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field
from workflows.data_analysis_composition import DataAnalysisWorkflowConfig

from experiments.shared.checksum_manifest import sha256_file


class FrozenArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    def verify(self, root: Path) -> Path:
        path = (root / self.path).resolve()
        if Path(self.path).is_absolute() or not path.is_relative_to(root.resolve()):
            raise ValueError("frozen prior artifact must stay inside its repository")
        if sha256_file(path) != self.sha256:
            raise ValueError(f"frozen prior artifact checksum mismatch: {self.path}")
        return path


class FrozenPrior(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["full-prior-v6"]
    advice: FrozenArtifact
    analysis_policies: dict[str, FrozenArtifact]


def frozen_prior(root: Path) -> FrozenPrior:
    """Load the experiment declaration; hashes are checked before use."""
    return FrozenPrior.model_validate_json(
        (
            root
            / "experiments/tidmad/information_treatments/full-prior-v6/manifest.json"
        ).read_text()
    )


def full_analysis_policy(root: Path, band: str) -> DataAnalysisWorkflowConfig:
    """Both workflow and orchestration consume the same frozen band policy."""
    declaration = frozen_prior(root)
    declaration.advice.verify(root)
    if band not in declaration.analysis_policies:
        raise ValueError(f"no frozen Full policy for band {band!r}")
    path = declaration.analysis_policies[band].verify(root)
    return DataAnalysisWorkflowConfig.model_validate(yaml.safe_load(path.read_text()))

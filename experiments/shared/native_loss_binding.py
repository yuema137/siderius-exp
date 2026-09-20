"""Bind approved custom-loss source in the confined native training child.

The protected launcher supplies this declaration over an inherited descriptor.
It is not an authorization document a research caller may submit. No review
runs here or inside the epoch loop. Candidate imports require prior confinement.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from experiments.shared.objective_code_package import (
    ObjectiveCodePackage,
    bound_objective_source,
    require_package_source,
)
from experiments.shared.objective_review_pipeline import AutomaticReviewBundle


class AdmittedLossSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: str = Field(min_length=1, max_length=1048576)
    loss_name: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,95}$")
    parameters: dict[str, JsonValue]
    code_package: ObjectiveCodePackage | None = None

    @model_validator(mode="after")
    def matching_source(self):
        require_package_source(self.source, self.code_package)
        return self


def admitted_loss_source(
    bundle: AutomaticReviewBundle, *, policy_sha256: str, objective_sha256: str
) -> AdmittedLossSource:
    """Project validated operator-owned approval; do not import its source."""
    bundle = AutomaticReviewBundle.model_validate_json(bundle.model_dump_json())
    if (
        bundle.receipt.decision != "approved"
        or bundle.receipt.policy_sha256 != policy_sha256
        or bundle.material.sha256 != objective_sha256
    ):
        raise ValueError("native loss does not have the required approval")
    request = bundle.numerical_request
    return AdmittedLossSource(
        source=request.source,
        loss_name=request.loss_name,
        parameters=request.parameters,
        code_package=request.code_package,
    )


@contextmanager
def bind_native_loss(source: AdmittedLossSource) -> Iterator[None]:
    """Use native registration and defaults; retain the module for training."""
    from ml_models import loss_models_sandbox as losses
    from ml_models import loss_plugin_loader as loader

    registries = (
        losses.LOSS_REGISTRY,
        losses.LOSS_CONFIG_REGISTRY,
        losses.LOSS_CONTRACT_REGISTRY,
        loader.LOSS_TARGET_DTYPE_REGISTRY,
        loader.LOSS_REDUCTION_REGISTRY,
    )
    # Registration owns dtype/reduction side effects too. Restore all mappings
    # even when an invalid declaration announces an unexpected loss name.
    previous = [dict(registry) for registry in registries]
    try:
        with bound_objective_source(source.source, source.code_package) as path:
            name = losses.register_loss_in_memory(str(path))
            if name != source.loss_name:
                raise ValueError("native loss identity differs from approved source")
            configuration = losses.LOSS_CONFIG_REGISTRY[name]()
            if (
                not isinstance(configuration, BaseModel)
                or configuration.model_dump(mode="json") != source.parameters
            ):
                raise ValueError("native loss defaults differ from approved parameters")
            yield
    finally:
        for registry, saved in zip(registries, previous, strict=True):
            registry.clear()
            registry.update(saved)

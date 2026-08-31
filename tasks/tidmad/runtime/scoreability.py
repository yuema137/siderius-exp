"""Task-owned scoreability contract for TIDMAD denoising deliverables."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping

import h5py
from pydantic import Field

from execute_tools.evaluation_metric import (
    ScoreabilityContract,
    ScoreabilityFailure,
    ScoreabilityVerdict,
)


class TidmadScoreabilityContract(ScoreabilityContract):
    """Validate the HDF5 fields consumed by the frozen TIDMAD scorer."""

    contract_id: str = "tidmad_denoised_h5"
    input_channel_group: str = Field(
        description="Group holding the denoised signal consumed as channel one."
    )
    required_attrs: tuple[str, ...] = ("voltage_range_mV", "sampling_frequency")
    required_storage_dtype: str = Field(
        description="NumPy dtype name required for persisted samples."
    )

    def check(self, deliverables: Mapping[int, str]) -> ScoreabilityVerdict:
        failures: list[ScoreabilityFailure] = []
        if not deliverables:
            failures.append(
                ScoreabilityFailure(
                    requirement="completeness",
                    detail="no in-scope file was named for scoring",
                )
            )
        for identity, path in deliverables.items():
            failures.extend(self._check_one(int(identity), path))
        return ScoreabilityVerdict(contract_id=self.contract_id, failures=tuple(failures))

    def _check_one(self, identity: int, path: str) -> list[ScoreabilityFailure]:
        def fail(requirement: str, detail: str) -> ScoreabilityFailure:
            return ScoreabilityFailure(
                requirement=requirement,
                input_identity=identity,
                detail=detail,
            )

        if not os.path.isfile(path):
            return [fail("completeness", f"deliverable not found at {path!r}")]
        try:
            with h5py.File(path, "r") as handle:
                return self._check_open(handle, path, fail)
        except OSError as exc:
            return [
                fail("completeness", f"deliverable at {path!r} is not readable HDF5: {exc}")
            ]

    def _check_open(
        self,
        handle: h5py.File,
        path: str,
        fail: Callable[[str, str], ScoreabilityFailure],
    ) -> list[ScoreabilityFailure]:
        failures: list[ScoreabilityFailure] = []
        samples_key = "/".join(("timeseries", self.input_channel_group, "timeseries"))
        node = handle.get(samples_key)
        if not isinstance(node, h5py.Dataset):
            failures.append(
                fail(
                    "required_channels",
                    f"input channel dataset {samples_key!r} missing in {path!r}",
                )
            )
        elif str(node.dtype) != self.required_storage_dtype:
            failures.append(
                fail(
                    "required_dtype",
                    f"{samples_key!r} in {path!r} is stored as {str(node.dtype)!r}, "
                    f"required {self.required_storage_dtype!r}",
                )
            )

        attrs_key = "/".join(("timeseries", self.input_channel_group))
        attrs_group = handle.get(attrs_key)
        if isinstance(attrs_group, h5py.Group):
            for attr in self.required_attrs:
                if attr not in attrs_group.attrs:
                    failures.append(
                        fail(
                            "required_attrs",
                            f"attr {attr!r} missing on group {attrs_key} in {path!r}",
                        )
                    )
        return failures

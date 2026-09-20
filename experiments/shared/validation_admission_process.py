"""One-time, target-free subprocesses used by protected native admission.

All runtime paths and namespace settings come from the operator. The caller
binds source/config identity and publishes review evidence; these probes alone
never authorize private validation or execute in the per-epoch loop.
"""

import os
import subprocess
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from experiments.shared.native_loss_discovery import (
    LossDiscoveryRequest,
    NativeLossSelection,
)
from experiments.shared.native_model_discovery import (
    ModelDiscoveryRequest,
    NativeModelSelection,
)
from experiments.shared.native_objective_metadata import (
    NativeObjectiveMetadata,
    ObjectiveMetadataRequest,
)
from experiments.shared.native_training_metadata import (
    NativeConfigurationMetadata,
    NativeConfigurationRequest,
)
from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
    NumericalReviewResult,
)
from experiments.shared.validation_confinement import ValidationNamespace

Result = TypeVar("Result", bound=BaseModel)


@dataclass(frozen=True)
class AdmissionProbeRuntime:
    python: Path
    namespace: ValidationNamespace
    environment: Mapping[str, str]
    diagnostics: Path
    deadline: float  # One continuing monotonic deadline, never reset per probe.

    def loss_selection(self, request: LossDiscoveryRequest) -> NativeLossSelection:
        return self._run(request, "native_loss_discovery", NativeLossSelection)

    def model_selection(self, request: ModelDiscoveryRequest) -> NativeModelSelection:
        return self._run(request, "native_model_discovery", NativeModelSelection)

    def configuration(
        self, request: NativeConfigurationRequest
    ) -> NativeConfigurationMetadata:
        return self._run(
            request, "native_training_metadata", NativeConfigurationMetadata
        )

    def objective_metadata(
        self, request: ObjectiveMetadataRequest
    ) -> NativeObjectiveMetadata:
        return self._run(request, "native_objective_metadata", NativeObjectiveMetadata)

    def numerical(self, request: NumericalReviewRequest) -> NumericalReviewResult:
        return self._run(request, "objective_numerical_review", NumericalReviewResult)

    def _run(
        self, request: BaseModel, module: str, result_type: type[Result]
    ) -> Result:
        if self.namespace.share_network:
            raise ValueError("admission probes require isolated networking")
        if time.monotonic() >= self.deadline:
            raise TimeoutError("admission deadline exhausted before probe")
        payload = request.model_dump_json().encode()
        if len(payload) > 4194304:
            raise ValueError("admission request exceeds limit")
        # This parent is operator-owned and never mounted into probe namespaces.
        directory = Path(tempfile.mkdtemp(prefix=f"{module}-", dir=self.diagnostics))
        started = time.monotonic()
        status = "failed"
        try:
            with (
                os.fdopen(
                    os.open(
                        directory / "stdout.json",
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                    ),
                    "wb",
                ) as output,
                os.fdopen(
                    os.open(
                        directory / "stderr.log",
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                    ),
                    "wb",
                ) as errors,
                subprocess.Popen(
                    [
                        *self.namespace.prefix(),
                        str(self.python),
                        "-B",
                        "-m",
                        f"experiments.shared.{module}",
                    ],
                    cwd=self.namespace.cwd,
                    env=dict(self.environment),
                    stdin=subprocess.PIPE,
                    stdout=output,
                    stderr=errors,
                ) as process,
            ):
                try:
                    process.communicate(
                        payload, timeout=max(0.001, self.deadline - time.monotonic())
                    )
                except subprocess.TimeoutExpired as error:
                    # bubblewrap's die-with-parent covers its namespace children.
                    process.kill()
                    process.wait(timeout=2)
                    status = "deadline_exhausted"
                    raise TimeoutError("admission probe exceeded deadline") from error
                if process.returncode != 0:
                    raise RuntimeError(
                        f"admission probe failed; private evidence: {directory}"
                    )
            with (directory / "stdout.json").open("rb") as output:
                response = output.read(4194305)
            if len(response) > 4194304:
                raise ValueError("admission response exceeds limit")
            result = result_type.model_validate_json(response)
            status = "completed"
            return result
        finally:
            import json

            with os.fdopen(
                os.open(
                    directory / "timing.json",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                ),
                "w",
            ) as timing:
                json.dump(
                    {"status": status, "seconds": time.monotonic() - started}, timing
                )

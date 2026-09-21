"""The PhyTS TESS pack's Health view provider.

Registers through the SAME public interface an out-of-tree task uses, is
loaded ONLY through the pack's ``declared/task_health.yaml`` explicit
``kind: file`` ref, and its content digest joins the pinned run identity.
Underscore-prefixed so no wholesale ``plugins/`` scan ever execs it.

**The view.** This task's deliverable is one scalar rotation frequency per
light curve, so the continuous-sample stream is simply every predicted value,
ordered by the deliverable's own row key. Sorting makes the projection
independent of dict insertion order, which would otherwise let two runs over
the same predictions produce differently ordered views.

The payload is read through ``ctx.load_evaluation_payload()`` — the task's
own codec, reused lazily after applicability has been decided. Reconstructing
the filename here would couple Health to one storage convention and let the
metric and Health readers drift apart.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

import numpy as np
from execute_tools.health_checks import (
    CONTINUOUS_SAMPLES,
    ContinuousSamplesPayload,
    HealthView,
    register_view_provider,
)
from execute_tools.health_checks.schemas import HealthCheckContext


class TessPredictionViews:
    """Exposes the predicted rotation frequencies as the standard view."""

    provider_id: ClassVar[str] = "phyts_tess.prediction_views"
    capabilities: ClassVar[frozenset[str]] = frozenset({CONTINUOUS_SAMPLES})

    def materialize(
        self,
        capability_key: str,
        ctx: HealthCheckContext,
        config: dict[str, Any] | None = None,
    ) -> HealthView:
        payload = ctx.load_evaluation_payload()
        if not isinstance(payload, Mapping):
            raise TypeError(
                "PhyTS TESS evaluation payload must map 'gaia:sector' keys to scalar "
                f"rotation frequencies; got {type(payload).__name__}."
            )
        # An EMPTY deliverable decodes to an empty stream rather than raising:
        # the artifact WAS read, and the consuming check owns the emptiness
        # verdict. A value that is not a real number is a projection failure,
        # because "the deliverable's sample stream" cannot honestly contain it.
        samples = np.array(
            [float(payload[key]) for key in sorted(payload)], dtype=np.float64
        )
        return HealthView(
            capability_key=capability_key,
            provider_id=self.provider_id,
            payload=ContinuousSamplesPayload(samples=samples),
        )


register_view_provider(TessPredictionViews())

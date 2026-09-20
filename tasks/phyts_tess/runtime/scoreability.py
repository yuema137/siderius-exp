"""Task-owned scoreability contract for PhyTS TESS rotation deliverables.

This runs BEFORE the arithmetic and decides whether the deliverable is
scoreable at all. Its whole job is to turn "mysterious garbage score" into a
recorded refusal that names a reason — so every check below is total and
non-raising, reporting failures rather than throwing them.

What it can and cannot see: the framework hands it deliverable PATHS, not the
run's evaluation scope. So it validates the artifact's own integrity —
readable, right format, non-empty, every value a finite real number — and
leaves scope COVERAGE to the metric, which is the first place both halves are
in hand.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping

from execute_tools.evaluation_metric import (
    ScoreabilityContract,
    ScoreabilityFailure,
    ScoreabilityVerdict,
)

DELIVERABLE_FORMAT = "phyts_tess_rotation_predictions_v1"


class TessRotationScoreabilityContract(ScoreabilityContract):
    """Validate the JSON prediction map the TESS metrics consume."""

    contract_id: str = "phyts_tess_rotation_predictions"

    def check(self, deliverables: Mapping[int, str]) -> ScoreabilityVerdict:
        failures: list[ScoreabilityFailure] = []
        if not deliverables:
            failures.append(
                ScoreabilityFailure(
                    requirement="completeness",
                    detail="no in-scope deliverable was named for scoring",
                )
            )
        for identity, path in deliverables.items():
            failures.extend(self._check_one(int(identity), path))
        return ScoreabilityVerdict(
            contract_id=self.contract_id, failures=tuple(failures)
        )

    def _check_one(self, identity: int, path: str) -> list[ScoreabilityFailure]:
        def fail(requirement: str, detail: str) -> ScoreabilityFailure:
            return ScoreabilityFailure(
                requirement=requirement, input_identity=identity, detail=detail
            )

        if not os.path.isfile(path):
            return [fail("completeness", f"deliverable not found at {path!r}")]
        try:
            payload = json.loads(
                open(path, encoding="utf-8").read()  # noqa: SIM115 - closed by CPython refcount
            )
        except (OSError, ValueError) as exc:
            return [
                fail(
                    "completeness",
                    f"deliverable at {path!r} is not readable JSON: {exc}",
                )
            ]

        if not isinstance(payload, dict):
            return [fail("format", f"deliverable at {path!r} is not a JSON object")]
        if payload.get("format") != DELIVERABLE_FORMAT:
            return [
                fail(
                    "format",
                    f"deliverable at {path!r} declares format {payload.get('format')!r}, "
                    f"expected {DELIVERABLE_FORMAT!r}",
                )
            ]
        predictions = payload.get("predictions")
        if not isinstance(predictions, dict):
            return [
                fail("format", f"deliverable at {path!r} carries no predictions object")
            ]
        if not predictions:
            return [
                fail(
                    "completeness", f"deliverable at {path!r} carries zero predictions"
                )
            ]

        failures: list[ScoreabilityFailure] = []
        non_finite = 0
        first_bad: str | None = None
        for key, value in predictions.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                numeric = math.nan
            if not math.isfinite(numeric):
                non_finite += 1
                if first_bad is None:
                    first_bad = str(key)
        if non_finite:
            # Reported once with a count rather than once per curve: a model
            # that produced NaN usually produced it everywhere, and a verdict
            # carrying thousands of identical failures is unreadable.
            failures.append(
                fail(
                    "numerical",
                    f"{non_finite} of {len(predictions)} predictions in {path!r} are not "
                    f"finite rotation frequencies, first at key {first_bad!r}",
                )
            )
        return failures

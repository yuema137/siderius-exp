"""PhyTS TESS — the pack's own terminal metric implementations.

The primary metric is **R-squared, HIGHER is better**. RMSE and MAE are
declared beside it as OBSERVATIONAL secondaries: they are recorded and shown,
and they never order candidates.

**Why R-squared is the primary and not RMSE.** It is the quantity the PhyTS
baseline table reports for this task, so a candidate can be read against a
published reference without re-deriving anything. The consequence has to
travel with it: R-squared is normalized by the EVALUATION SET'S OWN total sum
of squares, so two values are comparable only when computed over the same
evaluation population. A number from a `portion < 1.0` round is not
comparable to a full-validation number, and neither is comparable to the
paper's test-set figure. RMSE, in physical cycles per day, is the quantity to
quote when an absolute error is wanted — which is exactly why it is kept.

All three read the generic scoring vocabulary — ``evaluation_payload``,
``task_scope``, ``data_dir`` — the three values the FRAMEWORK owns. Truth
comes from the evaluation scope, which is the run's ground-truth authority;
nothing here re-reads a parquet or invents a second source.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, ClassVar

from execute_tools.evaluation_metric import EvaluationMetric

#: Declared once. ``metric_r2.json`` names this id and the implementation may
#: not rewrite it.
TESS_PRIMARY_METRIC_ID = "r2"


def _paired(
    evaluation_payload: Any, task_scope: Any, metric_id: str
) -> list[tuple[float, float]]:
    """``[(truth, prediction), ...]`` over the scope, in scope order.

    A key the deliverable does not carry is a hard error, never an imputed
    value. Filling a missing prediction with the truth mean would flatter the
    score, and filling it with zero would punish it; both produce a plausible
    number computed from something the model never said. The scoreability
    contract screens the deliverable's own integrity; scope COVERAGE can only
    be checked here, because the contract is handed file paths and never sees
    the scope.
    """
    truth_of = getattr(task_scope, "truth", None)
    if not callable(truth_of):
        raise TypeError(
            f"{metric_id} needs the run's evaluation scope to read truth from; got "
            f"{type(task_scope).__name__}, which declares no `truth()`."
        )
    truth = truth_of()
    if not truth:
        raise ValueError(
            f"{metric_id} needs a non-empty evaluation scope — an empty scope is a "
            "caller wiring defect, not a scoreability case."
        )
    predictions = evaluation_payload or {}
    missing = [key for key in truth if key not in predictions]
    if missing:
        raise ValueError(
            f"{metric_id} cannot score a deliverable that covers "
            f"{len(truth) - len(missing)} of {len(truth)} scoped light curves; "
            f"first missing key {missing[0]!r}. A partial deliverable is a producer "
            "defect, not a metric decision."
        )
    return [(float(truth[key]), float(predictions[key])) for key in truth]


class TessRotationR2Metric(EvaluationMetric):
    """Coefficient of determination over the evaluation scope, HIGHER better.

    ``R2 = 1 - SSR/SST`` with ``SST`` computed from the evaluation scope's own
    target mean, so a model that predicts that mean for every curve scores
    exactly ``0.0`` and anything worse goes negative. There is no clipping:
    a negative R-squared is real information — the PhyTS mean baseline itself
    reports ``-0.017`` — and clamping it to zero would erase the distinction
    between "no better than the mean" and "actively worse".

    ``SST == 0`` is refused rather than returned as a number. It means every
    scoped curve shares one rotation frequency, for which the ratio is
    undefined; on the released data that needs a scope of identical-target
    rows, so it signals a scope-construction defect, not a bad model.
    """

    IMPLEMENTS: ClassVar[tuple[str, ...]] = (TESS_PRIMARY_METRIC_ID,)

    def _compute(
        self,
        deliverables: Mapping[int, str],
        /,
        *,
        evaluation_payload: Any,
        task_scope: Any,
        data_dir: str | None = None,
    ) -> tuple[float, list[float | None] | None, tuple[str, ...]]:
        pairs = _paired(evaluation_payload, task_scope, TESS_PRIMARY_METRIC_ID)
        mean = sum(truth for truth, _ in pairs) / len(pairs)
        total = sum((truth - mean) ** 2 for truth, _ in pairs)
        if total <= 0.0:
            raise ValueError(
                "r2 is undefined for an evaluation scope whose target variance is "
                f"zero ({len(pairs)} curves all at frot={mean}). This is a scope "
                "construction defect, not an unscoreable deliverable."
            )
        residual = sum((truth - prediction) ** 2 for truth, prediction in pairs)
        if not math.isfinite(residual):
            raise ValueError(
                "r2 received a non-finite residual sum; the deliverable carries "
                "predictions that are not finite numbers."
            )
        return 1.0 - residual / total, None, ()


class TessRotationRmseMetric(EvaluationMetric):
    """Root mean squared error in cycles per day, LOWER better.

    Observational. It is the absolute-error companion to R-squared: unlike
    R-squared it carries physical units and does not move when the evaluation
    population's variance changes, which makes it the right number to quote
    across two differently scoped rounds even though it never orders them.
    """

    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("rmse",)

    def _compute(
        self,
        deliverables: Mapping[int, str],
        /,
        *,
        evaluation_payload: Any,
        task_scope: Any,
        data_dir: str | None = None,
    ) -> tuple[float, list[float | None] | None, tuple[str, ...]]:
        pairs = _paired(evaluation_payload, task_scope, "rmse")
        mean_square = sum(
            (truth - prediction) ** 2 for truth, prediction in pairs
        ) / len(pairs)
        return math.sqrt(mean_square), None, ()


class TessRotationMaeMetric(EvaluationMetric):
    """Mean absolute error in cycles per day, LOWER better.

    Observational, and deliberately kept beside RMSE rather than instead of
    it. The released targets contain a small number of extreme values — train
    reaches ``frot = 17.45`` while validation stops near ``2.85`` — and the
    gap between MAE and RMSE is the cheapest available read on whether a
    candidate's error is spread evenly or concentrated in a few curves.
    """

    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("mae",)

    def _compute(
        self,
        deliverables: Mapping[int, str],
        /,
        *,
        evaluation_payload: Any,
        task_scope: Any,
        data_dir: str | None = None,
    ) -> tuple[float, list[float | None] | None, tuple[str, ...]]:
        pairs = _paired(evaluation_payload, task_scope, "mae")
        return (
            sum(abs(truth - prediction) for truth, prediction in pairs) / len(pairs),
            None,
            (),
        )

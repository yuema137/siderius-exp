"""Frozen two-decimal diagnostics for explicit historical prompt profiles."""

from typing import Any


def _fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def render_training_dynamics_line(diagnosis: Any, objective_kind: str | None = None) -> str:
    """ONE compact line of calibration-free training facts for one experiment.

    Example (planner, with the objective family label)::

        [focal] train 2.90->2.35 (decreasing, 5 ep) · val 2.95->2.62
        (decreasing; best ep 3, +0.07 after best) · gap +0.27 (comparable)

    ``objective_kind=None`` omits the ``[...]`` label — the REFLECTOR path.
    That is not an oversight: the reflector is given the ``TrainingDiagnosis``
    and nothing else (§3.8), because its ``actual_results`` already carries
    this round's ``final_loss`` and ``loss_history`` under the run's own loss
    config, and adding a second transport for the objective family would widen
    the frozen bridge surface to restate something already present.

    Degenerate states render explicitly rather than silently: a legacy record
    with no history says so, a non-finite history says so, and a gap that is
    not comparable says why. Rendering nothing would read to the LLM as "the
    training was unremarkable".
    """
    state = getattr(diagnosis, "state", None)
    if diagnosis is None or state == "absent":
        return "training dynamics: none recorded"
    if state == "invalid":
        return "training dynamics: invalid (non-finite)"

    label = f"[{objective_kind}] " if objective_kind else ""
    parts = []

    epochs = diagnosis.epochs_completed
    epoch_note = f", {epochs} ep" if epochs is not None else ""
    truncated = ", truncated" if diagnosis.truncated else ""
    parts.append(
        f"train {_fmt(diagnosis.train_first)}->{_fmt(diagnosis.train_last)} "
        f"({diagnosis.train_trend or 'n/a'}{epoch_note}{truncated})"
    )

    if diagnosis.validation_state == "present":
        best = diagnosis.best_validation_epoch
        best_note = f"; best ep {best}" if best is not None else ""
        degradation = diagnosis.final_vs_best_validation_degradation
        # F-SCANE-2. This suppression used to be an ACCIDENT: at one epoch the
        # derivation produced a literal `0.0`, which is falsy, so the LLM
        # happened never to see a fabricated "+0.0 after best". The record and
        # the operator report had no such accident protecting them. Since the
        # ruling landed the value is `None` under
        # `validation_degradation_verdict != "observed"`, so the same falsy
        # test now expresses the intended rule and these bytes are unchanged
        # in BOTH cases (a genuine observed 0.0 still renders nothing, exactly
        # as before).
        deg_note = f", +{_fmt(degradation)} after best" if degradation else ""
        parts.append(
            f"val {_fmt(diagnosis.validation_first)}->{_fmt(diagnosis.validation_last)} "
            f"({diagnosis.validation_trend or 'n/a'}{best_note}{deg_note})"
        )
    else:
        parts.append("val not recorded")

    gap = diagnosis.train_validation_gap_final
    if gap is None:
        reason = "not comparable" if diagnosis.comparability != "established" else "unavailable"
        parts.append(f"gap n/a ({reason})")
    else:
        parts.append(f"gap {gap:+.2f} (comparable)")

    return label + " · ".join(parts)

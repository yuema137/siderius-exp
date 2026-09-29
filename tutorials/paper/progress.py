"""Plot recorded Formal scores and Health evidence, without inventing scores."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Literal

from agent.schemas.hyperparam_tuning import HyperparamTuningOutput
from pydantic import BaseModel, ConfigDict


class ProgressPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    iteration: int
    exp_id: str
    model: str
    score: float | None
    metric: str | None
    direction: str | None
    validity: Literal["pass", "fail", "unknown"]
    status: str
    source: str


def read_progress(workspace: Path) -> list[ProgressPoint]:
    """Only Formal attempts; no Trial substitution and no legacy score fallback."""
    workspace = workspace.resolve()
    points = []
    seen = set()
    for path in sorted(workspace.rglob("run_output_*.json")):
        output = HyperparamTuningOutput.model_validate_json(path.read_text())
        parts = path.relative_to(workspace).parts
        iteration = next(
            (int(m[1]) for part in parts if (m := re.fullmatch(r"iter_(\d+)", part))),
            None,
        )
        if iteration is None:
            raise ValueError(f"cannot identify chain iteration from {path}")
        for record in output.all_records:
            if record.is_trial:
                continue
            identity = (iteration, record.exp_id)
            if identity in seen:
                raise ValueError(f"duplicate attempt identity: {identity}")
            seen.add(identity)
            metric = record.metric_result
            value = metric.scalar if metric else None
            score = float(value) if value is not None and math.isfinite(value) else None
            health = record.health_gate_results
            failed = any(
                h.check_passed is False or h.execution_status == "failed"
                for h in health
            )
            passed = bool(health) and all(
                h.check_passed is True and h.execution_status == "passed"
                for h in health
            )
            validity = (
                "fail"
                if failed or record.status != "success"
                else ("pass" if passed else "unknown")
            )
            points.append(
                ProgressPoint(
                    iteration=iteration,
                    exp_id=record.exp_id,
                    model=record.model_type,
                    score=score,
                    metric=metric.metric_id if metric else None,
                    direction=metric.direction if metric else None,
                    validity=validity,
                    status=record.status,
                    source=str(path),
                )
            )
    return sorted(points, key=lambda p: (p.iteration, p.exp_id))


def plot_progress(
    workspace: Path,
    output_dir: Path,
    *,
    title: str,
    expected_iterations: int | None = None,
):
    """Save a portable PNG/SVG/CSV and return the Matplotlib figure.

    Filled/open points mean measured Health PASS/FAIL (or failed execution), not
    retrospective scientific certification. Missing scores use a separate strip.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    from tutorials.paper.runner import ROOT, disjoint

    workspace, output_dir = workspace.resolve(), output_dir.resolve()
    if not workspace.is_dir():
        raise ValueError(f"no run workspace: {workspace}")
    if not disjoint(output_dir, ROOT) or output_dir == workspace:
        raise ValueError("save plots in an external project subdirectory")
    points = read_progress(workspace)
    metrics = {(p.metric, p.direction) for p in points if p.score is not None}
    if len(metrics) > 1:
        raise ValueError("do not combine different metrics or directions in one chart")
    iterations = {
        int(m[1])
        for p in workspace.glob("iter_*")
        if (m := re.fullmatch(r"iter_(\d+)", p.name))
    }
    iterations.update(p.iteration for p in points)
    if expected_iterations:
        iterations.update(range(1, expected_iterations + 1))
    if not iterations:
        raise ValueError("no recorded or expected search iterations")
    fig, (ax, missing_ax) = plt.subplots(
        2, 1, figsize=(9, 5), sharex=True, gridspec_kw={"height_ratios": [5, 1]}
    )
    color = "#2468a0"
    scored = [p for p in points if p.score is not None]
    if scored:
        # Running-best RAW Formal score, including hollow points, as in the paper.
        direction = next(iter(metrics))[1]
        best_x, best_y = [], []
        best = None
        for i in sorted(iterations):
            values = [p.score for p in scored if p.iteration == i]
            if values:
                candidate = (max if direction == "higher" else min)(values)
                best = (
                    candidate
                    if best is None
                    else (max if direction == "higher" else min)(best, candidate)
                )
            if best is not None:
                best_x.append(i)
                best_y.append(best)
        ax.plot(
            best_x,
            best_y,
            color=color,
            alpha=0.4,
            linewidth=1.5,
            label="Best recorded Formal score (includes invalid)",
        )
    for p in scored:
        if p.validity == "unknown":
            ax.scatter(p.iteration, p.score, color="gray", marker="x", s=65, zorder=3)
        else:
            ax.scatter(
                p.iteration,
                p.score,
                facecolors=color if p.validity == "pass" else "none",
                edgecolors=color,
                s=65,
                linewidths=1.7,
                zorder=3,
            )
    for i in sorted(iterations):
        unscored = [p for p in points if p.iteration == i and p.score is None]
        if unscored or not any(p.iteration == i for p in points):
            missing_ax.scatter(
                i, 0, facecolors="none", edgecolors=color, marker="o", s=45
            )
            label = f"{len(unscored)} unscored" if unscored else "no Formal record"
            missing_ax.annotate(
                label,
                (i, 0),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
    if not scored:
        ax.text(
            0.5,
            0.5,
            "No finite Formal scores recorded\nSee the unscored strip and run records",
            transform=ax.transAxes,
            ha="center",
        )
    metric, direction = next(iter(metrics)) if metrics else ("Formal score", None)
    ax.set_ylabel(f"{metric}" + (f" ({direction} is better)" if direction else ""))
    ax.set_title(title + " — score versus iteration")
    ax.grid(axis="y", alpha=0.2)
    handles = [
        Line2D(
            [],
            [],
            marker="o",
            color="none",
            markeredgecolor=color,
            markerfacecolor=color,
            label="Health PASS / successful attempt",
        ),
        Line2D(
            [],
            [],
            marker="o",
            color="none",
            markeredgecolor=color,
            markerfacecolor="none",
            label="Health FAIL / failed attempt",
        ),
        Line2D(
            [], [], marker="x", color="gray", linestyle="none", label="Health unknown"
        ),
    ]
    if scored:
        handles += [
            Line2D(
                [],
                [],
                color=color,
                alpha=0.4,
                label="Best raw Formal score (may be invalid)",
            )
        ]
    ax.legend(handles=handles, fontsize=8, loc="best")
    missing_ax.set_ylim(-0.6, 0.8)
    missing_ax.set_yticks([])
    missing_ax.set_ylabel("No score", fontsize=9)
    missing_ax.set_xlabel("Search iteration (not a tuning round)")
    missing_ax.set_xticks(sorted(iterations))
    missing_ax.set_xlim(min(iterations) - 0.35, max(iterations) + 0.35)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
        missing_ax.spines[spine].set_visible(False)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(output_dir / f"score-versus-iteration.{extension}", dpi=160)
    with (output_dir / "score-versus-iteration.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ProgressPoint.model_fields))
        writer.writeheader()
        writer.writerows(p.model_dump() for p in points)
    return fig

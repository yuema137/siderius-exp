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


def read_progress(
    workspace: Path, *, health_policy: Literal["required", "none"] = "required"
) -> list[ProgressPoint]:
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
                else (
                    "pass"
                    if passed or (health_policy == "none" and score is not None)
                    else "unknown"
                )
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
    health_policy: Literal["required", "none"] = "required",
):
    """Save a portable PNG/SVG/CSV and return the Matplotlib figure.

    Filled/open points mean measured Health PASS/FAIL (or failed execution), not
    retrospective scientific certification. Unscored attempts remain in the CSV.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    from tutorials.paper.runner import ROOT, disjoint

    workspace, output_dir = workspace.resolve(), output_dir.resolve()
    if not workspace.is_dir():
        raise ValueError(f"no run workspace: {workspace}")
    if not disjoint(output_dir, ROOT) or output_dir == workspace:
        raise ValueError("save plots in an external project subdirectory")
    points = read_progress(workspace, health_policy=health_policy)
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
    # Figure 4 typography, line/marker conventions and uncluttered single panel.
    # The tutorial changes only the horizontal coordinate to search iteration.
    style = {
        "font.family": "serif",
        "font.serif": ["DejaVu Serif"],
        "font.size": 8.5,
        "mathtext.fontset": "dejavuserif",
        "axes.labelsize": 8.5,
        "axes.titlesize": 9,
        "axes.linewidth": 0.7,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "legend.fontsize": 8,
        "legend.frameon": False,
    }
    with plt.rc_context(style):
        fig, ax = plt.subplots(figsize=(4.5, 2.8))
        fig.subplots_adjust(left=0.14, right=0.97, bottom=0.18, top=0.78)
        color = "#2468a0"
        scored = [p for p in points if p.score is not None]
        metric, direction = next(iter(metrics)) if metrics else ("r2", "higher")
        bounded_r2 = metric.lower() == "r2"
        x = [p.iteration for p in scored]
        y = [p.score for p in scored]
        ax.plot(x, y, color=color, lw=0.8, ls="--")
        best, frontier, improvements = None, [], []
        for point in scored:
            improves = best is None or (
                point.score > best if direction == "higher" else point.score < best
            )
            if improves:
                best = point.score
                if (not bounded_r2 or 0 <= best <= 1) and point.validity == "pass":
                    improvements.append((point.iteration, best))
            frontier.append(best)
        if x:
            tail = max(iterations)
            ax.plot(x + [tail], frontier + [frontier[-1]], color=color, lw=1.3)
        outside = []
        for point in scored:
            score = point.score
            clipped = min(1, max(0, score)) if bounded_r2 else score
            marker = ("v" if score < 0 else "^") if score != clipped else "o"
            if point.validity == "unknown":
                # Do not manufacture a Health verdict absent from native records.
                continue
            ax.scatter(
                point.iteration,
                clipped,
                marker=marker,
                facecolors=color if point.validity == "pass" else "white",
                edgecolors=color,
                s=12 if marker != "o" else 7.3,
                linewidths=0.7,
                clip_on=False,
                zorder=4,
            )
            if score != clipped:
                outside.append((point.iteration, score))
        if len(outside) == 1:
            iteration, score = outside[0]
            ax.annotate(
                f"{score:.3f}",
                (iteration, 0 if score < 0 else 1),
                xytext=(-3, 6 if score < 0 else -10),
                textcoords="offset points",
                ha="right",
                fontsize=8,
                color=color,
            )
        elif outside:
            below = sum(score < 0 for _, score in outside)
            if below:
                ax.text(
                    0.5,
                    0.12,
                    f"{below} scores < 0",
                    transform=ax.transAxes,
                    ha="center",
                    fontsize=8,
                    color=color,
                )
            if len(outside) > below:
                ax.text(
                    0.5,
                    0.83,
                    f"{len(outside) - below} scores > 1",
                    transform=ax.transAxes,
                    ha="center",
                    fontsize=8,
                    color=color,
                )
        if improvements:
            ax.scatter(
                *zip(*improvements),
                marker="*",
                s=38,
                c=color,
                edgecolors="white",
                linewidths=0.3,
                zorder=5,
            )
        ax.set_title(title, loc="left", pad=6)
        ax.set_ylabel(
            r"$R^2$"
            if bounded_r2
            else ("Denoising score" if metric == "tidmad_denoising_score" else metric)
        )
        ax.set_xlabel("Iteration")
        ax.set_xlim(0, max(iterations) + 0.15)
        ax.set_xticks(sorted(iterations))
        if bounded_r2:
            ax.set_ylim(0, 1)
            ax.set_yticks([0, 0.5, 1])
        ax.grid(False)
        handles = [
            Line2D([], [], color=".25", ls="--", lw=0.8, label="Formal result"),
            Line2D([], [], color=".25", lw=1.3, label="Current best"),
            Line2D([], [], color=".25", marker="*", ls="none", ms=6, label="New best"),
        ]
        fig.legend(
            handles=handles,
            loc="upper center",
            ncol=3,
            frameon=False,
            fontsize=8,
            columnspacing=1.2,
            handlelength=2,
            handletextpad=0.5,
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(output_dir / f"score-versus-iteration.{extension}", dpi=160)
    with (output_dir / "score-versus-iteration.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ProgressPoint.model_fields))
        writer.writeheader()
        writer.writerows(p.model_dump() for p in points)
    return fig

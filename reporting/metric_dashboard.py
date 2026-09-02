"""Build a self-contained metric-versus-iteration dashboard from run records."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ITERATION = re.compile(r"^iter_(\d+)$")
_REFUSING_ACTIONS = {"invalidate_round", "skip_iter", "skip_to_formal"}


@dataclass(frozen=True)
class Candidate:
    iteration: int
    score: float
    metric_id: str
    direction: str
    phase: str
    exp_id: str


@dataclass(frozen=True)
class TrajectoryPoint:
    iteration: int
    current: float
    best: float
    new_best: bool
    phase: str
    exp_id: str


def _iteration_from_path(path: Path, workspace: Path) -> int | None:
    for part in path.relative_to(workspace).parts:
        match = _ITERATION.fullmatch(part)
        if match:
            return int(match.group(1))
    return None


def _candidate(path: Path, workspace: Path) -> Candidate | None:
    if path.name.startswith("experiment_results_"):
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if payload.get("status") != "success" or payload.get("metric_refusal"):
        return None
    if payload.get("is_degenerate") is True:
        return None
    if str(payload.get("gate_action") or "continue") in _REFUSING_ACTIONS:
        return None
    metric = payload.get("metric_result")
    if not isinstance(metric, dict):
        return None
    scalar = metric.get("scalar")
    if not isinstance(scalar, (int, float)) or not math.isfinite(float(scalar)):
        return None
    metric_id = metric.get("metric_id")
    direction = metric.get("direction")
    if not isinstance(metric_id, str) or direction not in {"higher", "lower"}:
        return None
    iteration = _iteration_from_path(path, workspace)
    if iteration is None:
        return None
    is_trial = payload.get("is_trial")
    phase = (
        "trial" if is_trial is True else "formal" if is_trial is False else "unknown"
    )
    return Candidate(
        iteration=iteration,
        score=float(scalar),
        metric_id=metric_id,
        direction=direction,
        phase=phase,
        exp_id=str(payload.get("exp_id") or path.stem),
    )


def collect_panel(name: str, workspace: Path) -> dict[str, Any]:
    """Collect one primary-metric trajectory from a SIDERIUS workspace."""
    workspace = workspace.resolve()
    candidates = [
        candidate
        for path in workspace.glob("iter_*/**/records/iter_*/*.json")
        if (candidate := _candidate(path, workspace)) is not None
    ]
    identities = {(item.metric_id, item.direction) for item in candidates}
    if len(identities) > 1:
        raise ValueError(
            f"{name}: mixed primary metrics in one workspace: {identities}"
        )
    if identities:
        metric_id, direction = next(iter(identities))
    else:
        metric_id, direction = None, None

    by_iteration: dict[int, list[Candidate]] = {}
    for item in candidates:
        by_iteration.setdefault(item.iteration, []).append(item)

    points: list[TrajectoryPoint] = []
    incumbent: float | None = None
    for iteration in sorted(by_iteration):
        items = by_iteration[iteration]
        formal = [item for item in items if item.phase == "formal"]
        selectable = formal or items
        reverse = direction == "higher"
        current = sorted(selectable, key=lambda item: item.score, reverse=reverse)[0]
        new_best = incumbent is None or (
            current.score > incumbent if reverse else current.score < incumbent
        )
        if new_best:
            incumbent = current.score
        assert incumbent is not None
        points.append(
            TrajectoryPoint(
                iteration=iteration,
                current=current.score,
                best=incumbent,
                new_best=new_best,
                phase=current.phase,
                exp_id=current.exp_id,
            )
        )

    return {
        "name": name,
        "workspace": str(workspace),
        "metric_id": metric_id,
        "direction": direction,
        "points": [asdict(point) for point in points],
    }


def _coordinates(points: list[dict[str, Any]], width: int, height: int):
    left, right, top, bottom = 62, 22, 34, 50
    plot_width = width - left - right
    plot_height = height - top - bottom
    iterations = [int(point["iteration"]) for point in points]
    values = [float(point[key]) for point in points for key in ("current", "best")]
    x_min, x_max = min(iterations), max(iterations)
    if x_min == x_max:
        x_min, x_max = max(0, x_min - 1), x_max + 1
    y_min, y_max = min(values), max(values)
    if y_min == y_max:
        padding = max(abs(y_min) * 0.05, 0.05)
    else:
        padding = (y_max - y_min) * 0.12
    y_min, y_max = y_min - padding, y_max + padding

    def x(value: float) -> float:
        return left + (value - x_min) * plot_width / (x_max - x_min)

    def y(value: float) -> float:
        return top + (y_max - value) * plot_height / (y_max - y_min)

    return left, right, top, bottom, y_min, y_max, x, y


def _panel_svg(panel: dict[str, Any]) -> str:
    width, height = 620, 330
    points = list(panel.get("points") or [])
    name = html.escape(str(panel["name"]))
    metric = html.escape(str(panel.get("metric_id") or "primary metric pending"))
    direction = html.escape(str(panel.get("direction") or "unknown"))
    if not points:
        return (
            f'<section class="panel"><h2>{name}</h2>'
            f'<div class="metric">{metric} · {direction}</div>'
            '<div class="empty">No valid scored iteration yet.</div></section>'
        )

    left, right, top, bottom, y_min, y_max, x, y = _coordinates(points, width, height)
    plot_right, plot_bottom = width - right, height - bottom
    grid = []
    for index in range(5):
        fraction = index / 4
        y_value = y_max - fraction * (y_max - y_min)
        y_pos = top + fraction * (plot_bottom - top)
        grid.append(
            f'<line class="grid" x1="{left}" y1="{y_pos:.1f}" x2="{plot_right}" y2="{y_pos:.1f}"/>'
            f'<text class="tick" x="{left - 8}" y="{y_pos + 4:.1f}" text-anchor="end">{y_value:.4g}</text>'
        )
    x_ticks = sorted({int(point["iteration"]) for point in points})
    if len(x_ticks) > 8:
        stride = math.ceil(len(x_ticks) / 8)
        x_ticks = x_ticks[::stride]
    axes = [
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{plot_bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}"/>',
    ]
    for iteration in x_ticks:
        x_pos = x(iteration)
        axes.append(
            f'<text class="tick" x="{x_pos:.1f}" y="{plot_bottom + 22}" text-anchor="middle">{iteration}</text>'
        )
    current_line = " ".join(
        f"{x(point['iteration']):.1f},{y(point['current']):.1f}" for point in points
    )
    best_line = " ".join(
        f"{x(point['iteration']):.1f},{y(point['best']):.1f}" for point in points
    )
    marks = []
    for point in points:
        x_pos, y_pos = x(point["iteration"]), y(point["current"])
        title = html.escape(
            f"iteration {point['iteration']}: {point['current']:.8g} "
            f"({point['phase']}, {point['exp_id']})"
        )
        marks.append(
            f'<circle class="current-dot" cx="{x_pos:.1f}" cy="{y_pos:.1f}" r="4"><title>{title}</title></circle>'
        )
        if point["new_best"]:
            marks.append(
                f'<text class="star" x="{x_pos:.1f}" y="{y_pos - 10:.1f}" text-anchor="middle">★<title>New best: {title}</title></text>'
            )
    provisional = any(point["phase"] != "formal" for point in points)
    note = " · latest point provisional until Formal" if provisional else ""
    return f"""
<section class="panel">
  <h2>{name}</h2>
  <div class="metric">{metric} · {direction} is better{note}</div>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="{name} metric trajectory">
    {"".join(grid)}{"".join(axes)}
    <polyline class="best-line" points="{best_line}"/>
    <polyline class="current-line" points="{current_line}"/>
    {"".join(marks)}
    <text class="axis-label" x="{(left + plot_right) / 2:.1f}" y="{height - 10}" text-anchor="middle">Iteration</text>
  </svg>
  <div class="legend"><span class="solid"></span> cumulative best <span class="dashed"></span> current iteration <span class="legend-star">★</span> new best</div>
</section>"""


def render_dashboard(panels: list[dict[str, Any]], output: Path) -> None:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    panel_html = "\n".join(_panel_svg(panel) for panel in panels)
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SIDERIUS experiment trajectories</title>
<style>
:root{{--bg:#0b1020;--panel:#121a2d;--ink:#e8edf7;--muted:#91a0b8;--grid:#27344c;--best:#52d3a5;--current:#7da7ff;--star:#ffd166}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Inter,system-ui,sans-serif}}
main{{max-width:1500px;margin:auto;padding:28px}} h1{{margin:0 0 4px;font-size:25px}} .updated{{color:var(--muted);margin-bottom:22px}}
.panels{{display:grid;grid-template-columns:repeat(3,minmax(300px,1fr));gap:18px}} .panel{{background:var(--panel);border:1px solid #24314a;border-radius:14px;padding:18px;box-shadow:0 8px 30px #0004}}
h2{{margin:0;font-size:19px}} .metric{{color:var(--muted);margin:4px 0 8px}} svg{{width:100%;height:auto;overflow:visible}}
.grid{{stroke:var(--grid);stroke-width:1}} .axis{{stroke:#64748b;stroke-width:1.2}} .tick,.axis-label{{fill:var(--muted);font-size:12px}}
.best-line,.current-line{{fill:none;stroke-linejoin:round;stroke-linecap:round}} .best-line{{stroke:var(--best);stroke-width:3}} .current-line{{stroke:var(--current);stroke-width:2.5;stroke-dasharray:8 6}}
.current-dot{{fill:var(--current);stroke:var(--panel);stroke-width:2}} .star,.legend-star{{fill:var(--star);color:var(--star);font-size:18px}} .legend{{display:flex;gap:8px;align-items:center;color:var(--muted);font-size:12px}}
.solid,.dashed{{display:inline-block;width:28px;border-top:3px solid var(--best)}} .dashed{{border-top:2px dashed var(--current);margin-left:10px}} .empty{{height:300px;display:grid;place-items:center;color:var(--muted)}}
@media(max-width:1050px){{.panels{{grid-template-columns:1fr}}}} @media print{{:root{{--bg:#fff;--panel:#fff;--ink:#111;--muted:#555;--grid:#ddd}}.panel{{box-shadow:none}}}}
</style></head><body><main><h1>Scientific metric trajectories</h1><div class="updated">Generated {generated_at}. Solid = cumulative best; dashed = current iteration.</div><div class="panels">{panel_html}</div></main></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def _parse_task(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("task must use NAME=/absolute/workspace")
    return name, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect", help="collect workspace records")
    collect.add_argument("--task", action="append", type=_parse_task, required=True)
    collect.add_argument("--output", type=Path, required=True)
    render = subparsers.add_parser("render", help="render one or more receipts")
    render.add_argument("--receipt", action="append", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "collect":
        receipt = {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "panels": [collect_panel(name, path) for name, path in args.task],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return 0

    panels: list[dict[str, Any]] = []
    names: set[str] = set()
    for receipt_path in args.receipt:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("schema_version") != 1:
            raise ValueError(f"unsupported receipt schema: {receipt_path}")
        for panel in receipt["panels"]:
            if panel["name"] in names:
                raise ValueError(f"duplicate panel name: {panel['name']}")
            names.add(panel["name"])
            panels.append(panel)
    render_dashboard(panels, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

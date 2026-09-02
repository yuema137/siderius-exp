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


@dataclass(frozen=True)
class AxisScale:
    """Explicit y-axis limits for a panel."""

    minimum: float
    maximum: float
    tick_step: float

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (self.minimum, self.maximum, self.tick_step)
        ):
            raise ValueError("axis limits and tick step must be finite")
        if self.maximum <= self.minimum:
            raise ValueError("axis maximum must be greater than minimum")
        if self.tick_step <= 0:
            raise ValueError("axis tick step must be positive")

    def ticks(self) -> list[float]:
        count = round((self.maximum - self.minimum) / self.tick_step)
        if not math.isclose(
            self.minimum + count * self.tick_step,
            self.maximum,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("axis range must be an integer multiple of tick step")
        return [self.maximum - index * self.tick_step for index in range(count + 1)]

    @property
    def decimals(self) -> int:
        text = f"{self.tick_step:.10f}".rstrip("0")
        return len(text.partition(".")[2])


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


def _output_candidate(path: Path, workspace: Path) -> Candidate | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    metric = payload.get("metric_spec")
    if not isinstance(metric, dict):
        return None
    metric_id = metric.get("id")
    direction = metric.get("direction")
    if not isinstance(metric_id, str) or direction not in {"higher", "lower"}:
        return None
    iteration = _iteration_from_path(path, workspace)
    if iteration is None:
        return None
    for phase, score_key, exp_key in (
        ("formal", "best_valid_formal_denoising_score", "best_valid_formal_exp_id"),
        ("trial", "best_valid_trial_denoising_score", "best_valid_trial_exp_id"),
    ):
        scalar = payload.get(score_key)
        exp_id = payload.get(exp_key)
        if isinstance(scalar, (int, float)) and math.isfinite(float(scalar)) and exp_id:
            return Candidate(
                iteration=iteration,
                score=float(scalar),
                metric_id=metric_id,
                direction=direction,
                phase=phase,
                exp_id=str(exp_id),
            )
    return None


def collect_panel(name: str, workspace: Path) -> dict[str, Any]:
    """Collect one primary-metric trajectory from a SIDERIUS workspace."""
    workspace = workspace.resolve()
    output_candidates = [
        candidate
        for path in workspace.glob("iter_*/**/run_output_iter_*.json")
        if (candidate := _output_candidate(path, workspace)) is not None
    ]
    authoritative_iterations = {item.iteration for item in output_candidates}
    record_candidates = [
        candidate
        for path in workspace.glob("iter_*/**/records/iter_*/*.json")
        if (candidate := _candidate(path, workspace)) is not None
        and candidate.iteration not in authoritative_iterations
    ]
    candidates = [*output_candidates, *record_candidates]
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


def _coordinates(
    points: list[dict[str, Any]],
    width: int,
    height: int,
    scale: AxisScale | None = None,
):
    left, right, top, bottom = 62, 22, 34, 50
    plot_width = width - left - right
    plot_height = height - top - bottom
    iterations = [int(point["iteration"]) for point in points]
    values = [float(point[key]) for point in points for key in ("current", "best")]
    x_min, x_max = min(iterations), max(iterations)
    if x_min == x_max:
        x_min, x_max = max(0, x_min - 1), x_max + 1
    if scale is not None:
        y_min, y_max = scale.minimum, scale.maximum
    else:
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


def _axis_controls(scale: AxisScale) -> str:
    return f"""
  <div class="axis-controls">
    <label>Y min <input class="y-min" type="number" step="any" value="{scale.minimum:g}"></label>
    <label>Y max <input class="y-max" type="number" step="any" value="{scale.maximum:g}"></label>
    <label>Tick step <input class="y-step" type="number" step="any" value="{scale.tick_step:g}"></label>
    <button class="apply-axis" type="button">Apply</button>
    <span class="axis-error" role="status"></span>
  </div>"""


def _panel_svg(panel: dict[str, Any], panel_index: int) -> str:
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

    scale_payload = panel.get("y_axis")
    scale = AxisScale(**scale_payload) if isinstance(scale_payload, dict) else None
    left, right, top, bottom, y_min, y_max, x, y = _coordinates(
        points, width, height, scale
    )
    initial_scale = scale or AxisScale(y_min, y_max, (y_max - y_min) / 4)
    plot_right, plot_bottom = width - right, height - bottom
    grid = []
    y_ticks = (
        scale.ticks()
        if scale is not None
        else [y_max - index * (y_max - y_min) / 4 for index in range(5)]
    )
    decimals = scale.decimals if scale is not None else None
    for y_value in y_ticks:
        y_pos = y(y_value)
        tick_label = (
            f"{y_value:.{decimals}f}" if decimals is not None else f"{y_value:.4g}"
        )
        grid.append(
            f'<line class="grid" x1="{left}" y1="{y_pos:.1f}" x2="{plot_right}" y2="{y_pos:.1f}"/>'
            f'<text class="tick" x="{left - 8}" y="{y_pos + 4:.1f}" text-anchor="end">{tick_label}</text>'
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
    current_coordinates = [
        [x(point["iteration"]), float(point["current"])] for point in points
    ]
    best_coordinates = [
        [x(point["iteration"]), float(point["best"])] for point in points
    ]
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
            f'<circle class="current-dot" data-score="{point["current"]:.17g}" cx="{x_pos:.1f}" cy="{y_pos:.1f}" r="4"><title>{title}</title></circle>'
        )
        if point["new_best"]:
            marks.append(
                f'<text class="star" data-score="{point["current"]:.17g}" x="{x_pos:.1f}" y="{y_pos - 10:.1f}" text-anchor="middle">★<title>New best: {title}</title></text>'
            )
    provisional = any(point["phase"] != "formal" for point in points)
    note = " · latest point provisional until Formal" if provisional else ""
    return f"""
<section class="panel" data-interactive-axis="true" data-panel-index="{panel_index}">
  <h2>{name}</h2>
  <div class="metric">{metric} · {direction} is better{note}</div>
  {_axis_controls(initial_scale)}
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="{name} metric trajectory" data-top="{top}" data-bottom="{plot_bottom}">
    <defs><clipPath id="plot-clip-{panel_index}"><rect x="{left}" y="{top}" width="{plot_right - left}" height="{plot_bottom - top}"/></clipPath></defs>
    <g class="y-grid">{"".join(grid)}</g>{"".join(axes)}
    <g class="series" clip-path="url(#plot-clip-{panel_index})">
      <polyline class="best-line" data-values="{html.escape(json.dumps(best_coordinates), quote=True)}" points="{best_line}"/>
      <polyline class="current-line" data-values="{html.escape(json.dumps(current_coordinates), quote=True)}" points="{current_line}"/>
      {"".join(marks)}
    </g>
    <text class="axis-label" x="{(left + plot_right) / 2:.1f}" y="{height - 10}" text-anchor="middle">Iteration</text>
  </svg>
  <div class="legend"><span class="solid"></span> cumulative best <span class="dashed"></span> current iteration <span class="legend-star">★</span> new best</div>
</section>"""


def render_dashboard(panels: list[dict[str, Any]], output: Path) -> None:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    panel_html = "\n".join(
        _panel_svg(panel, index) for index, panel in enumerate(panels)
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="30">
<title>SIDERIUS experiment trajectories</title>
<style>
:root{{--bg:#0b1020;--panel:#121a2d;--ink:#e8edf7;--muted:#91a0b8;--grid:#27344c;--best:#52d3a5;--current:#7da7ff;--star:#ffd166}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Inter,system-ui,sans-serif}}
main{{max-width:1500px;margin:auto;padding:28px}} h1{{margin:0 0 4px;font-size:25px}} .updated{{color:var(--muted);margin-bottom:22px}}
.panels{{display:grid;grid-template-columns:repeat(3,minmax(300px,1fr));gap:18px}} .panel{{background:var(--panel);border:1px solid #24314a;border-radius:14px;padding:18px;box-shadow:0 8px 30px #0004}}
h2{{margin:0;font-size:19px}} .metric{{color:var(--muted);margin:4px 0 8px}} svg{{width:100%;height:auto;overflow:visible}}
.axis-controls{{display:flex;align-items:end;flex-wrap:wrap;gap:8px;margin:10px 0 2px}} .axis-controls label{{display:grid;gap:2px;color:var(--muted);font-size:12px}} .axis-controls input{{width:82px;border:1px solid #3a4964;border-radius:5px;background:#0b1020;color:var(--ink);padding:5px 6px}} .axis-controls button{{border:1px solid #4f6b95;border-radius:5px;background:#223451;color:var(--ink);padding:5px 11px;cursor:pointer}} .axis-error{{color:#ff8d8d;font-size:12px;min-height:18px}}
.grid{{stroke:var(--grid);stroke-width:1}} .axis{{stroke:#64748b;stroke-width:1.2}} .tick,.axis-label{{fill:var(--muted);font-size:12px}}
.best-line,.current-line{{fill:none;stroke-linejoin:round;stroke-linecap:round}} .best-line{{stroke:var(--best);stroke-width:3}} .current-line{{stroke:var(--current);stroke-width:2.5;stroke-dasharray:8 6}}
.current-dot{{fill:var(--current);stroke:var(--panel);stroke-width:2}} .star{{fill:var(--star);color:var(--star);font-size:18px}} .legend-star{{fill:var(--star);color:var(--star);font-size:21px}} .legend{{display:flex;gap:9px;align-items:center;color:var(--muted);font-size:15px}}
.solid,.dashed{{display:inline-block;width:28px;border-top:3px solid var(--best)}} .dashed{{border-top:2px dashed var(--current);margin-left:10px}} .empty{{height:300px;display:grid;place-items:center;color:var(--muted)}}
@media(max-width:1050px){{.panels{{grid-template-columns:1fr}}}} @media print{{:root{{--bg:#fff;--panel:#fff;--ink:#111;--muted:#555;--grid:#ddd}}.panel{{box-shadow:none}}}}
</style></head><body><main><h1>Scientific metric trajectories</h1><div class="updated">Generated {generated_at}. Solid = cumulative best; dashed = current iteration.</div><div class="panels">{panel_html}</div></main>
<script>
const svgNamespace = "http://www.w3.org/2000/svg";
function updateAxis(panel) {{
  const minimum = Number(panel.querySelector(".y-min").value);
  const maximum = Number(panel.querySelector(".y-max").value);
  const step = Number(panel.querySelector(".y-step").value);
  const error = panel.querySelector(".axis-error");
  if (![minimum, maximum, step].every(Number.isFinite) || maximum <= minimum || step <= 0) {{
    error.textContent = "Use finite values with max > min and step > 0.";
    return;
  }}
  const intervalCount = Math.round((maximum - minimum) / step);
  if (intervalCount < 1 || Math.abs(minimum + intervalCount * step - maximum) > 1e-9) {{
    error.textContent = "Range must be an integer multiple of tick step.";
    return;
  }}
  if (intervalCount > 40) {{
    error.textContent = "Choose a tick step that produces at most 40 intervals.";
    return;
  }}
  error.textContent = "";
  const svg = panel.querySelector("svg");
  const top = Number(svg.dataset.top);
  const bottom = Number(svg.dataset.bottom);
  const y = score => top + (maximum - score) * (bottom - top) / (maximum - minimum);
  const decimals = Math.min(8, (String(step).split(".")[1] || "").length);
  const grid = svg.querySelector(".y-grid");
  grid.replaceChildren();
  for (let index = 0; index <= intervalCount; index += 1) {{
    const value = maximum - index * step;
    const position = y(value);
    const line = document.createElementNS(svgNamespace, "line");
    line.setAttribute("class", "grid");
    line.setAttribute("x1", "62"); line.setAttribute("x2", "598");
    line.setAttribute("y1", position.toFixed(1)); line.setAttribute("y2", position.toFixed(1));
    const label = document.createElementNS(svgNamespace, "text");
    label.setAttribute("class", "tick"); label.setAttribute("x", "54");
    label.setAttribute("y", (position + 4).toFixed(1)); label.setAttribute("text-anchor", "end");
    label.textContent = value.toFixed(decimals);
    grid.append(line, label);
  }}
  svg.querySelectorAll("polyline[data-values]").forEach(line => {{
    const coordinates = JSON.parse(line.dataset.values);
    line.setAttribute("points", coordinates.map(([xValue, score]) => `${{xValue.toFixed(1)}},${{y(score).toFixed(1)}}`).join(" "));
  }});
  svg.querySelectorAll("circle[data-score]").forEach(dot => dot.setAttribute("cy", y(Number(dot.dataset.score)).toFixed(1)));
  svg.querySelectorAll("text.star[data-score]").forEach(star => star.setAttribute("y", (y(Number(star.dataset.score)) - 10).toFixed(1)));
}}
document.querySelectorAll(".panel[data-interactive-axis]").forEach(panel => {{
  panel.querySelector(".apply-axis").addEventListener("click", () => updateAxis(panel));
  panel.querySelectorAll(".axis-controls input").forEach(input => input.addEventListener("keydown", event => {{
    if (event.key === "Enter") updateAxis(panel);
  }}));
}});
</script></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def _parse_task(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("task must use NAME=/absolute/workspace")
    return name, Path(path)


def _parse_y_axis(value: str) -> tuple[str, AxisScale]:
    name, separator, limits = value.partition("=")
    parts = limits.split(":")
    if not separator or not name or len(parts) != 3:
        raise argparse.ArgumentTypeError("y-axis must use NAME=MIN:MAX:STEP")
    try:
        scale = AxisScale(*(float(part) for part in parts))
        scale.ticks()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return name, scale


def _apply_y_axes(
    panels: list[dict[str, Any]], configured: list[tuple[str, AxisScale]]
) -> None:
    by_name = {str(panel["name"]): panel for panel in panels}
    for name, scale in configured:
        if name not in by_name:
            raise ValueError(f"y-axis names unknown panel: {name}")
        by_name[name]["y_axis"] = asdict(scale)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect", help="collect workspace records")
    collect.add_argument("--task", action="append", type=_parse_task, required=True)
    collect.add_argument("--output", type=Path, required=True)
    render = subparsers.add_parser("render", help="render one or more receipts")
    render.add_argument("--receipt", action="append", type=Path, required=True)
    render.add_argument(
        "--y-axis",
        action="append",
        type=_parse_y_axis,
        default=[],
        help="fixed panel scale as NAME=MIN:MAX:STEP",
    )
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
    _apply_y_axes(panels, args.y_axis)
    render_dashboard(panels, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

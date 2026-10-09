# Static metric trajectory dashboard

`metric_dashboard.py` builds a self-contained HTML dashboard from SIDERIUS
experiment records. Generated receipts and HTML files are runtime artifacts;
keep them beside the workspaces rather than committing them to this repository.

Run from this checkout with its own environment. Replace `/runtime/task-a`
with your completed run workspace and choose your output paths:

```bash
uv sync --group dev --frozen
```

Collect one run, then render the receipt just created:

```bash
.venv/bin/python reporting/metric_dashboard.py collect \
  --task 'Task A=/runtime/task-a' \
  --output /runtime/task-a-receipt.json

.venv/bin/python reporting/metric_dashboard.py render \
  --receipt /runtime/task-a-receipt.json \
  --y-axis 'Task A=0.60:0.80:0.05' \
  --output /runtime/metric-dashboard.html
```

Open `/runtime/metric-dashboard.html` in a browser. The collector also accepts
multiple `NAME=/absolute/workspace` arguments. To combine separately collected
receipts, including ones from different machines, add another `--receipt` to
`render`; for example, `--receipt /runtime/task-b-receipt.json` only after that
file has been collected.

`--y-axis NAME=MIN:MAX:STEP` is optional and repeatable. It fixes a panel's
display range and tick spacing without embedding task-specific presentation
rules in the renderer. `NAME` must exactly match the panel name recorded by
the collector. Every populated panel also includes browser-side Y min, Y max,
and tick-step controls. `Apply` redraws the panel and retains the values across
the page's automatic refreshes. `Set as default` also retains them when the
dashboard is closed and reopened in the same browser. Browser settings do not
modify the receipt or any experiment artifact.

Only successful, finite primary-metric results that were not refused or
invalidated contribute points. Formal results take precedence within an
iteration; a Trial-only point is explicitly labelled provisional. The dashed
line is the selected current-iteration score, the solid line is the cumulative
best according to the metric's declared direction, and a star marks each new
best. The generated page reloads itself every 30 seconds when served over HTTP.

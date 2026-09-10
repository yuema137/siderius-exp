# Static metric trajectory dashboard

`metric_dashboard.py` builds a self-contained HTML dashboard from SIDERIUS
experiment records. Generated receipts and HTML files are runtime artifacts;
keep them beside the workspaces rather than committing them to this repository.

The collector accepts one or more `NAME=/absolute/workspace` arguments. The
renderer can combine receipts collected on different machines:

```bash
python reporting/metric_dashboard.py collect \
  --task 'Task A=/runtime/task-a' \
  --output /runtime/task-a-receipt.json

python reporting/metric_dashboard.py render \
  --receipt /runtime/task-a-receipt.json \
  --receipt /runtime/task-b-receipt.json \
  --y-axis 'Task A=0.60:0.80:0.05' \
  --output /runtime/metric-dashboard.html
```

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

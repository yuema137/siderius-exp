# TESS runner wrapper

[run.sh](run.sh) checks this checkout's Python environment and forwards arguments
to `tutorials.paper.runner`, the TESS tutorial runner. It is not the launcher for
TIDMAD, Project8 or LIGO.

For a first run, follow the [setup guide](../README.md) and use Quick B in your
copied notebook, or the exact generated `scripts/run-*.sh` command shown by
Quick A. That external script already selects your saved experiment JSON.

If you deliberately use this generic TESS wrapper, supply the external saved
experiment explicitly:

```bash
# EXP_CHECKOUT and TUTORIAL_HOME come from the setup guide.
# Run after Quick A has saved the default quick-demo-001 experiment.
bash "$EXP_CHECKOUT/tutorials/paper/scripts/run.sh" \
  --experiment "$TUTORIAL_HOME/experiments/tess_quick-demo-001.json"
# Add --launch only when ready for API calls and GPU work.
```

The command above previews only. Do not launch both this wrapper and Quick B
for the same experiment. Keep editable task/configuration files and outputs in
your external project; the wrapper itself stays unchanged in the source repo.

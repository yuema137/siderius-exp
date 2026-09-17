# TIDMAD main fixed-workflow configuration

This is a partial, non-launchable starting point for the planned one-band,
24-hour main experiment. `workflow.json` pins the continuous-regression task,
the experiment-owned `iclr_official_v1.json` for every current LLM role,
the exact 40,000-sample segment length, and the ordinary continuous-regression
task composition. Trial and Formal training strategy and portions are chosen by the agent
from the selected band's training files; Trial validation portion is also
agent-chosen. No frozen 10% parent pool applies to this experiment. Formal
evaluation scores the complete validation band regardless of training portion.
The shared configuration
sets a 100-iteration ceiling, three rounds, two epochs, 30/120-minute
Trial/Formal time-admission budgets, and 40-GiB VRAM limits. The workspace, band, and 24-hour
run deadline remain launch-owned.

`advice.json` is the one reviewed Full-arm advice artifact for every band.
It describes the paper's FC Net layers and the agreed time/VRAM context;
it does not require FC Net or forbid other model families. The no-prior arm
does not receive it. The Full treatment remains non-launchable until the
dedicated data-analysis binding and gate are qualified.

The future launcher will accept one treatment selector (`full` or `no-prior`).
Both treatments must use the same workflow and agent-parameter JSON. The
information-treatment manifest owns human advice and the dedicated data-analysis
state. `full` must refuse until the separately developed data-analysis component
is actually wired and validated; `no-prior` must pass explicit disabled states.
ML literature review stays enabled in both treatments. No run should be
started from this directory until those contracts and the launch gate are
completed and qualified.

The `main-fixed-no-prior.yaml` manifest declares `data_analysis: disabled`.
The treatment renderer forwards that state as `--no-data_analysis_enabled`;
it does not invent a second switch or alter the shared workflow JSON. The
Full arm still requires a band-scoped analysis binding and a qualified launch
gate before the workflow becomes effectful.

## NoPrior preparation check

`preflight.py` resolves a single NoPrior unit without starting an experiment.
It checks the repository, dependency, installed package and framework checkout
revisions; requires a fresh external workspace; and verifies that the selected
band's data directory contains only its training/validation HDF5 pairs and the
approved `segment_anchors.json`. Each HDF5 byte stream is checked against the
existing `campaigns/tidmad_gold/inputs/q3_data_manifest.sha256`. Its JSON output
records the resolved chain arguments and input digests. It does not write a
workspace or launch a chain.

From the exact exp checkout after installing its frozen environment:

```bash
.venv/bin/python -m experiments.tidmad.main_fixed_workflow.preflight \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 \
  --data_dir /path/to/isolated/band-0-3-data \
  --workspace /path/to/new/no-prior-0-3-workspace \
  --run_name YOUR_REVIEWED_RUN_NAME
```

The root `SIDERIUS_REVISION` currently differs from the dependency revision in
`pyproject.toml` and `uv.lock`, so this check intentionally refuses until one
compatible revision is frozen across all three. A separate main launcher,
24-hour deadline, H100 qualification and real one-band smoke are still required
before any paper run.

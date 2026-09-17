# TIDMAD main fixed-workflow configuration

This directory contains the NoPrior launch path for the planned one-band,
24-hour main experiment. The paper run is not qualified yet: real H100 data,
the short smoke, candidate replay, and the final launch checkpoint remain open.
`workflow.json` pins the continuous-regression task,
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

The eventual shared launcher will accept one treatment selector (`full` or
`no-prior`). Both treatments must use the same workflow and agent-parameter JSON. The
information-treatment manifest owns human advice and the dedicated data-analysis
state. `full` remains unavailable until the separately developed data-analysis
component is wired and validated. The current `launch.sh` accepts only NoPrior
and passes explicit disabled states. ML literature review remains enabled.

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

The root `SIDERIUS_REVISION`, `pyproject.toml`, `uv.lock`, installed package and
isolated framework checkout must all match the selected exact commit. The
preparation branch aligns these to `bb9c8cb40fd14956c1608557254104cd5b3f32bb`
(the reviewed generic chain fix on infra master `28b83f8`).

## NoPrior unit control

`launch.sh` previews a single unit by default. Supply an external parent
directory for that unit; the chain workspace is its `workspace/` child. For an
effectful launch, the parent of the unit directory must already be the mounted
persistent work volume, so a missing work disk cannot create a new clock on
the VM boot disk:

```bash
bash experiments/tidmad/main_fixed_workflow/launch.sh \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 \
  --data_dir /path/to/isolated/band-0-3-data \
  --unit-dir /path/to/new/no-prior-0-3-unit \
  --run_name YOUR_REVIEWED_RUN_NAME
```

The preview checks pins, treatment, configuration and all selected input
checksums; it creates no unit files. Adding `--launch` starts or resumes the
effectful chain. Before the first effect, it also requires exactly one H100
and checks the presence of API keys for enabled LLM providers in the same
process. A trusted external secret injector or mode-600 service environment
file must supply those keys; values never enter receipts.

The first launch writes `launch.json` exactly once, with the resolved command,
input identities, UTC start and the start plus 24 hours as deadline. Restart
revalidates the current inputs against that receipt and resumes the same chain
workspace without extending the deadline. The supervisor appends events and
chain output below the unit directory and kills the chain process group at the
deadline. `systemd/tidmad-no-prior@.service` is the reboot/restart template;
replace `@NO_PRIOR_USER@`, `@NO_PRIOR_GROUP@`, and `@UNIT_MOUNT@` with a dedicated
unprivileged account and the mounted work-volume path before installation.
Each `%i` needs its own mode-600
`/etc/tidmad-no-prior/%i.env` declaring `EXP_CHECKOUT`, `SIDERIUS_CHECKOUT`,
`BAND`, `DATA_DIR`, `UNIT_DIR`, `RUN_NAME`, and the required provider key. The
service must be enabled for boot recovery. No unit is installed or launched by
this repository change.

The ordinary output-retention default removes large per-sample deliverables
after scoring and Health while retaining checkpoints and certified model
artifacts. The main experiment still needs a demonstrated offline candidate
replay and scorer/Health parity check before paper-run authorization.

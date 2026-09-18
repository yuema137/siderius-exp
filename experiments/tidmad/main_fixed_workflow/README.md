# TIDMAD main fixed-workflow configuration

This directory contains the NoPrior launch path for the planned one-band,
24-hour main experiment. The paper run is not qualified yet: real H100 data,
the short smoke, candidate replay, and the final launch checkpoint remain open.
`workflow.json` pins the continuous-regression task,
the experiment-owned `iclr_official_v1.json` for every current LLM role,
the exact 40,000-sample segment length, and the existing frozen-pool
continuous-regression composition. It selects the same content-pinned 20 of
200 PSD segments per training file as the deployed single-band CLI baseline.
Trial chooses a smaller sample from that parent. Formal uses the complete
parent (`formal_portion=0.1`, `formal_train_portion=1.0`); its portion is
operator-owned because the frozen-pool capability refuses a different Formal
parent. Trial validation portion remains agent-chosen. Formal evaluation
scores the complete validation band. This changes the experiment binding,
not any file in `tasks/tidmad`.
The shared configuration
sets a 100-iteration ceiling, three rounds, two epochs, 30/120-minute
Trial/Formal time-admission budgets, and 40-GiB VRAM limits. The workspace, band, and 24-hour
run deadline remain launch-owned.
The phase runtime watchdog is explicitly disabled (`--no-runtime_watchdog`)
to avoid terminating candidates based on estimated phase duration. The
supervisor's fixed 24-hour deadline and disk-space guard remain active.

`advice.json` is the one reviewed Full-arm advice artifact for every band.
It describes the paper's FC Net layers and the agreed time/VRAM context;
it does not require FC Net or forbid other model families. The no-prior arm
does not receive it. The Full treatment (Data Analysis plus human advice)
has not been discussed and finalized for the main run; this preparation
qualifies NoPrior only.

The eventual shared launcher will accept one treatment selector (`full` or
`no-prior`). Both treatments must use the same workflow and agent-parameter JSON. The
information-treatment manifest owns human advice and the dedicated data-analysis
state. `full` remains unavailable until its scientific configuration and
launch binding are decided and qualified. The current `launch.sh` accepts only NoPrior
and passes explicit disabled states. ML literature review remains enabled.

The `main-fixed-no-prior.yaml` manifest declares `data_analysis: disabled`.
The treatment renderer forwards that state as `--no-data_analysis_enabled`;
it does not invent a second switch or alter the shared workflow JSON. The
Full arm still requires a separate decision and a qualified band-scoped
analysis binding before any effectful launch.

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
isolated framework checkout must all match the selected exact commit.
The current pin is `270098f00fd100300b396c56a9af0668b559c974`. Composed
inference now passes the resolved model input dtype to the execution adapter.
Before training, its resource worker also checks one real validation input
through that adapter. This catches input-interface failures early; it does not
replace scoring or Health, or guarantee that every validation sample succeeds.

## NoPrior unit control

`launch.sh` previews a single unit by default. Supply an external parent
directory for that unit; the chain workspace is its `workspace/` child. For an
effectful launch, the parent of the unit directory must already be the mounted
persistent work volume, so a missing work disk cannot create a new clock on
the VM boot disk. The unit directory is private to the service account:

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
after scoring and Health. The tuner also removes raw training `.pth` files
after each complete iteration by default, while retaining every scored
certified `.pt` candidate. The main experiment still needs a demonstrated
offline candidate replay and scorer/Health parity check before paper-run
authorization.

## Retained-artifact backup and disk guard

`backup.sh` is an exp-owned, independent service. Its systemd oneshot and
10-minute timer are `systemd/tidmad-no-prior-backup@.*`; the separate 2-minute
free-space guard is `systemd/tidmad-no-prior-disk-guard@.*`. Install both pairs
with the same `@UNIT_MOUNT@` replacement as the workflow service, then enable
both timers for each band. Both wait until immutable `launch.json` exists. Run
one manual backup service invocation after launch to verify an actual upload
and receipt before relying on the timer.

Each instance needs a separate mode-600
`/etc/tidmad-no-prior/%i-backup.env` with `BACKUP_BUCKET`, `BACKUP_PREFIX`,
`BACKUP_ENDPOINT`, `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`, and
`AWS_SECRET_ACCESS_KEY`; the
ordinary `%i.env` still owns `UNIT_DIR` and `EXP_CHECKOUT`. Install AWS CLI
1.46.1 in a separate `/opt/tidmad-no-prior/awscli-venv`; the backup service's
PATH selects it without changing the frozen exp or infra environments. Grant
the instance's writer group only `storage.uploader` and
`storage.object-lister` for its own versioned bucket; these roles permit sync
and multipart upload without object read or delete. Never put S3 keys in a
repository or the workflow's LLM environment file.

The sync includes certified `.pt` weights, model artifact documents, configs,
source, scoring and Health receipts. It excludes retired training `.pth`,
denoised HDF5, environment files, temporary files and logs, never uses S3 deletion, and appends
local `backup_receipts.jsonl` after each attempt. Versioning protects earlier
object revisions when a JSON record grows. If the mounted work volume falls
below 50 GiB free, the backup service first stops that instance's workflow
service and writes a `low_space_stop` receipt; the 24-hour deadline remains
unchanged. Operators must inspect disk space and the receipt before resuming.

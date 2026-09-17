# TIDMAD coding-agent baseline

This folder prepares coding-agent baselines for Codex and Claude Code. The
existing four-band, one-clock package is a diagnostic pilot; the planned main
experiment gives each agent one band and a separate 24-hour clock. Neither
mode defines a second version of TIDMAD. The builder derives both an agent-visible
view and an evaluator-private snapshot from the same tracked
[`tasks/tidmad`](../../tasks/tidmad/) authority. Both machines receive the same
bundle bytes and the same operator-approved kickoff file, `task.md`.

The bundle also requires one explicit information treatment. The treatment
records whether the run receives human advice and whether optional workflow
modules apply. Advice is either absent by declaration or copied as one
checksum-verified `advice.json`; it is never inferred from nearby files.

The baseline adds no research workflow, resource monitor or general preflight
to either CLI. The surrounding scripts only keep the clock honest, restart a
CLI that exits early, protect the hidden evaluation truth, retain validly
scored candidates, back them up, and collect the final result.

## What the agent can see

- the sanitized `tasks/tidmad` view and shared `task.md`;
- the labelled training files selected by the frozen unit: all 20 for the
  diagnostic pilot, or only the chosen band's 4, 6, 5, or 5 files;
- its own 1 TiB local workspace and outbound internet;
- the fixed `tidmad-score` command.

It cannot read official validation inputs or truth, the private scorer assets,
backup credentials, the other agent's machine, or any SIDERIUS campaign output.
Each of the four bands is an independent search: architectures may differ.
Every candidate that receives an eligible complete-band score is retained.

## Operator-owned evaluation contract

Candidate evaluation covers every official validation file in the requested
band: files 0--3, 4--9, 10--14 or 15--19. The diagnostic pilot's final
evaluation composes four winners over all 20 files. A main-experiment unit
finalizes only its selected band and records a sparse 20-file vector; four
independent accepted units are needed before any overall composition.
Metric aggregation, band membership,
Health eligibility and evaluation scope are scientific protocol decisions.
They must not be narrowed, sampled or otherwise changed for runtime or cost
reasons without explicit operator approval.

## Before renting GPUs

1. Review the tracked [`task.md`](task.md); changing it creates a new frozen
   experiment package and run identity.
2. Choose and review one treatment from
   [`experiments/tidmad/information_treatments`](../../experiments/tidmad/information_treatments/).
3. Build one archive and copy those exact bytes to both machines.
4. Prepare a distinct agent API credential and append-only backup credential
   for each machine.
5. Create two isolated Nebius VMs only after the archive is ready.

From this checkout, using its own environment and the exact pinned SIDERIUS
checkout:

```bash
.venv/bin/python -m \
  deployments.tidmad_coding_agent_baseline.tools.build_bundle \
  --task-md deployments/tidmad_coding_agent_baseline/task.md \
  --information-treatment \
    experiments/tidmad/information_treatments/prerelease-without-advice.yaml \
  --siderius-checkout /path/to/exact-pinned-SIDERIUS \
  --output /safe/bundles/tidmad-coding-agent-baseline.tar.gz
sha256sum /safe/bundles/tidmad-coding-agent-baseline.tar.gz
```

Use the same reported archive hash on both machines. The builder refuses a
dirty TIDMAD task tree or a SIDERIUS checkout that differs from
[`SIDERIUS_REVISION`](../../SIDERIUS_REVISION).

The command above builds the explicit advice-off condition. To build the
otherwise identical advice-on condition, change only the treatment path to
`experiments/tidmad/information_treatments/prerelease-with-advice.yaml`.
The resulting `treatment.json` records the selected arm and advice identity;
the public task-view hash remains the same. Codex and Claude must receive the
same archive bytes when they belong to the same arm.

The command above is for the four-band diagnostic pilot. For a **single-band
main-experiment package**, select one band explicitly, use
`task-main-band.md` and `main-cli-no-advice.yaml`, and build the same archive
bytes for Codex and Claude in that band:

```bash
.venv/bin/python -m \
  deployments.tidmad_coding_agent_baseline.tools.build_bundle \
  --task-md deployments/tidmad_coding_agent_baseline/task-main-band.md \
  --information-treatment \
    experiments/tidmad/information_treatments/main-cli-no-advice.yaml \
  --siderius-checkout /path/to/exact-pinned-SIDERIUS \
  --band 4-9 \
  --output /safe/bundles/tidmad-band-4-9.tar.gz
```

Replace `4-9` with the selected band and use a distinct run/workspace for
each band. This package carries only that band's training/validation checksum
entries and evaluator scopes. It does not by itself authorize a main run:
freeze the remaining launch inputs and complete the H100 drill first.

## VM contract

Each condition receives one Nebius H100 VM, 16 vCPU, 200 GB RAM and one
condition-local 1 TiB persistent disk. Do not mount shared storage. Use a
different API key, backup credential and create-only object-storage prefix on
each VM. Neither agent credential may reach the backup destination or the
other condition.

The agent works for exactly 24 hours. The systemd service has a 24-hour,
15-minute ceiling; the final 15 minutes are collection-only. The first deadline
record is create-once and survives service and VM restarts.

## Runtime layout

```text
/work/input/       frozen bundle input; read-only to the agent
/work/harness/     installed deployment tools and units
/work/agent/       agent-owned source and environments
/work/state/       deadline, invocation receipts and retained candidates
/work/submission/  final collection
/work/logs/        structured CLI output
/data/             public training plus evaluator-private validation views
```

Every validly scored complete-band candidate is retained below
`/var/lib/tidmad-baseline/candidates/<band>/<candidate-id>/`. That tree is
readable but not writable by the agent. A completed identity cannot be
replaced. Temporary denoised HDF5 files are deleted only after score and
candidate publication succeed.

## Install one VM

Copy the archive and the raw files named by its `data_manifest.sha256` to
root-only staging directories on the VM's local disk: 40 files for a diagnostic
pilot, or 8/12/10/10 training-plus-validation files for one selected band.
In particular, `/data/raw-staging` must not be readable by
`baseline-agent`. Extract the archive into a root-only directory, then run:

```bash
sudo bash tidmad-coding-agent-baseline/harness/machine/install_vm.sh \
  codex /root/tidmad-coding-agent-baseline
# Use "claude" on the other machine.

sudo /opt/tidmad-evaluator/venv/bin/python -I -m \
  baseline_harness.prepare_data \
  --source-root /data/raw-staging \
  --training-pool-manifest /opt/tidmad-evaluator/assets/task_snapshot/tasks/tidmad/declared/frozen_training_pool_v1.json \
  --private-group baseline-evaluator
```

For the main single-band condition this flag is required: it exposes only the
frozen 20/200 training PSD segments per file while retaining the verified full
raw staging source in a root-only directory. Do not omit it when staging a
main run. Legacy diagnostic staging without the flag remains unchanged.
Data preparation verifies every selected repository-owned checksum. The
selected band's bounded training files remain available for fitting. Validation inputs
and targets, plus
the exact frequency/anchor/scorer assets, remain evaluator-only. Evaluator
inference copies omit release-identity attributes such as the original file
number.

Put `BASELINE_PRODUCT` and the product API key in
`/etc/tidmad-baseline/agent.env`, mode `0640`, owned by
`root:baseline-agent`. Put the separate object-storage credential plus
`BACKUP_BUCKET` and the condition-unique `BACKUP_PREFIX` in
`/etc/tidmad-baseline/backup.env`, mode `0640`, owned by
`root:baseline-backup`. Never place either file in a repository or bundle.

Install the actual Codex or Claude CLI globally. Do not start the experiment
clock yet. The machine must also provide Python 3.12 and an operator-selected
AWS CLI version. The installer records both versions and deliberately refuses
to fetch an unpinned latest AWS CLI during installation. Set
`BASELINE_PYTHON_BIN` only when Python 3.12 is installed under another name.
The installer sets the non-interactive systemd process's HOME, temporary and
cache directories below `/baseline/agent/` and puts the user-installed product
CLI directory on PATH. This is explicit runtime configuration; it does not
copy, inspect or replace either product's authenticated account state.

## Required H100 drill

Before the formal clock starts, each product must actually write a file, run
Python, see the GPU, fetch a public page, install a small package, save and
reload a checkpoint, report the served model and exit without a prompt. Then:

1. terminate the CLI during a second invocation and observe continuation;
2. restart the service and prove the deadline bytes are unchanged;
3. reboot the VM and prove the boot ID changed, the deadline bytes did not, and
   the enabled service returned;
4. run `tools/clear_workspace.py`, which removes and recreates only `agent`,
   `state`, `submission` and `logs`;
5. re-verify the frozen input manifest and schedule one common UTC start.

Run the smoke as `baseline-agent` with that machine's agent environment loaded:

```bash
sudo -u baseline-agent bash -lc '
  set -a
  source /etc/tidmad-baseline/agent.env
  exec /work/harness/venv/bin/python -m baseline_harness.smoke_test \
    --product codex \
    --root /work/agent/smoke \
    --expected-model-regex "gpt-5[.]6-sol"
'
```

Use `--product claude` and an exact Opus 5 response-identity pattern on the
other VM. The smoke checks the flags exposed by the installed CLI and records
the actual CLI version and structured-log hash. A requested alias is not
enough: do not start if the returned model identity does not match.

For the reboot drill, install a temporary schedule, allow an invocation to
start, record the before receipt, and reboot:

```bash
sudo /work/harness/venv/bin/python -m baseline_harness.schedule \
  --scheduled-start-epoch "$DRILL_START_EPOCH"
sudo /work/harness/venv/bin/python -m baseline_harness.reboot_probe before
sudo reboot
# After reconnecting:
sudo /work/harness/venv/bin/python -m baseline_harness.reboot_probe after
```

The after check requires a new boot ID, byte-identical deadline, an active
agent service, and an active absolute stop timer. Stop and disable the drill
units before clearing. Then run the exact cleanup; it refuses while they are
active:

```bash
sudo systemctl stop tidmad-coding-agent.service \
  tidmad-baseline-start.timer tidmad-baseline-stop.timer \
  tidmad-baseline-finalize.timer tidmad-baseline-backup.timer
sudo systemctl disable tidmad-coding-agent.service \
  tidmad-baseline-start.timer tidmad-baseline-stop.timer \
  tidmad-baseline-finalize.timer tidmad-baseline-backup.timer
sudo /work/harness/venv/bin/python -m baseline_harness.clear_workspace \
  --owner baseline-agent --group baseline-results
```

Finally choose one UTC epoch at least several minutes ahead and run the same
schedule command on both VMs. The persisted start receipts prove the requested
barrier and actual start times; the deadline is written once and never
recomputed after restart.

## Scoring and submission

The scorer owns the canonical TIDMAD formula. During search the agent may name
only a candidate below `/work/agent` and a band permitted by its frozen unit.
The evaluator
selects every official validation file in that band, snapshots the candidate,
runs its frozen model through evaluator-owned segmentation and output assembly,
applies scoring and Health across the complete band, and retains eligible
candidates. It does not expose an official-final scoring command.

The inference identity receives execute-only traversal through the retained
state root to its own root-created session directory. It is not a member of the
results group and cannot list or read retained sibling state.

```bash
tidmad-score candidate \
  --band 0-3 \
  --candidate-id my-candidate-001 \
  --candidate-source /work/agent/candidates/my-candidate-001
```

Candidate source contains `model.py` (or `model/`), `architecture.json`,
`train_config.json`, `weights.pth`, and an exported TorchScript `model.pt`.
Evaluator code alone reads HDF5 files, slices fixed raw 40,000-sample segments,
converts the model output with the frozen task-owned rule, and writes
deliverables. The diagnostic contract accepts categorical logits; a
single-band main unit requires continuous regression. The model runs under a root-owned,
network-disabled inference identity and receives only segment tensors. At the
immutable deadline the finalizer stops the
agent, selects the best retained complete-band candidate for each required
band, replays it over that band's full validation scope, and packages the
result. A diagnostic pilot requires four winners; a single-band unit requires
one and emits a sparse 20-file vector. A missing required band remains a
partial submission; the finalizer never invents scores.

The final `task.md`, cloud provisioning commands, model identity patterns and
actual drill receipts remain launch-time inputs. A local test is not evidence
that the H100 drill ran. Run the focused local checks with:

```bash
.venv/bin/ruff check deployments/tidmad_coding_agent_baseline \
  tests/deployments/tidmad_coding_agent_baseline
.venv/bin/pytest -q tests/deployments/tidmad_coding_agent_baseline
```

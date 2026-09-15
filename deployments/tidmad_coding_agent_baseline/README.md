# TIDMAD coding-agent baseline

This folder prepares two independent 24-hour baselines: one gives the TIDMAD
problem to Codex, and the other gives the same problem to Claude Code. It does
not define a second version of TIDMAD. Both machines receive a byte-for-byte
snapshot of the existing [`tasks/tidmad`](../../tasks/tidmad/) package and the
same operator-approved kickoff file, `task.md`.

The baseline adds no research workflow, resource monitor or general preflight
to either CLI. The surrounding scripts only keep the clock honest, restart a
CLI that exits early, protect the hidden evaluation truth, retain validly
scored candidates, back them up, and collect the final result.

## What the agent can see

- the frozen `tasks/tidmad` snapshot and shared `task.md`;
- all 20 labelled training files;
- validation inputs with `channel0002` removed;
- its own 1 TiB local workspace and outbound internet;
- the fixed `tidmad-score` command.

It cannot read validation truth, the evaluator environment, backup credentials,
the other agent's machine, or any SIDERIUS campaign output. Each of the four
bands is an independent search: architectures may differ, and an accidental
match is allowed. Every candidate that receives a valid score is retained.

## Before renting GPUs

1. Finish and approve one `task.md` outside the repository.
2. Build one archive and copy those exact bytes to both machines.
3. Prepare a distinct agent API credential and append-only backup credential
   for each machine.
4. Create two isolated Nebius VMs only after the archive is ready.

From this checkout, using its own environment and the exact pinned SIDERIUS
checkout:

```bash
.venv/bin/python -m \
  deployments.tidmad_coding_agent_baseline.tools.build_bundle \
  --task-md /safe/operator/task.md \
  --siderius-checkout /path/to/exact-pinned-SIDERIUS \
  --output /safe/bundles/tidmad-coding-agent-baseline.tar.gz
sha256sum /safe/bundles/tidmad-coding-agent-baseline.tar.gz
```

Use the same reported archive hash on both machines. The builder refuses a
dirty TIDMAD task tree or a SIDERIUS checkout that differs from
[`SIDERIUS_REVISION`](../../SIDERIUS_REVISION).

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
/data/             machine-local public inputs and private validation truth
```

Every validly scored candidate is retained below
`/var/lib/tidmad-baseline/candidates/<band>/<candidate-id>/`. That tree is
readable but not writable by the agent. A completed identity cannot be
replaced. Temporary denoised HDF5 files are deleted only after score and
candidate publication succeed.

## Install one VM

Copy the archive and the 40 raw files to root-only staging directories on the
VM's local disk. In particular, `/data/raw-staging` must not be readable by
`baseline-agent`. Extract the archive into a root-only directory, then run:

```bash
sudo bash tidmad-coding-agent-baseline/harness/machine/install_vm.sh \
  codex /root/tidmad-coding-agent-baseline
# Use "claude" on the other machine.

sudo /opt/tidmad-evaluator/venv/bin/python -I -m \
  baseline_harness.prepare_data \
  --source-root /data/raw-staging \
  --private-group baseline-evaluator
```

Data preparation verifies the 40 repository-owned checksums. Training files
remain labelled. The public validation copies contain only `channel0001`; the
unchanged validation files containing `channel0002` are readable only by the
fixed evaluator.

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
  tidmad-baseline-start.timer tidmad-baseline-stop.timer
sudo systemctl disable tidmad-coding-agent.service \
  tidmad-baseline-start.timer tidmad-baseline-stop.timer
sudo /work/harness/venv/bin/python -m baseline_harness.clear_workspace \
  --owner baseline-agent --group baseline-results
```

Finally choose one UTC epoch at least several minutes ahead and run the same
schedule command on both VMs. The persisted start receipts prove the requested
barrier and actual start times; the deadline is written once and never
recomputed after restart.

## Scoring and submission

The scorer owns the canonical TIDMAD formula. The agent may select only a
root-owned named scope and paths below `/work/agent`; it cannot replace the task
package, raw validation truth or archive destination. The current bundle
contains full scopes named `band-0-3-full`, `band-4-9-full`,
`band-10-14-full`, `band-15-19-full`, and `all-full`.

```bash
tidmad-score candidate \
  --band 0-3 --scope band-0-3-full \
  --candidate-id my-candidate-001 \
  --candidate-source /work/agent/candidates/my-candidate-001 \
  --denoised-dir /work/agent/evaluation/my-candidate-001
```

Candidate source contains `model.py` (or `model/`), `architecture.json`,
`train_config.json` and `weights.pth`. The final all-band invocation names one
retained winner per band and writes the canonical 20-entry score vector. At the
deadline the finalizer packages complete winners when available and otherwise
marks the submission partial; it never invents missing scores.

The final `task.md`, cloud provisioning commands, model identity patterns and
actual drill receipts remain launch-time inputs. A local test is not evidence
that the H100 drill ran. Run the focused local checks with:

```bash
.venv/bin/ruff check deployments/tidmad_coding_agent_baseline \
  tests/deployments/tidmad_coding_agent_baseline
.venv/bin/pytest -q tests/deployments/tidmad_coding_agent_baseline
```

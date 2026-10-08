# TIDMAD fixed workflow experiment

Run one TIDMAD waveform band with a fixed research schedule and an explicit
information treatment. Each unit has its own external workspace and 24-hour
clock. The [task package](../../../tasks/tidmad/README.md) defines waveform
meaning, score and Health checks; this directory chooses budgets and treatments.

For a small learning run, start with the
[one-band tutorial](../../../tutorials/paper/tidmad/README.md). For recorded paper
units and source-pair limits, use the [paper artifact reference](../../paper-artifacts.md).

## Choose the information treatment

| Condition | Information available | Preparation |
| --- | --- | --- |
| NoPrior | Literature Review; no human advice or Data Analysis | Preview below |
| DA-only | Literature Review and Data Analysis; no human advice | [Analysis preparation](FULL_LAUNCH.md) |
| Historical Full | Literature Review, Data Analysis and frozen advice | [Full preparation](FULL_LAUNCH.md) |

Use a fresh unit for changed inputs. These are experiment conditions, not new
versions of the scientific task. Exact files and resolved settings belong to the
[workflow contract](workflow-contract.md#current-shared-workflow-settings).

<a id="what-each-command-does"></a>

## Preview a NoPrior unit

From a clean exp checkout with its own frozen environment, prepare the selected
band's verified HDF5 files and anchors in an external directory. Use the exact
framework revision from `SIDERIUS_REVISION`. Then run:

```bash
.venv/bin/python -m experiments.tidmad.main_fixed_workflow.preflight \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 \
  --data_dir /path/to/isolated/band-0-3-data \
  --workspace /path/to/unit-parent/no-prior-0-3/workspace \
  --run_name reviewed_run_name
```

This checks pins, task/configuration identities and data bytes, and prints the
command. It starts no provider calls or training. The future workspace must be
`<unit-dir>/workspace`; changing any input requires a fresh preview.

## Review the supervisor, then launch

```bash
bash experiments/tidmad/main_fixed_workflow/launch.sh \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 \
  --data_dir /path/to/isolated/band-0-3-data \
  --unit-dir /path/to/unit-parent/no-prior-0-3 \
  --run_name reviewed_run_name
```

Review the resulting receipt, then add `--launch` to start. Formal deployment
requires an H100, an external credential environment and persistent storage.
The supervisor records the start and deadline once; a restart does not extend
the clock. Follow the [deployment and retention contract](workflow-contract.md#what-each-command-does)
for backup, disk protection and service installation before a formal run.

## Find the next owner

| Need | Read |
| --- | --- |
| Exact settings, file ownership and customization | [Workflow contract](workflow-contract.md) |
| Prepare raw files and anchors | [Task data guide](../../../tasks/tidmad/data/README.md) |
| Analysis-enabled launch | [Full/DA-only launch](FULL_LAUNCH.md) |
| Prior bounded execution evidence | [Smoke qualification](SMOKE_QUALIFICATION.md) |
| Restart an existing unit | [Continuation contract](CONTINUATION.md) |

# TIDMAD fixed workflow experiment

This directory turns the TIDMAD task package into one concrete experiment: one
band, one external workspace, one run identity, and one selected information
treatment. It does not redefine TIDMAD's metric or model I/O. Those remain in
`tasks/tidmad/`.

The normal user path is:

```text
choose band and external data root
    → run preflight.py (NoPrior only)
    → review the printed pins, hashes, treatment, and command
    → run launch.sh with the same inputs
    → inspect the external workspace and receipts
```

## File map: change the right file

| File | What it does | Change it when… |
| --- | --- | --- |
| `workflow.json` | Shared fixed-workflow settings: task composition, LLM routing file, iterations, rounds, epoch ceilings, Trial/Formal time and VRAM limits, validation/evaluation portions, and parameter rules | You are intentionally defining a new workflow treatment |
| `iclr_official_v1.json` | Provider/model and reasoning-effort routing for interpret, analysis, propose, implement, validate, tune, and literature review | You are changing the LLM routing; record a new experiment identity |
| `../information_treatments/main-fixed-no-prior.yaml` | Explicitly disables human advice and Data Analysis while keeping Literature Review enabled | You need the NoPrior information condition |
| `../information_treatments/main-fixed-da-only.yaml` | Enables Data Analysis and disables model-level advice | You need the DA-only ablation |
| `../information_treatments/main-fixed-full.yaml` | Enables the frozen Full advice artifact and Data Analysis | You need the Full prior condition |
| `advice.json` | Legacy/local Full advice artifact retained for historical compatibility | Do not edit for the current Full treatment; use `full-prior-v8/advice.json` and its manifest |
| `preflight.py` | Resolves one band, verifies pins/checksums, and prints a launch receipt without starting a chain | Before every fresh unit and after any input change |
| `FULL_LAUNCH.md` | Preparation and launch instructions for DA-only and historical Full conditions | Before any treatment that enables Data Analysis or advice |
| `band_inputs.py` | Defines the four supported bands and rejects files outside the selected band | To add a new band or a different file grouping; update checksums and tests too |
| `launch.sh` | Thin wrapper that invokes the supervisor in this directory's environment | Normally do not edit; it is the stable entrypoint |
| `supervisor.py` | Owns the 24-hour unit clock, launch receipt, restart/resume checks, deadline stop, and service boundary | Only when changing run control or restart semantics |
| `unit_clock.py` | Writes and validates the immutable UTC deadline | Only when changing clock identity or receipt format |
| `backup.py`, `backup.sh` | Uploads retained certified artifacts and writes backup receipts | Only when changing retained-artifact selection or backup transport |
| `systemd/` | Service and timer templates for workflow, backup, and disk guard | When installing or changing machine-level service behavior |

The task package files are documented in
[`tasks/tidmad/README.md`](../../../tasks/tidmad/README.md). If the requested
change concerns waveform meaning, score, deliverable encoding, data topology,
or Health thresholds, change the task owner there instead of putting the rule
in this experiment directory.

## Current shared workflow settings

`workflow.json` is the single place for the values below. The exact values in
the current file are authoritative; this table explains their meaning.

| Setting | Meaning |
| --- | --- |
| `task_composition` | Uses `continuous_regression_frozen_pool.yaml`, the continuous `[B,T]` waveform task with the fixed training parent |
| `--num_iterations` | Maximum iterations in this fixed schedule |
| `--max_rounds` | Tuning rounds within one iteration |
| `--max_epochs`, `--trial_max_epochs`, `--formal_max_epochs` | Scientific/runtime epoch ceilings; a time budget can stop earlier |
| Trial/Formal time budgets | Candidate execution allowances for Trial and Formal |
| Trial/Formal VRAM budgets | Admission and runtime memory ceilings |
| `--formal_training_scope_source operator` | Formal training parent is chosen by the experiment, not by an agent proposal |
| `--formal_portion` | Fraction of each selected parent file used to build the Formal training scope; current value `0.1` means 10% of the declared parent |
| `--formal_train_portion` | Fraction of that already-selected Formal scope used in each training epoch; current value `1.0` means all of the Formal scope |
| `--formal_eval_portion` | Final Formal evaluation scope; the ICLR fixed workflow locks this to the full selected validation band |
| `--training_validation_portion` | Snapshot used for training-time validation loss in new runs |
| `--training_budget_reserve_fraction` | Portion held for final inference, scoring, and saving |
| `--no-runtime_watchdog` | Disables prediction-based phase killing; the supervisor deadline and disk guard remain separate controls |
| `workflow_parameter_rules` | Deterministic constraints on model parameters, including the fixed segmentation size |

The current ICLR fixed-workflow file resolves to these concrete values:

```text
iterations=100, rounds=3
max_epochs=trial_max_epochs=formal_max_epochs=100
Trial/Formal time=30/120 minutes
Trial/Formal VRAM=40/40 GiB
formal_training_scope_source=operator
formal_portion=0.1, formal_train_portion=1.0, formal_eval_portion=1.0
training_validation_portion=0.1
training_budget_reserve_fraction=0.2
prediction/runtime watchdog=disabled
model_config.segmentation_size=40000 (exact rule)
```

The epoch value is a ceiling, not a promise to stop after 100 epochs. The
time policy may stop earlier, and the cooperative budget logic reserves the
configured downstream fraction for inference, scoring, and saving. Scientific
early stopping is not enabled by this file.

`formal_portion=0.1` does not mean that each epoch sees 10% of the Formal
scope. The 10% selection happens first; `formal_train_portion=1.0` then makes
each epoch use all samples in that selected scope.

The workflow settings do not change the task's raw data, target, score, or
Health rules. A proposal still has to satisfy the task model I/O contract and
the workflow's schema checks.

## Information treatments

The treatment YAML files make information changes explicit. They all point to
the same `tasks/tidmad` package and the same workflow JSON.

| Treatment | Human advice | Data Analysis | Literature Review |
| --- | --- | --- | --- |
| `main-fixed-no-prior.yaml` | Off | Off | On |
| `main-fixed-da-only.yaml` | Off | On | On |
| `main-fixed-full.yaml` | On, frozen `full-prior-v8/advice.json` | On | On |

The treatment file is selected by the launcher/supervisor binding. It is not a
second task manifest. Its SHA-256 and resolved module states are recorded in
the preflight and launch receipts.

The preparation path depends on the condition:

- **NoPrior:** run `preflight.py`, review its receipt, then use the normal
  `launch.sh` entrypoint. The preflight example is for this condition.
- **DA-only:** first run `prepare_full.py --condition da-only`, then follow the
  three explicit analysis bindings in [`FULL_LAUNCH.md`](FULL_LAUNCH.md).
- **Full:** first run `prepare_full.py --condition full`, then use the Full
  launch command in [`FULL_LAUNCH.md`](FULL_LAUNCH.md). Do not infer this path
  from the NoPrior preflight command.

## What each command does

### 1. Preflight: inspect, do not launch

`preflight.py` checks all of the following before a provider call or training:

- exact exp revision and exact SIDERIUS revision;
- the installed SIDERIUS package and its `uv.lock` environment;
- a fresh external workspace;
- the selected band name and the expected training/validation HDF5 pair list;
- every selected HDF5 checksum against the committed campaign manifest;
- `segment_anchors.json` byte equality with the committed task ruler;
- task composition, workflow JSON, LLM config, literature config, and treatment hashes;
- the final command that will be passed to SIDERIUS.

Example:

```bash
.venv/bin/python -m experiments.tidmad.main_fixed_workflow.preflight \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 \
  --data_dir /path/to/isolated/band-0-3-data \
  --workspace /path/to/new/no-prior-0-3-workspace \
  --run_name reviewed_run_name
```

If you change the band, data root, treatment, workspace, or pinned checkout,
run preflight again. Do not reuse an old receipt after one of those changes.

### 2. Launch: start or resume one unit

```bash
bash experiments/tidmad/main_fixed_workflow/launch.sh \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 \
  --data_dir /path/to/isolated/band-0-3-data \
  --unit-dir /path/to/unit-parent/no-prior-0-3 \
  --run_name reviewed_run_name \
  --launch
```

`launch.sh` is a wrapper; `supervisor.py` does the work. The first effectful
launch writes `launch.json` once with the resolved command, input identities,
UTC start, and UTC deadline. A restart validates the same receipt and resumes
the same workspace without extending the deadline. A new scientific treatment
requires a new unit directory and run identity.

The service requires one H100 for the formal deployment, provider keys from a
mode-600 external environment, and a mounted persistent work volume. Secrets
are checked for presence but never written to receipts.

### 3. Backup and disk protection

The backup service and disk guard are independent systemd units. Backup keeps
certified `.pt` candidates, configs, source, score/Health receipts, and
provenance. It excludes raw `.pth` training files, denoised HDF5, `.env`,
temporary files, and logs. Every upload appends a local backup receipt. The
disk guard writes a `low_space_stop` receipt and stops the workflow service if
the mounted volume falls below its configured free-space threshold.

Install the matching templates under `systemd/` only after replacing the
machine placeholders and reviewing the unit-specific environment files. The
repository does not install or start services automatically.

## Changing data splits or other settings

Use this decision sequence:

1. **Only a different existing band?** Keep the task and workflow files. Change
   `--band` and `--data_dir`; preflight will reject files from other bands.
2. **A different set of segment rows?** Create a new declared pool JSON and
   composition/treatment. Update its seed, row indices, provenance, and tests.
   Do not overwrite `frozen_training_pool_v1.json` for a new scientific arm.
3. **A different model window or training budget?** Change `workflow.json` and
   give the result a new experiment identity. Re-run preflight and qualification.
4. **A different scientific output, score, or Health rule?** Change the task
   declarations/runtime under `tasks/tidmad/`, update the reference evidence,
   and start a fresh task/experiment identity. Do not patch a result file.
5. **A different advice or Data Analysis condition?** Add or update a treatment
   YAML and its referenced artifact. Keep the task composition and scientific
   contract unchanged.

## Retention and provenance

The external unit directory contains the launch receipt, chain workspace,
candidate records, scoring and Health evidence, backup receipts, and the
immutable deadline events. The repository contains no raw HDF5, credentials,
run workspace, or generated candidate code. Historical units are not resumed
under a new release; a new release creates a fresh unit and records its exact
pin.

## Related files

- [TIDMAD task package](../../../tasks/tidmad/README.md)
- [TIDMAD data-root preparation](../../../tasks/tidmad/data/README.md)
- [Full launch preparation](FULL_LAUNCH.md)
- [Smoke qualification](SMOKE_QUALIFICATION.md)
- [Continuation and resume](CONTINUATION.md)

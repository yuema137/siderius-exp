# Task-owned declarations and reference snapshots

This directory contains scientific declarations imported from the reviewed
pre-separation TIDMAD projection. Current compositions read `dataset_profile.json`
and `metric_spec.json` directly. The other files preserve reference snapshots;
they are not all loaded by every composition.

Before changing a value, follow the selected composition and the current-owner
column below. Update the selected declaration, dependent implementation,
provenance and task tests together. A change in scientific meaning requires a
new task identity and qualification; retain historical inputs and results.
The [task contract](../task-contract.md#which-file-owns-which-decision) explains
the full ownership boundary.

| File | Current role and owner | Historical source at import |
|---|---|---|
| `dataset_profile.json` | Bound by the task compositions; declares topology and storage encoding used by the runtime | `execute_tools/dataset_config.py`: `resolve_dataset_profile`, `TIDMAD_PROFILE` |
| `metric_spec.json` | Bound by the task compositions; implemented by `runtime/scoring.py` | Imported golden-metric declaration |
| `model_io_contract.json` | Historical classification snapshot; live model I/O comes from the selected `declared/task_config*.yaml` | `configs/task_config.yaml` via `workflows/task_config.py`: `run_bound_model_io_contract` |
| `deliverable_spec.json` | Reference snapshot; live naming comes from the composition's `deliverable` block, encoding from the dataset profile and output conversion | `execute_tools/deliverable_spec.py`: `derive_tidmad_deliverable_spec` |
| `identity.json` | Reference snapshot of file families and indices; runtime topology comes from the bound dataset profile | `execute_tools/dataset_config.py`: `DatasetConfig` file patterns / `num_files` |

The final column records historical framework paths, not current scientific
owners or instructions to regenerate files there. Current bindings can be read
in [continuous regression](../compositions/continuous_regression.yaml),
[the frozen-pool variant](../compositions/continuous_regression_frozen_pool.yaml)
and [historical classification qualification](../compositions/bounded_qualification.yaml).
See [provenance](../PROVENANCE.md#snapshots-in-resolved--provenance) for the import
checkpoint and [task tests](../../../tests/tasks/tidmad) for current checks.

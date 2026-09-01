# `resolved/` — task-owned frozen declarations

These files were imported from the reviewed pre-separation TIDMAD projection.
The composition reads the declared dataset and metric files at runtime, so an
intentional edit changes task identity and requires qualification evidence.

No framework-side projection tool or duplicate scientific authority remains.
Changes must update the declaration, provenance, and external task tests in
one reviewed commit.

| snapshot | generated from (owning authority) |
|---|---|
| `dataset_profile.json` | task-owned reviewed profile; decoded by `tasks/tidmad/runtime/profile.py` |
| `model_io_contract.json` | configs/task_config.yaml `forward_contract.model_io` via workflows/task_config.py (`run_bound_model_io_contract`) |
| `deliverable_spec.json` | execute_tools/deliverable_spec.py (`derive_tidmad_deliverable_spec`) |
| `metric_spec.json` | task-owned metric declaration loaded by `compositions/bounded_qualification.yaml` |
| `identity.json` | execute_tools/dataset_config.py (`DatasetConfig` file patterns / `num_files`) |

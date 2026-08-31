# Tasks

Each directory is a static scientific task package consumed through SIDERIUS
task-composition and plugin contracts. Task packages own dataset identity and
splits, scientific semantics, model I/O, objectives, metrics, Health
definitions, plugins, runtime adapters, and task provenance.

Task packages do not own iteration schedules, resource budgets, training
exposure, literature-review treatments, workflow launchers, or result records.
Those belong under `experiments/`; multi-stage selection and authorization
belong under `campaigns/`.

Private datasets and credentials are never committed.

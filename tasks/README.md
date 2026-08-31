# Tasks

Each directory is a static scientific task package consumed through SIDERIUS
task-composition and plugin contracts. Task packages own dataset identity and
splits, scientific semantics, model I/O, objectives, metrics, Health
definitions, plugins, runtime adapters, and task provenance.

Task packages do not own iteration schedules, resource budgets, training
exposure, literature-review treatments, or result records. Experiments select
a workflow and supply those treatment values; the workflow retains ownership
of Trial/Formal mechanics. Multi-run selection and authorization belong under
`campaigns/`.

Private datasets and credentials are never committed.

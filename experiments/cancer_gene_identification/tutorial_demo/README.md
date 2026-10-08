# CPDB workflow demonstration

Use the [Cancer tutorial](../../../tutorials/supplementary/cancer/README.md) to
create an external project and run the saved script. This workflow selects one
complete CPDB graph with its original masks, three search iterations, all-Luna
test routing and task-owned masked BCE. Validation feeds search; Test labels are
not loaded. It is not an eight-network benchmark or a paper artifact.

The initializer copies this workflow into your project's `experiments/` folder.
The adjacent saved experiment JSON owns iterations, active-label fractions and
budgets. Formal training fractions remain operator-controlled. Batch size is one
whole graph; reduced active-label fractions do not reduce topology or model
memory. No Health, Data Analysis, literature review or advice is enabled.

A [recorded three-iteration run](../../../tutorials/supplementary/cancer/example/README.md)
completed all Trial and Formal phases with diagnostic result authority. No task
Health checks are declared or evaluated. Original qualification/campaign
configurations and evidence remain separate.

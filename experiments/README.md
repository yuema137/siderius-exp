# Experiments

Each experiment directory selects one static task package and one workflow,
then owns one concrete treatment: parameter values, advice, literature-review
state, iteration and epoch counts, data exposure, output locks, resource
budgets, and result receipts.

The workflow owns the execution procedure, including Trial/Formal roles and
their progression. The experiment may set approved values for that workflow;
it does not redefine what Trial or Formal means.

Experiment records identify the exact SIDERIUS revision, this repository
revision, resolved task identity, configuration and plugin hashes, dataset
identity, executable argv, and runtime budgets. Changing any treatment value
creates a new experiment identity; it does not modify the task package.

Final consumer-pair qualification wrappers live under each task's
`p0_final_pair_qualification/` directory and support exact-checkout,
fresh-workspace and `--dry-run` validation.

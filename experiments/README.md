# Experiments

Each experiment directory selects one static task package and owns one concrete
treatment: workflow topology, launch parameters, advice, literature-review
state, iteration and epoch counts, data exposure, output locks, resource
budgets, and result receipts.

Experiment records identify the exact SIDERIUS revision, this repository
revision, resolved task identity, configuration and plugin hashes, dataset
identity, executable argv, and runtime budgets. Changing any treatment value
creates a new experiment identity; it does not modify the task package.

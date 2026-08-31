# NatureBench cancer-gene identification task package

This package declares the NatureBench `s41551-024-01312-5` cancer-gene task. It
is a transductive binary node-classification problem over eight biological
networks. The primary metric is the unweighted mean of per-network validation
AUPRC values; higher is better.

## Scientific contract

One item is one complete graph. The task runtime converts dense HDF5 adjacency
matrices into packed node and edge records. Models emit raw binary logits while
preserving node and active-split markers. The task-owned masked BCE objective
uses labels only on the active node mask, and task parameter rules require
batch size one.

Validation masks remain held out during model search. A fair official
comparison requires freezing a selected method, refitting under the comparator
protocol, exporting test probabilities, and running the untouched NatureBench
evaluator. Validation AUPRC alone is not an official test result.

AI-Build-AI reports headline mean AUPRC `0.774`; its committed per-network
artifacts average to `0.7725415502369475`. Reports keep those two authorities
separate.

## Static task compositions

```text
compositions/two_network.yaml    complete cpdb and ltg graphs
compositions/eight_network.yaml  all eight complete NatureBench graphs
```

These are reusable task scopes, not workflows. An experiment selects one of
them, while the selected SIDERIUS workflow retains ownership of Trial/Formal
roles, progression, retries, and persistence.

## Package ownership

```text
declared/                   dataset, metric, task, proposer, and implementor declarations
plugins/_cancer_gene_task.py  scope construction, graph packing, and prediction codec
plugins/_cancer_gene_metrics.py  per-network AUPRC/AUROC and unweighted means
plugins/cancer_gene_masked_bce.py  task-authoritative masked objective
plugins/cancer_gene_reference_gnn.py  known-good qualification model
PROVENANCE.md               benchmark source and data identity
STATUS.md                   supported capability and evidence record
```

The task directory contains no experiment launcher, iteration schedule,
resource budget, or campaign authorization.

## Data

Point the task runtime at the NatureBench
`tasks/s41551-024-01312-5/problem/data` directory containing:

```text
cpdb/data.h5       stringdb/data.h5   pcnet/data.h5
iref_v15/data.h5   iref_v9/data.h5    multinet/data.h5
mtg/data.h5        ltg/data.h5
```

Each file provides `network`, `features`, `mask_train`, `mask_val`,
`mask_test`, `y_train`, and `y_val`. Test labels are not task inputs.

## Experiments

```text
experiments/cancer_gene_identification/two_network_qualification/
experiments/cancer_gene_identification/eight_network_comparison/
```

Both are ordinary experiments selecting the same Trial/Formal workflow. Their
scope size does not make either one a campaign.

Sources:

- <https://huggingface.co/datasets/FrontisAI/NatureBench/tree/main/tasks/s41551-024-01312-5>
- <https://github.com/aibuildai/AI-Build-AI/tree/main/tasks/cancer-gene-identification>
- <https://github.com/Blair1213/TREE>

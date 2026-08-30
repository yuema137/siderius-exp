# NatureBench cancer-gene identification

This task pack runs SIDERIUS on NatureBench case `s41551-024-01312-5` without
adding task branches to framework code. It is a transductive binary
node-classification task over eight biological networks. The primary metric is
the unweighted mean of per-network AUPRC values; higher is better.

This package is an external consumer of a pinned SIDERIUS checkout. Its real
task declarations and workflows remain in `siderius-exp`; they are not
framework defaults or examples.

## Data

Obtain the exact benchmark task from
`FrontisAI/NatureBench/tasks/s41551-024-01312-5`. Point `--data_dir` at its
`problem/data` directory. It must contain:

```text
cpdb/data.h5       stringdb/data.h5   pcnet/data.h5
iref_v15/data.h5   iref_v9/data.h5    multinet/data.h5
mtg/data.h5        ltg/data.h5
```

Each HDF5 file must provide `network`, `features`, `mask_train`, `mask_val`,
`mask_test`, `y_train`, and `y_val`. Test labels are deliberately not part of
the task input.

## Scientific contract

One dataset item is one complete graph. The task-owned data path converts the
dense HDF5 adjacency matrix to packed node and edge records, so training memory
scales with nodes plus nonzero edges. Candidate models must use batch size 1,
preserve the node and active-split markers in their output, and emit raw binary
logits. The declared masked BCE objective consumes labels only on the active
node mask.

During model search, the supplied validation masks remain held out and the
SIDERIUS metric computes validation AUPRC. A fair official comparison requires
freezing the selected method, refitting it on train plus validation labels,
exporting test probabilities, and running the untouched NatureBench evaluator.
Do not use official test scores to select candidates.

The AI-Build-AI repository reports a headline mean AUPRC of `0.774`; its
committed per-network `score.json` values average to `0.7725415502369475`.
Reports must keep the published claim and reproducible artifact value separate.

## Workflows

- `workflows/qualification/composition.yaml` selects the complete `cpdb` and
  `ltg` networks for bounded compatibility checks. Its score is not comparable
  with the eight-network benchmark result.
- `workflows/formal/composition.yaml` selects all eight complete networks for
  the scientific campaign and AI-Build-AI comparison.

## Dry run

```bash
bash tasks/cancer_gene_identification/quickstart.sh \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --workspace /tmp/cancer-gene-dry-run \
  --data_dir /path/to/NatureBench/tasks/s41551-024-01312-5/problem/data \
  --workflow qualification \
  --dry-run
```

The script is a thin adapter over the production chain launcher. Extra
arguments are passed through and later values override the bounded defaults.
The bounded default runs two chain iterations. Each iteration has one Trial
round followed by one forced Formal round, so iteration-state continuity and
the Trial-to-Formal transition are both exercised before validation AUPRC is
computed. Formal training and evaluation exposure are externally fixed at
`0.25`; the agent cannot expand them. Generated capabilities are isolated under
the supplied workspace to prevent candidates from an earlier qualification
run entering a cold start.
The bounded default disables the shared runtime watchdog until SIDERIUS issue
`#388` is repaired; explicit Trial and Formal operator budgets remain declared.

## Package contents

- `declared/`: dataset, metric, task, proposer, and implementor declarations.
- `plugins/_cancer_gene_task.py`: scope construction, graph packing, and the
  benchmark-shaped prediction codec.
- `plugins/_cancer_gene_metrics.py`: per-network AUPRC/AUROC and their
  unweighted means.
- `plugins/cancer_gene_masked_bce.py`: task-authoritative masked objective.
- `plugins/cancer_gene_reference_gnn.py`: small known-good message-passing
  reference plugin for qualification.
- `workflows/qualification/`: bounded two-network compatibility workflow.
- `workflows/formal/`: complete eight-network campaign composition.

Sources:

- <https://huggingface.co/datasets/FrontisAI/NatureBench/tree/main/tasks/s41551-024-01312-5>
- <https://github.com/aibuildai/AI-Build-AI/tree/main/tasks/cancer-gene-identification>
- <https://github.com/Blair1213/TREE>

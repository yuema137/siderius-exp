# Final-pair qualification

This directory is an index for the four bounded consumer-pair checks. They
exercise the real task adapters against one exact SIDERIUS revision. They are
engineering qualification runs, not scientific campaigns.

## Choose a task

| Task | Run page | Task page |
|---|---|---|
| TIDMAD | [`tidmad/`](../tidmad/p0_final_pair_qualification/) | [`tasks/tidmad/`](../../tasks/tidmad/) |
| Oxford-IIIT Pets | [`oxford_iiit_pet/`](../oxford_iiit_pet/p0_final_pair_qualification/) | [`tasks/oxford_iiit_pet/`](../../tasks/oxford_iiit_pet/) |
| DAVIS | [`davis_future_prediction/`](../davis_future_prediction/p0_final_pair_qualification/) | [`tasks/davis_future_prediction/`](../../tasks/davis_future_prediction/) |
| Cancer MTG | [`cancer_gene_identification/`](../cancer_gene_identification/p0_final_pair_qualification/) | [`tasks/cancer_gene_identification/`](../../tasks/cancer_gene_identification/) |

Each task page gives the exact bounded command, required external data, and
workspace rule. Start with `--dry-run`, use a fresh workspace, and keep logs
and results outside Git.

## What this qualification proves

The four wrappers check that a task can bind to the pinned framework, execute
the selected workflow, save typed records, and preserve task-owned split and
metric rules. Trial/Formal values, budgets, and data portions belong to each
experiment wrapper and are not task defaults.

Scientific quality and infrastructure behavior are reported separately. A
candidate rejected by a task's Health rule can still provide valid evidence
that the infrastructure reached training, inference, scoring, and Health.

Historical receipts are kept in provenance records and are not launch
authorization. Do not reuse an old workspace or treat an old score as evidence
for a changed repository pair.

# Cancer-gene MTG size qualification

This bounded engineering experiment keeps the complete `mtg` graph fixed in
both Trial and Formal. Trial activates deterministic 25% subsets of the
task-owned training and validation masks. Formal activates the complete
training and validation masks. Graph topology, node features, split ownership,
model family, objective, and metric remain unchanged, so the intended treatment
difference is data exposure rather than cross-network generalization.

The complete graph remains visible in both regimes because this is a
transductive node-classification task. Sampling never moves nodes between the
declared train, validation, and test masks.

```bash
bash experiments/cancer_gene_identification/launch.sh \
    --experiment mtg_size_qualification \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/cancer-mtg-size-workspace \
    --data_dir /path/to/NatureBench/problem/data
```

Use `--dry-run` first. The validation AUPRC is qualification evidence, not an
official NatureBench test result.

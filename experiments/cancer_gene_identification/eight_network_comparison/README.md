# Cancer-gene eight-network comparison

This experiment selects
`tasks/cancer_gene_identification/compositions/eight_network.yaml`, containing
all eight NatureBench networks. It uses the same SIDERIUS Trial/Formal workflow
as the bounded qualification; eight-network scope does not make it a campaign.

The current launcher preserves the existing two-iteration, two-round, one-epoch,
batch-one, 0.25-exposure, and 10/16 GiB qualification treatment. A valid
validation mean AUPRC can be compared across SIDERIUS candidates, but an
official AI-Build-AI comparison additionally requires the frozen refit and
untouched NatureBench test-evaluator procedure.

```bash
bash experiments/cancer_gene_identification/launch.sh \
    --experiment eight_network_comparison \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/cancer-eight-network-workspace \
    --data_dir /path/to/NatureBench/problem/data
```

Use `--dry-run` first. Any override creates a different experiment treatment
and must be recorded separately.

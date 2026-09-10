# Cancer-gene two-network qualification

This bounded engineering experiment selects
`tasks/cancer_gene_identification/compositions/two_network.yaml`, containing
complete `cpdb` and `ltg` graphs. Its mean validation AUPRC is not comparable
with the eight-network NatureBench result.

It uses the shared SIDERIUS Trial/Formal workflow for two research iterations,
two tuner rounds, one epoch, regressor output, batch size one, 0.25 training and
evaluation exposure, and 10/16 GiB Trial/Formal VRAM ceilings. The workflow
owns Trial/Formal semantics; this experiment supplies those treatment values.
Because one complete graph batch is substantially more expensive to inspect
than the image and short-sequence qualification batches, this workflow gives
one footprint forward 600 seconds and the complete isolated preflight 1,800
seconds. These are measurement watchdogs, not training exposure or capacity
ceilings.

```bash
bash experiments/cancer_gene_identification/launch.sh \
    --experiment two_network_qualification \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/cancer-two-network-workspace \
    --data_dir /path/to/NatureBench/problem/data
```

Use `--dry-run` first. Any override creates a different experiment treatment
and must be recorded separately.

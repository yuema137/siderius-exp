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

## Watchdog replay

The issue-#388 CPDB/LTG replay is a separate, bounded profile. It is the only
Cancer launcher profile that enables the runtime watchdog; it uses a fresh
workspace identity, one Trial followed by a forced Formal round, one epoch,
batch size one, a 20-minute Formal operator budget, a 3.5 watchdog safety
factor, and a 120-second floor:

```bash
bash experiments/cancer_gene_identification/launch.sh \
    --experiment two_network_qualification \
    --profile watchdog_replay \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/fresh/cancer-watchdog-replay-workspace \
    --data_dir /path/to/NatureBench/problem/data \
    --dry-run
```

This profile is for the planned external replay and does not certify a
runtime-profile or launch a workload by itself. Preserve its setup-only
evidence and record the measured Formal admission/deadline after a real run.

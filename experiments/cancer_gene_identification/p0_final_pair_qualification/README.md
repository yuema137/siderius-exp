# Cancer MTG historical P0 final-pair qualification

This wrapper requires the [historical P0 infra pin](../../p0_final_pair_qualification/README.md),
not the current repository-root release revision.

This is a bounded consumer-pair qualification wrapper, not a campaign. Read
the [Cancer task contract](../../../tasks/cancer_gene_identification/README.md),
use a fresh external workspace, and inspect the command with `--dry-run`
before execution.

```bash
bash experiments/cancer_gene_identification/p0_final_pair_qualification/launch.sh --siderius-checkout /path/to/SIDERIUS --workspace /path/to/fresh/workspace --data_dir /path/to/problem/data
```

Selects the existing one-network MTG profile and full graph, with one epoch/batch 1, 5/8-minute budgets, 180/600-second probes and two iterations × two rounds. Existing two-network coverage remains unchanged.

The data root must contain `mtg/data.h5`; outputs remain in the external workspace.

# DAVIS historical P0 final-pair qualification

This wrapper requires the [historical P0 infra pin](../../p0_final_pair_qualification/README.md),
not the current repository-root release revision.

This is a bounded consumer-pair qualification wrapper, not a campaign. Read
the [DAVIS task contract](../../../tasks/davis_future_prediction/README.md),
use a fresh external workspace, and inspect the command with `--dry-run`
before execution.

```bash
bash experiments/davis_future_prediction/p0_final_pair_qualification/launch.sh --siderius-checkout /path/to/SIDERIUS --workspace /path/to/fresh/workspace --data_dir /path/to/DAVIS_2017
```

Preserves 8-context/4-target geometry, selects Trial/Formal `.05/.20`, caps train/eval at 3/3, uses one epoch/batch 1, 2/3-minute budgets and 60/240-second probes across two iterations × two rounds.

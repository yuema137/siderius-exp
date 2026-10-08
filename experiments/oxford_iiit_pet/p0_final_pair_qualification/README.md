# Oxford-IIIT Pet historical P0 final-pair qualification

This wrapper requires the [historical P0 infra pin](../../p0_final_pair_qualification/README.md),
not the current repository-root release revision.

This is a bounded consumer-pair qualification wrapper, not a campaign. Read
the [task contract](../../../tasks/oxford_iiit_pet/README.md), use a fresh
external workspace, and inspect the command with `--dry-run` before execution.

```bash
bash experiments/oxford_iiit_pet/p0_final_pair_qualification/launch.sh --siderius-checkout /path/to/SIDERIUS --workspace /path/to/fresh/workspace --data_dir /path/to/OXFORD_IIIT_PET
```

Uses all 370/74 manifest rows, one epoch, batch 16, 2/3-minute budgets, 60/180-second probes and two iterations × two rounds. Results stay in the external workspace; `--dry-run` inspects argv.

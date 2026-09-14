# TIDMAD final-pair qualification

This is a bounded consumer-pair qualification wrapper, not the TIDMAD Gold
campaign. It exercises the selected task and workflow with a fresh external
workspace. Review the [task contract](../../../tasks/tidmad/README.md) and use
`--dry-run` before any execution.

```bash
bash experiments/tidmad/p0_final_pair_qualification/launch.sh --siderius-checkout /path/to/SIDERIUS --workspace /path/to/fresh/workspace --data_dir /path/to/TIDMAD
```

Uses Trial/Formal `.01/.01`, train cap 1024, one epoch, batch 16, 3/5-minute budgets, 60/240-second probes and two iterations × two rounds. Results stay in the external workspace. Use `--dry-run` to inspect argv.

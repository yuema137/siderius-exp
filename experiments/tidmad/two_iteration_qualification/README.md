# TIDMAD two-iteration qualification

This bounded engineering experiment selects
`tasks/tidmad/compositions/bounded_qualification.yaml` and drives it through
the normal SIDERIUS Trial/Formal workflow. It is not a Gold campaign.

## Frozen experiment configuration

- two research iterations;
- two tuner rounds per iteration;
- one epoch per attempt;
- Trial/Formal batch parity with a Formal minimum of one;
- Trial, Formal training, and Formal evaluation portions of `0.02`;
- Trial and Formal time ceilings of 20 and 60 minutes;
- task-owned literature-review configuration.

The task owns its data adapter, declarations, metric, Health definition,
scientific prompt blocks, and reusable bounded composition. This experiment
owns selecting that composition and the treatment values above.

## Launch

```bash
bash experiments/tidmad/two_iteration_qualification/launch.sh \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/tidmad-qualification-workspace \
    --data_dir /path/to/tidmad-data
```

Use `--dry-run` first. Any override creates a different experiment treatment
and must be recorded separately.

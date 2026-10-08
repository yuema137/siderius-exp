# TIDMAD two-iteration qualification

Start here for the current bounded TIDMAD experiment. It selects the task
package's composition and records one treatment; it is not a Gold campaign and
does not authorize provider-backed execution. Read the [task README](../../../tasks/tidmad/README.md)
for scientific semantics and the [campaign index](../../../campaigns/README.md)
for Gold status.

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

First [stage and byte-compare the approved anchor](../../../tasks/tidmad/data/README.md#stage-the-approved-anchor)
at `data_dir/segment_anchors.json`. Both composed scoring and Trial anchoring
read that caller-staged file; an existing committed anchor or a presence-only
preflight is not proof of equality. Preserve the canonical ruler and reference
assets; [reference data ownership](../../../tasks/tidmad/README.md#5-reference-data-and-tools).

```bash
bash experiments/tidmad/two_iteration_qualification/launch.sh \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/tidmad-qualification-workspace \
    --data_dir /path/to/tidmad-data
```

Use `--dry-run` first. Any override creates a different experiment treatment
and must be recorded separately.

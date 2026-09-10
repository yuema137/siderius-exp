# DAVIS two-iteration qualification

This bounded engineering experiment selects
`tasks/davis_future_prediction/compositions/bounded_qualification.yaml` and
drives it through the normal SIDERIUS production chain. It is not a
competitive scientific campaign.

## Frozen experiment configuration

- two research iterations;
- two tuner rounds per iteration;
- one training epoch per attempt;
- complete 60-clip training and 15-clip validation qualification manifests;
- regressor output locked for task comparability;
- Trial/Formal batch parity with a Formal minimum of one;
- Trial VRAM ceiling of 10 GiB and Formal VRAM ceiling of 16 GiB;
- isolated preflight process-tree host-memory limit of 32 GiB;
- complete task-owned training and Formal evaluation portions.

The task owns the reusable scope, lower-is-better MSE, exact-L1 objective,
secondary metrics, Health definition, plugins, and runtime adapter. This
experiment owns selecting that scope and the treatment values above.

The 32-GiB preflight host-memory value is separate from the GPU VRAM ceilings.
It is the smallest rounded workflow allowance above the 24.933-GiB process-tree
RSS observed for a valid full-frame video candidate on TestPod. Exceeding it
still produces inconclusive measurement evidence, not a GPU-capacity verdict.

## Launch

```bash
bash experiments/davis_future_prediction/two_iteration_qualification/launch.sh \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/davis-qualification-workspace \
    --data_dir /path/to/davis-root
```

Use `--dry-run` first to inspect the exact resolved child command without LLM
or GPU work. Any override creates a different experiment treatment and must be
recorded separately.

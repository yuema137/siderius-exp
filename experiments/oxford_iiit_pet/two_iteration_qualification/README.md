# Oxford-IIIT Pet two-iteration qualification

This experiment exercises the static Oxford-IIIT Pet task package through the
normal SIDERIUS production chain. It is bounded engineering qualification, not
a competitive scientific campaign.

## Frozen experiment configuration

- two research iterations;
- two tuner rounds per iteration;
- one training epoch per attempt;
- complete 370-row training and 74-row validation qualification manifests;
- Trial/Formal batch parity with a Formal minimum of one;
- Trial VRAM ceiling of 8 GiB and Formal VRAM ceiling of 12 GiB;
- classifier output locked for task comparability;
- complete task-owned training and evaluation portions.

These values belong to this experiment. The task package owns the dataset,
splits, model I/O contract, objective, metrics, Health semantics, plugins, and
runtime adapter.

## Launch

```bash
bash experiments/oxford_iiit_pet/two_iteration_qualification/launch.sh \
    --siderius-checkout /path/to/pinned/SIDERIUS \
    --workspace /path/to/pets-qualification-workspace \
    --data_dir /path/to/oxford-iiit-pet/images
```

Use `--dry-run` first to inspect the exact resolved child command without LLM
or GPU work. Additional arguments pass through to `run_chain.sh`; any override
creates a different experiment treatment and must be recorded as such.

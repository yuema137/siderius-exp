# Oxford-IIIT Pet two-iteration qualification

This experiment exercises the static Oxford-IIIT Pet task package through the
normal SIDERIUS production chain. It is bounded engineering qualification, not
a competitive scientific campaign.

It explicitly selects
`tasks/oxford_iiit_pet/compositions/bounded_qualification.yaml`, the task-owned
370-row training and 74-row validation scope. The task defines that reusable
scope; this experiment decides to use it.

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
runtime adapter. The selected SIDERIUS workflow owns Trial/Formal execution,
round progression, retries, and persistence; this experiment supplies its
approved parameter values.

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

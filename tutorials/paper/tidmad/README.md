# TIDMAD: one band, editable budgets, and two kinds of frequency holdout

Use this tutorial to learn how a model denoises detector waveforms, change its
Trial/Formal data allowances, and evaluate frequencies excluded from training.
It uses band **0-3**, comprising four training and four validation HDF5 files.
The [notebook](../notebooks/02_tidmad_tutorial.ipynb) explains and prepares inputs;
terminal scripts run the search and, separately, final-test inference.

## Start in your own directory

First follow the [shared installation instructions](../README.md#1-install-in-the-two-exact-checkouts).
Use the exact exp environment, including its `tutorial` dependency group, and
the pinned infra checkout. From exp:

```bash
.venv/bin/python -B -m tutorials.paper.tidmad.project \
  --project /absolute/path/to/my-tidmad-study \
  --infra-checkout /absolute/path/to/SIDERIUS-tutorial
```

The project directory must be new and outside both repositories. Open its
`notebooks/02_tidmad_tutorial.ipynb` with the exp environment's Jupyter kernel.
For example, from exp:

```bash
.venv/bin/jupyter lab --ServerApp.root_dir=/absolute/path/to/my-tidmad-study
```

| Location in your project | What belongs there |
|---|---|
| `notebooks/` | Editable explanation and configuration examples |
| `tasks/tidmad/` | Copied task; frequency eligibility, waveform contract and metric |
| `experiments/` | Your iteration, fraction, time/VRAM, hardware and run settings |
| `llm/agents.json` | LLM routing; **no API-key values** |
| `advice/README.txt` | Explains that human advice is disabled in this entrypoint |
| `data/band-0-3/` | Eight original HDF5 files and initialized `segment_anchors.json` |
| `data/frequency-catalog.json` | Reviewed per-segment injected-frequency catalog |
| `scripts/` | Generated search and final-test entrypoints |
| `runs/<name>/` | Each fresh search's models, logs and results |
| `final-test/` | Selected-model declaration, selection seal and separate test outputs |

Credentials belong in the launching process's environment, sourced from a
trusted external secret file/store. Do not put them anywhere in this project.
The script reports names/presence only and refuses missing keys before launch.
NoPrior disables human advice and data analysis here; literature review remains
enabled, so its routed credentials are included in the check.

## What to try in the notebook

1. Change `iterations`/`epochs`, then Trial proportions and time/VRAM budgets.
2. Inspect the **paper pool**: 20 frozen training segments per file. Trial `.5`
   means 10/20; Formal `.1` identifies that 20/200 pool and uses all 20.
3. Inspect a worked **frequency split**: distinct injected frequencies go to
   train, workflow validation, or final test. All repeats of one frequency stay
   together. This excludes examples; it does not zero Fourier coefficients.
4. Prepare the real catalog and save a new task composition. In this new task,
   Trial/Formal fractions apply to the remaining eligible segments. It is a
   different scientific protocol from the paper pool.
5. Launch your saved experiment from its script. After model selection, stop
   search, seal one candidate, and run its final-test script without LLM calls.

The official [TIDMAD distribution](https://github.com/jessicafry/TIDMAD) provides
`download_data.py`; `--train_files 4 --validation_files 4 --science_files 0`
selects this band's files. The notebook provides exact staging and catalog
commands. A band still contains about 32 GB of uncompressed channel samples;
no download occurs during notebook Run All. Source hashes and original segment
indices are preserved for scoring.

Preview and launch from the initialized project:

```bash
/absolute/path/to/my-tidmad-study/scripts/run-tidmad.sh
/absolute/path/to/my-tidmad-study/scripts/run-tidmad.sh --launch
```

Preview needs no GPU/data/keys, but both source checkouts must be clean and
correctly pinned. Launch accepts one NVIDIA RTX 5090 or H100. Budgets must leave
VRAM headroom; the 40 GiB paper setting does not fit a 5090. Another NVIDIA GPU
requires qualifying and extending the GPU check plus checking CUDA and
calibration. AMD and Intel GPUs are unsupported. Per-stage time allowances are
not total campaign deadlines or spending caps.

## Interpret the two evaluations correctly

**Workflow validation** influences the agent and can be used during training
validation. It tests frequencies excluded from training examples, but it is
not untouched by model selection. **Final test** reserves a third frequency
group until the selected model is fixed. Its script hashes the selected model,
configuration and plugins, refuses changes after sealing, and writes results
outside the search workspace. Do not use that result to choose another model.

This fixed workflow is a trusted local process without a separate security
sandbox. Its files are locally readable; the final holdout is a procedural
separation, not proof of access isolation. Frequency separation tests transfer
across injected tones, not an absolute absence of memorization. Nearby tones,
harmonics and amplitude distributions remain relevant scientific choices.

The final report uses the task's TIDMAD metric, is **diagnostic**, and does not
perform the full workflow Health assessment. Full-band catalog accuracy and
real API/GPU performance have not yet been qualified for this tutorial. The
catalog inspector refuses ambiguous/changing tones rather than guessing. If
that happens on real data, investigate the data semantics before proceeding.

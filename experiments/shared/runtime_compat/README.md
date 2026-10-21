# Historical timing decisions

Use this package when you want a **new external workspace** to apply a paper
experiment's original timing rules. Ordinary tutorials use the framework's
corrected default and do not need this package. Installing it changes no default.

Use the **standalone pair qualified for this package**: runtime package 0.1.6
and infra revision `7b0ab06f0a4d2e205725a7d778443202280ac02b`. The exp root
version file remains the ordinary tutorial dependency; it does not select this
newer historical compatibility environment. The [current qualification](qualifications/observation-order/report.md)
explains the offline checks. The [earlier receipt](../../../provenance/validation/2026-10-08_v1_metadata/receipt.json)
is historical evidence for its own source versions.

The paper runs estimated training time from observed steps. Their rules could
reject a short phase even after every requested step had finished, because too
few observations were stable. New infra can use the actual time of completed
work. This package preserves the original timing algorithms and selects the
original admission rule explicitly. It also keeps the old way of reading and
sorting saved timing records; ordinary runs use corrected timezone handling.
The separate historical prompt adapters can
then present those decisions to the agents in the original format.

## Prepare your own launch

1. Start with the recorded unit in the [paper artifact reference](../../paper-artifacts.md).
   Copy its launch configuration and complete task package to your own project.
   Remap data paths and select a new output workspace. Keep its other historical
   profiles, model routing, budgets and task settings.
2. Prepare a separate infra checkout at the qualified revision above, then run
   `uv sync --group dev --frozen` inside that checkout. Do this for each
   environment that launches infra or executes training. Do not use the exp
   root environment's older framework for this package.

   From your exp checkout, install the standalone package into those exact
   environments:

   ```bash
   uv pip install --python /path/to/launch/.venv/bin/python ./experiments/shared/runtime_compat
   uv pip install --python /path/to/execution/.venv/bin/python ./experiments/shared/runtime_compat
   ```

   Replace both paths with your actual environment paths. If they are the same,
   run the command once. Run this installation after `uv sync`: a later exact
   sync may remove separately installed packages.
3. Find your `run_id` in the [versioned launch overlay](paper-measured-completion-v1.json).
   Add its `--runtime_verifier` and the shared arguments below to your copied
   standard iteration or chain command. For example, TESS `nop_004` uses:

   ```bash
   --runtime_completion_policy verified-prediction-v1 \
   --runtime_verifier legacy-7689fd58-verifier-v1 \
   --trial_time_admission_source measured \
   --formal_time_admission_source measured
   ```

   These are additional arguments, not a standalone launch command. Keep the
   copied command's other required arguments and replace conflicting flags
   instead of appending duplicates. Installing exp does not apply the overlay.
4. Install planner package 0.12.2 from this exp checkout into the launch
   environment already prepared in step 2:

   ```bash
   uv pip install --python /path/to/launch/.venv/bin/python ./experiments/shared/planner_compat
   ```

   Keep the qualified infra revision from step 2. The general
   [planner installation guide](../planner_compat/usage.md#install-into-the-environment-that-will-run-infra)
   also describes older root-pinned setups; that version instruction does not
   apply to this standalone pair.

   In your copied `llm/agents.json`, use
   `legacy-9b78d505cb11-paper-scheduler-off-v11` for TESS, LIGO and TIDMAD, or
   `legacy-9b78d505cb11-paper-late-scheduler-off-v11` for Project8. Keep the
   historical training scheduler disabled (`train_config.lr_schedule: null`). For example:

   ```json
   {"tune": {"planner_strategy": "legacy-9b78d505cb11-paper-scheduler-off-v11"}}
   ```

   Merge this field into your existing configuration; keep its model, credentials
   and other routes. The immutable overlay still records its earlier v8 planner
   selection. Use the v11 mapping above for the currently qualified policy and
   training-manual presentation; v8 alone does not restore all of those fields.
   Saved results retain the actual verifier identity.

The overlay covers eleven native paper units: TESS, LIGO, Project8 dual
representation, four TIDMAD NoPrior bands and four TIDMAD analysis-on bands.
Their three verifier profiles preserve differences between the original source
versions; do not substitute one profile for another.

## Check the installation before running

Using the launch interpreter, resolve the selected profile:

```bash
/path/to/launch/.venv/bin/python -c 'from core.runtime_control.verifier_provider import resolve_runtime_verifier; print(resolve_runtime_verifier("legacy-7689fd58-verifier-v1").identity().model_dump_json())'
```

Repeat with the execution interpreter. Both must print the same identity. A
missing module means infra is too old; a missing profile means this package is
not installed there. An unqualified assembly or different identity means the
source pair is not verified together. Fix the installation; do not remove the
historical arguments or bypass the check.

Use a fresh workspace. Do not edit old locks, overwrite archived evidence or
import old timing-calibration entries as though the new profile had produced
them. New measurements record the selected profile's identity. Match the original
host timezone when reproducing historical timestamp decisions: the old rule
interpreted recorded times using that timezone.

This package restores the tested timing decisions; it does not restore deleted
artifacts or guarantee identical new LLM responses, trained weights or scores.
The [technical contract](contract.md) and [current qualification results](qualifications/observation-order/report.md)
list the original sources, test boundaries and remaining qualification.
[Prompt adapters](../prompt_compat/README.md) and
the [static estimator adapter](../preflight_compat/README.md) remain separate
historical requirements.

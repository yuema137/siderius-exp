# Historical timing decisions

Use this package when you want a **new external workspace** to apply a paper
experiment's original timing rules. Ordinary tutorials use the framework's
corrected default and do not need this package. Installing it changes no default.

**Release qualification is in progress.** Offline timing and installation checks
pass with infra `ec92186d`, including the historical prompt comparisons, but the
standard exp installation does not yet install that candidate. Independent
review and final release source pairing remain open.
The commands below explain the installation procedure; they are not yet a
ready-to-run public installation guide.

The paper runs estimated training time from observed steps. Their rules could
reject a short phase even after every requested step had finished, because too
few observations were stable. New infra can use the actual time of completed
work. This package preserves the original timing algorithms and selects the
original admission rule explicitly. The separate historical prompt adapters can
then present those decisions to the agents in the original format.

## Prepare your own launch

1. Start with the recorded unit in the [paper artifact reference](../../paper-artifacts.md).
   Copy its launch configuration and complete task package to your own project.
   Remap data paths and select a new output workspace. Keep its other historical
   profiles, model routing, budgets and task settings.
2. Install the package in the Python environment that launches infra **and** the
   environment that executes training, if they are different. From your exp
   checkout, after the normal environment setup, run:

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
4. In your copied `llm/agents.json`, set `tune.planner_strategy` to the value in
   that unit's `llm_configuration` section of the same overlay. Install the
   [planner compatibility package](../planner_compat/usage.md#install-into-the-environment-that-will-run-infra)
   in the launch environment. For TESS `nop_004`, the setting is:

   ```json
   {"tune": {"planner_strategy": "legacy-9b78d505cb11-paper-verifier-v8"}}
   ```

   Merge this field into your existing configuration; keep its model, credentials
   and other routes. This explicit planner profile presents the old timing
   format to the agent while saved results retain the new verifier identity.
   Selecting only the timing algorithm does not restore the old prompt format.

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
them. New measurements record the selected profile's identity.

This package restores the tested timing decisions; it does not restore deleted
artifacts or guarantee identical new LLM responses, trained weights or scores.
The [technical contract](contract.md) and [qualification results](presentation-qualification.json)
list the original sources, test boundaries and remaining qualification.
[Prompt adapters](../prompt_compat/README.md) and
the [static estimator adapter](../preflight_compat/README.md) remain separate
historical requirements.

# Historical preflight estimates

This optional package lets a **new workspace** use the static memory formulas
and inference batch decisions from SIDERIUS `078b23ca7d88`. It is for checking
historical experiments. Ordinary runs should use infra's corrected native
accounting.

For example, the old estimator charges a shared layer's parameters once for
each recorded forward call. The native estimator counts its registered state.
This package explicitly chooses the old arithmetic; the saved record identifies
that choice. It does not rewrite native estimates or archived results.

The package does not launch training, call an LLM, or measure GPU peaks.
Matching inputs and prompts does not guarantee the same generated model,
weights, or score.

## Install in the environment that runs infra

The current package targets the exact framework revision in the repository's
`SIDERIUS_REVISION`. Its [final-pair report](qualifications/final-pair/report.md)
records the source review, executed checks and limits. Use `static_only` and leave
`gpu_execution_policy` unselected for this historical view. Newly measured/protected
execution evidence is outside that qualification.

Earlier entries, including `7c869e67`, remain evidence for their recorded source
pairs. Keep the corresponding old package when reopening an old workspace; the
new qualification changes package identity. Frozen experiment declarations and
archived results are preserved.

The standalone `5aa404263c8dfb40662a8ab2f55225d801786984` entry in
[qualification.json](src/siderius_preflight_compat/qualification.json) qualifies
only the estimator; it lacks the storage producer required by v7 and is not a
complete installation for this workflow. An empty `assemblies` list means
qualification is unfinished; historical launches fail until a reviewed
candidate is listed.

Set these variables to the two checkouts on your machine, then install both
packages into the selected infra checkout's own environment:

```bash
export INFRA_CHECKOUT="/path/to/SIDERIUS"
export EXP_CHECKOUT="/path/to/siderius-exp"
uv pip install --python "$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/preflight_compat" \
  "$EXP_CHECKOUT/experiments/shared/planner_compat"
```

If the parent process and isolated preflight worker use different environments,
both must contain these exact packages. A missing package, changed source, or
unqualified infra assembly produces an error before probing. Installation alone
does not enable historical estimation.

Check the installation before creating the new run:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/preflight_compat/check_installation.py" \
  --infra-checkout "$INFRA_CHECKOUT" \
  --output "$HOME/preflight-installation.json"
```

Success writes a JSON receipt with `selected_checkout_assembly_match: true`,
`child_identity_match: true` and `unknown_assembly_refused: true`. It records
the commit actually checked separately from the reference commits whose source
assembly was qualified. This confirms that the selected checkout, parent and
child load matching qualified code, including after a normal merge changes the
commit number. Unknown framework code is still rejected.
It does not test API credentials, your dataset, or training. If it fails,
check the reported revision/package mismatch before launching.

## Select it in your external task package

First copy your complete task package into your own project directory, keeping
its relative resources together. Keep the original task and experiment files
unchanged. Edit the **copied** composition manifest:

```yaml
preflight_estimator: legacy-078b23ca-preflight-v1
inference_preflight:
  mode: static_only
  max_batches: 3
```

Code that already builds external task packages can call
`siderius_preflight_compat.configuration.historical_task_composition(manifest)`.
It returns a deep copy with both declarations. If the manifest already selects
`static_only`, it preserves its valid `max_batches` value. A conflicting or
malformed explicit policy raises instead of being overwritten. The helper
does not copy files, launch anything, or import an old workspace.

`static_only` keeps a static inference refusal as a refusal. For example, if
static inspection rejects inference batch 1, a historical run stops there;
it does not launch the new bounded measurement that could admit that batch.
`max_batches` remains part of the declared policy identity, but launches no
measurement while `static_only` is selected.

In your copied LLM configuration, explicitly select the matching historical
planner under `tune.planner_strategy`:

| Historical task path | Planner |
| --- | --- |
| TESS, LIGO, TIDMAD NoPrior | `legacy-9b78d505cb11-paper-storage-v7` |
| Project8, TIDMAD analysis-on | `legacy-9b78d505cb11-paper-late-storage-v7` |

This v7 planner first projects qualified storage evidence, then delegates to
the guarded v6 preflight view. Both checks must pass.

Other historical settings, prompt profiles, model routing, datasets, and task
plugins still need their existing verified bindings. The estimator selection
does not supply those settings. Use a new experiment/run identity and an empty
output workspace; do not resume an old lock in place.

The new evidence includes the estimator's source and framework identities.
The historical planner accepts only a qualified historical estimator identity.
It rejects native corrected numbers instead of silently presenting them as
historical numbers. V6 and v7 also reject any record carrying
`memory.inference_verification`, including a null or malformed value: the new
admission path has no qualified historical prompt view. Archived version 1
inputs without that field remain readable.

## Check the scope of the evidence

[The technical contract](contract.md) specifies the arithmetic, selection,
qualification, and tests. Frozen reference fixtures exercise completed static
calculations and batch search with bounded synthetic observations. They do not
establish actual GPU peak accuracy or replay unavailable historical requests.
The compatibility package intentionally leaves the remaining conservative
activation estimate unchanged.

The [qualification report](parity-report.md) records the reviewed candidate,
installed identities and the exact limits of the completed offline checks.

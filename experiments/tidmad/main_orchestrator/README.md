# TIDMAD external-orchestrator deployment preparation

Prepare one exact runtime pair and one joint prior selection for a Codex caller.
This is an **operator-only candidate preparation command**, not a launcher or
an agent-visible task package. It never starts the scientific clock or calls an
LLM, trains, scores, or changes any file in `tasks/tidmad`.

After installing this exact checkout with `uv sync --group dev --frozen`, use
its own Python and an infra checkout matching `SIDERIUS_REVISION`:

```bash
.venv/bin/python -m experiments.tidmad.main_orchestrator.prepare \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 --prior off --output /path/to/new/O-NoPrior-0-3

.venv/bin/python -m experiments.tidmad.main_orchestrator.prepare \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --band 0-3 --prior on --output /path/to/new/O-Full-0-3
```

Only `--prior` changes treatment: `on` means `O-Full`, `off` means `O-NoPrior`.
Both retain literature review and use the same versioned agent-model JSON. No
separate advice-only or analysis-only state is accepted. Each output directory
must be fresh; changing a flag does not resume an existing unit under a new arm.
The CLI verifies clean source checkouts, source/lock/install pins, exact advice
identity and the real native analysis binding. Missing prerequisites fail.

## Generated materials and visibility

`deployment.json` records the selected scope, identities, advice routing and
remaining launch blockers. `composition.yaml` is an additive operator overlay
referencing the original task files. `agent-models.json` copies the shared routing.
Full additionally has `analysis-policy.yaml` and the exact fixed-Full `advice.json`;
NoPrior emits neither and carries no advice content or analysis binding.

**Do not mount this output or the whole exp repository into the coding agent.**
The operator composition references private scorer code. Assemble a separate
agent-visible overlay onto the existing frozen common public view using
[the wrapper assembly instructions](../orchestrator_wrapper/PACKAGING.md).
Expose only the permitted advice/policy/routing and native capability bindings;
private scoring stays in the trusted executor. A Python binding check here does
not provision that service or certify physical data access.

## Candidate Full policy: review before freezing

The proposed policy reuses the raw-only diagnostic configuration in
`data_analysis_raw_characterization`, generalized to the chosen band's complete
file list and frozen-pool task-data identity. It exposes sampled validation
**input only**, not validation targets, predictions or residuals; no historical
inference or generated-skill promotion. Existing core-analysis/time-series packs
are available. Inherited candidate limits: 45 seconds per analysis call, 12 seconds
per skill, 8 GiB host memory, CPU, 10 task-stratified windows of 262144 samples,
seed 20260915. These are analysis bounds, not the 40000-sample model window or
additional run time. They remain a proposed main-run policy, not a qualified
Full freeze; both fixed-Full and orchestrator-Full need the same reviewed policy.

Human advice is copied byte-for-byte from the matching fixed-Full authority and
rendered by the existing native loader. Its current text includes fixed-workflow
100-iteration/3-round/2-epoch/40-GiB context; review its applicability and parity
before the Full freeze. This preparation does not silently impose those fixed
scheduling limits on the orchestrator or rewrite the frozen advice.

## Remaining deployment work

Every receipt explicitly says `launch_ready: false`. Bind and verify the existing
public package, data scope, protected infra/task mounts, private evaluator route,
outer Codex version/settings, continuing 24-hour clock, recovery, candidate
retention and replay. Native role routing is shared with the fixed workflow;
outer-controller routing/version is a separate launch identity. No 24-hour run
is authorized by preparation. `Full` also requires operator review/freeze of
analysis policy and matched fixed-Full wiring; do not call a partial treatment Full.

## Before an H100 smoke

Read the [local preparation findings](LOCAL_PREPARATION.md) and
[draft smoke run sheet](SMOKE.md). Eight public/toolbox assemblies passed byte
identity checks. The operator resolved the CLI advice-scope conflict through
[TREATMENT_SCOPE.md](TREATMENT_SCOPE.md); copy it into the agent workspace and
link it explicitly from `SIDERIUS-RUN.md`. The missing private native execution
route and the other recorded deployment requirements still block launch. These findings also separate
reusable toolbox contracts from task-specific deployment adaptation.

The [execution boundary](EXECUTION_BOUNDARY.md) records baseline reuse and the
remaining native-call compatibility issue. No new supervisor or submission
service is required by this preparation.

## Shared native execution settings (2026-09-19)

Preparation now writes `execution-policy.json` by projecting the existing fixed
workflow JSON. The receipt pins both source and projection digests. Missing
explicit fields fail closed. Current epoch ceilings are 100 for common, Trial
and Formal execution; budgets are 30/120 minutes and 40 GiB, with the same
Formal scope, 0.2 downstream reserve and disabled prediction watchdog. Existing
native time-budget continuation and last-completed-epoch behavior apply when
these settings are actually bound to the native executor.

Codex still chooses capability order, repeated calls and parallelism. Fixed
`num_iterations` and `max_rounds` are not controller limits for the orchestrator.
The policy file is operator-owned, with reviewed values restated in the additive
run declaration. It is not proof that a deployed worker enforces those values:
`execution_policy_enforcement` remains `pending_deployed_native_route`. Do not expose private composition or scorer source to make native imports
succeed. Frozen task bytes are unchanged.

[Current qualification](QUALIFICATION.md) separates completed preparation and
agent-interface evidence from the missing real-task H100 chain. The existing
baseline harness and scoring entry are the deployment basis. Extra generic
isolation services and Full qualification are not NoPrior launch gates.

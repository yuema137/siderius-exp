# PhyTS TESS — external orchestrator

The third way of running the same static task: an external caller selects
SIDERIUS capabilities itself, rather than following the fixed workflow's
pre-designed path.

**Nothing here is implemented.** This page records what the condition needs
and which prerequisites are already satisfied, so that whoever builds it
starts from the constraints rather than rediscovering them.

## Shape

Unlike [`../main_fixed_workflow/`](../main_fixed_workflow/README.md), this is
not a launcher. TIDMAD's equivalent is an **operator-only preparation
command**: it never starts a clock, calls an LLM, trains or scores. It emits a
deployment bundle — a resolved composition overlay, agent-model routing, the
selected treatment's advice and policy — that an external caller then runs.

The same three-axis split applies. `tasks/phyts_tess` stays the static task;
this directory would own one treatment; the information treatments already in
[`../information_treatments/`](../information_treatments/README.md) would be
reused rather than duplicated, since the prior contrast is the same contrast.

## Already satisfied

- **The task composes.** `compose_run_task_bindings` resolves the manifest
  against the pinned framework, so a composition overlay has something real
  to reference.
- **Deliverable and scoreability are task-owned.** The task names its own
  artifacts and carries an executable scoreability contract, so an external
  caller's output is validated by the same authority a chain's is.
- **The answer-separation exists.**
  [`tools/build_views.py`](../../../tasks/phyts_tess/tools/build_views.py)
  already produces the agent-visible and evaluator-private views; the
  orchestrator condition needs exactly this property and should reuse it
  rather than build a second one.

## Not satisfied, and why each matters

1. **The public/private boundary is not drawn.** The composition references
   the task's own scoring code. An external caller must not receive it: the
   metric and its scoreability contract stay in the trusted executor. Deciding
   precisely which files cross is a review decision, not an inference.
2. **No analysis policy.** If the full-prior arm is used, the caller's
   analysis must expose validation **input only** — never targets,
   predictions or residuals. TIDMAD's policy pins call timeouts, memory, CPU,
   window counts and a seed. None of those bounds have been chosen for TESS.
3. **No native capability binding.** For the caller to train through SIDERIUS
   rather than around it, model export, restore and a training channel have
   to be bound. `experiments/shared/` carries that machinery for TIDMAD's
   shape; whether it transfers to a fixed-length single-channel task is
   unverified.
4. **No wrapper.** The agent-visible overlay is assembled separately from the
   operator bundle. Mounting this repository, or the bundle, into the caller
   would expose private scoring.

## Do not

Do not mount `siderius-exp` or an operator bundle into an external caller.
Do not reuse the fixed workflow's supervisor here — it starts a clock and
runs a chain, which is precisely what a preparation command must not do.

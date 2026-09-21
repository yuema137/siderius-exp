# Full prior V8: training-order search guidance

V8 retains V7's reference-scale encoder-decoder exploration advice and adds
one evidence-backed training-order hypothesis shared by fixed workflow and
orchestration consumers:

- The published band-specific FCNet processed files sequentially, whereas the
  completed Full rounds used global shuffle.
- Interpretation should keep this difference visible while it remains
  untested instead of prematurely assigning the score gap to architecture or
  capacity.
- The tuner may select the existing `order_strategy: "sequential"` capability
  when the evidence makes that experiment useful. It remains free to select
  shuffle or another higher-value experiment.
- Current sequential execution changes sample visitation order and keeps one
optimizer across files. It is a supported search direction, not a claim of
exact FCNet reproduction.

## Local planning qualification

On 2026-09-21, a planning-only smoke used the pinned SIDERIUS revision
`0b44e40505b99fd752526c1ff9e9fc97c219dde2` and `gpt-5.6-sol` with this V8
tuner advice. Its synthetic history contained three comparable, completed
shuffle runs over the same selected data and identified visitation order as
untested. The real tuner planner returned `order_strategy="sequential"` in
22.621 seconds. `ExperimentPlan` accepted the output without fallback, and the
shared resolver selected `agent_proposal` with ascending file order
`[0, 1, 2, 3]`. No training, scoring, operator ordering override or task data
was used. This checks reachability and executable routing; it does not require
the agent to make the same choice under different evidence.

The inherited V7 guidance continues to require:

- Keep a research ledger and an explicit sequence of controlled hypotheses.
- Compare competing explanations, including architecture, parameter capacity and
  expressive power, optimization, data coverage, objectives and execution artifacts.
  Reassess unsuccessful diagnoses; choose experiments freely based on evidence
  and remaining time, without mandatory capacity tests or exhaustive ablations.
- Distinguish architecture families and independent training from calibration,
  seed, output-rendering and ensemble variants.
- Stop low-information sweeps based on evidence, without a fixed trial quota.
- Separate automatic best score from scientific support; document concerns and
  use authorized controls, without rewriting receipts or eligibility.
- Respect useful optimization, existing budgets, task rules and data access;
  neither parameter count nor resource consumption is a target by itself.
- Prefer an FCNet-informed encoder-decoder variant and incremental improvement
  before bolder departures. Start above 100M parameters when feasible, with the
  approximately 323M published reference as the preferred comparable scale and
  greater capacity as a legitimate option. These are recommendations, not hard
  acceptance thresholds.

`manifest.json` binds the English advice bytes and references the unchanged
four V6 DA policies (600 seconds per invocation). Original V6 and V7 artifacts
remain intact. No task, infra, scientific budget, NoPrior treatment or running
service is changed. This is advice, not an order-strategy override, scheduler
or compliance guarantee.

Use [Full input preparation](../../main_fixed_workflow/FULL_LAUNCH.md) from the
selected revision. New external inputs must be prepared for V8; existing V6 or
V7 receipts must not be relabeled. Orchestration must explicitly bind this same
manifest/advice when its deployment is qualified; importing the shared helper
alone does not prove that a native agent receives the advice.

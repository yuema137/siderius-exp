# Full prior V7: research strategy

V7 retains V6's reference-scale encoder-decoder exploration advice and adds
research-level guidance shared by fixed workflow and orchestration consumers:

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

`manifest.json` binds the English advice bytes and references the unchanged
four V6 DA policies (600 seconds per invocation). Original V6 artifacts remain
intact. No task, infra, scientific budget, NoPrior treatment or running service
is changed. This is advice, not an enforced scheduler or compliance guarantee.
No new real training test or orchestration qualification is claimed.

Use [Full input preparation](../../main_fixed_workflow/FULL_LAUNCH.md) from the
selected revision. New external inputs must be prepared for V7; existing V6
receipts must not be relabeled. Orchestration must explicitly bind this same
manifest/advice when its deployment is qualified; importing the shared helper
alone does not prove that a native agent receives the advice.

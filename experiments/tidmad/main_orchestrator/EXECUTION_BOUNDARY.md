# Baseline-compatible orchestration execution

The operator requires a clean comparison: the existing Codex baseline room,
with the SIDERIUS toolkit added. Reuse its research account, public task/data,
network/GPU access, supervisor/continuing clock, scoring command and collection.
Protect the installed infra and frozen task; add no unrelated scratch restrictions.

The baseline research service permits its narrowly authorized sudo scoring
command (`NoNewPrivileges=false`). Do not impose `NoNewPrivileges=yes` on that
research service and then replace the working scoring route to compensate.
Evaluator-owned inference keeps the baseline evaluator's existing restrictions.

The expanded supervisor, socket submission service and split-validation runtime
have been withdrawn from this release candidate. Their code/evidence remains in
history at exp `85a2191` and infra `8b416f88`; component passes from that design
are not evidence that this baseline-compatible deployment works.

## Selected runtime bindings

The baseline withholds official validation inputs/truth and private scorer code
from research, while allowing `tidmad-score` feedback. The additional public
composition selects `CandidateEvaluationMetric` and retains the frozen scientific
declaration without importing private scorer code. Bind the original baseline
candidate evaluator in the same process that invokes the tuner; see
[submission](SUBMISSION.md). Without that binding, a candidate-only metric
refuses execution before training.

Per-epoch validation is a separate `ValidationDeployment` binding. Its native
training launcher invokes the protected runner, which materializes private data
and returns admitted loss observations. Row counting uses the public task scope
declaration. The research-side resource probe retains its public training batch
and omits local validation-input materialization when complete evaluation is
bound. The protected complete evaluator owns inference; its actual execution
must verify the exported candidate's interface.

Resolve the smallest actual invocation incompatibility using the existing task
and evaluator contracts. Do not expose private files, disable native validation,
change the objective/scope or claim an unconnected service is operational.
Record any necessary scientific-contract change for operator decision rather
than silently choosing it. New general isolation features are not launch gates.

The operator subsequently authorized an additive private-loss interface only
for models actually trained by SIDERIUS, including custom objectives admitted by
automatic review with retained evidence/refusal reasons. This does not authorize
direct target access, arbitrary analysis, or changes to the frozen evaluation
package. [Admission contracts](../../shared/validation_admission.md) record the
implementation boundary and unfinished deployment work. Installed H100 training
and complete-tuner evidence, exact tested revisions and remaining live-review
gaps are recorded in [qualification](QUALIFICATION.md).

Use [smoke](SMOKE.md) for the acceptance scope of the selected release pair.

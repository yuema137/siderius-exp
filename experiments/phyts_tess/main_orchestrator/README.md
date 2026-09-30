# PhyTS TESS — external orchestrator

The third way of running the same static task: an external caller selects
SIDERIUS capabilities itself, rather than following the fixed workflow's
pre-designed path. This directory is the operator-side preparation for that
condition. It never starts a clock, calls an LLM, trains or scores on its own.

**Shortest route** (operator, on the host):

```bash
python -m experiments.phyts_tess.main_orchestrator.prepare \
    --siderius-checkout <framework> --agent-view <views>/agent --output <bundle>
python -m experiments.phyts_tess.main_orchestrator.verify_launcher_policy --installed /etc/tess-native/policy.json
python -m experiments.phyts_tess.main_orchestrator.verify_evaluator_policy --installed /etc/tess-native/evaluator.json
bash experiments/phyts_tess/main_orchestrator/machine/probe_authorization.sh
```

Host privilege work that no committed file can perform — accounts, wrappers,
sudoers, ownership — is listed in [DEPLOYMENT.md](DEPLOYMENT.md). The
single-host, two-account boundary and what it does and does not isolate is
recorded in [EXECUTION_BOUNDARY.md](EXECUTION_BOUNDARY.md).

## What the caller receives, and what it does not

The same three-axis split as the fixed workflow: `tasks/phyts_tess` stays the
static task, this directory owns one treatment, and the information
treatments in [`../information_treatments/`](../information_treatments/README.md)
are reused rather than duplicated.

The caller receives the **answer-free agent view** (identities, no
evaluated targets), a **public composition** whose metric is
`CandidateEvaluationMetric` — a metric that refuses to execute unless a
complete evaluator is bound in the caller's process — and a **public
runtime** of explicitly listed modules. It never receives `scoring.py`, the
identity manifest with validation targets, or anything in
`OPERATOR_ONLY_MODULES`.

## Two privilege boundaries, mirrored from TIDMAD

| boundary | caller invokes | runs as | source of truth |
|---|---|---|---|
| native training | `sudo -u tess-coordinator /usr/local/sbin/tess-native-training …` | coordinator | `native_handler.py`, `/etc/tess-native/policy.json` |
| scoring | `sudo -u tess-coordinator /usr/local/sbin/tess-score …` | coordinator | `tess_score.py`, `/etc/tess-native/evaluator.json` |

Scoring runs on the caller's side as `TessCandidateEvaluator`
([`tess_evaluation.py`](tess_evaluation.py)): it exports the trained
candidate, invokes `tess-score`, and reads back a coordinator-owned receipt
bound to the exact candidate bytes and invocation
([`tess_receipt.py`](tess_receipt.py)). The coordinator's side
([`tess_score.py`](tess_score.py)) snapshots the candidate, runs inference
over the complete validation split against the evaluator view's own truth,
applies the task's scoreability contract, its R-squared metric, its
observational secondaries and its declared Health family, and publishes the
receipt. Nothing is scored on the caller's side, and nothing is deleted on
the coordinator's: a scored candidate is retained, a failed one is set aside.

## File map

| file | side | role |
|---|---|---|
| `prepare.py` | operator | resolve and write the bundle: `caller/`, `evaluator/`, `deployment.json` |
| `public_task_tree.py`, `public_composition.py`, `public_runtime.py` | operator | what crosses to the caller, as explicit lists |
| `public_data_path.py` | caller | the task data path over the answer-free view |
| `execution_policy.py`, `draft_launcher_policy.py`, `stage_policy.py`, `verify_launcher_policy.py` | operator | the native-training policy: bounds, drafting from the deployment, deadline, verification |
| `native_handler.py`, `validation_scope.py`, `validation_rows.py` | coordinator | the native-training binding and its validation-scope admission |
| `candidate_model.py` | both | the candidate contract and the one loader both sides use |
| `tess_evaluation.py`, `tess_receipt.py` | caller | the bound evaluator and the receipt reader |
| `tess_score.py`, `verify_evaluator_policy.py` | coordinator | the scorer behind `tess-score` and its policy check |
| `supervisor.py` | operator | the campaign clock: one unit, process-group kill at the deadline |
| `caller/SIDERIUS-RUN.md`, `caller/task.md`, `caller/TREATMENT_SCOPE.md`, `caller/run/*.json` | caller | the run declaration for `onp_001`, the task brief, the O-NoPrior treatment, the two settings the binding loads |
| `assemble_workspace.py` | operator | the toolkit payload plus those documents, byte for byte, instantiated for a run id |
| `SUBMISSION.md` | caller | how the caller's process binds the evaluator and the protected validation launcher |
| `SMOKE.md` | operator | what one short run must show before the formal unit |
| `machine/install_host.sh`, `machine/install_evaluator.sh` | host | accounts, wrappers, sudoers, the directories each side owns |
| `machine/probe_authorization.sh`, `machine/probe_namespace.py` | host | the sudo route up to capture (PASS is a named refusal); the namespace up to a CUDA-visible import |

## Do not

Do not mount `siderius-exp` or an operator bundle into an external caller.
Do not reuse the fixed workflow's supervisor here — it starts a clock and
runs a chain, which is precisely what a preparation command must not do.
Do not give the caller the `evaluator/` view, whatever the ownership of the
directory it sits in today.

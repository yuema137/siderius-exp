# PhyTS project8: NoPrior fixed workflow

This experiment binds [the prepared task](../../../tasks/phyts_project8/README.md)
to the native fixed workflow. Deployment status and historical run receipts
are tracked separately from this experiment configuration.

- [workflow.json](workflow.json): one Trial followed by one Formal per proposal,
  agent-controlled Trial training fractions, full-pool full-epoch Formal training,
  fixed 10% epoch-loss validation, full
  Formal validation, and the requested stage time/VRAM limits.
- [agents.json](agents.json): OpenAI gpt-5.6-sol, medium reasoning, through the
  framework gateway.
- [information_treatment.yaml](information_treatment.yaml): advice and Data
  Analysis disabled. Literature Review stays enabled, matching the meaning
  of NoPrior in the TIDMAD experiment.
- [literature_review.yaml](literature_review.yaml): dynamic literature search;
  no hand-selected root papers or preferred models. This file must be passed
  by the launcher as `--ml_lit_review_config`.

The 100-epoch ceiling inherits the framework limit; it does not force the student's
20-epoch recipe. The campaign clock is 24 hours;
Trial/Formal wall-clock and VRAM values are declared once in workflow.json.
No final offline test evaluation is enabled.

## Formal training data policy

New runs use operator-owned Formal training scope with `formal_portion=1.0`
and `formal_train_portion=1.0`: all 40,000 prepared training events belong to
the pool, and every epoch selects that full pool. Trial sampling remains
agent-controlled. Epoch validation uses its fixed 10% snapshot; final Formal
evaluation uses all 5,000 validation events. Time budgets and epoch caps still
determine how many complete epochs fit.

The workflow fixes `train_config.drop_last=false` for Trial and Formal, retaining
the incomplete final batch. For example, Formal batch size 128 uses 313 steps,
including the final 64 events. Completed-epoch sample counts are recorded in
`training_history.training_samples`; training loss is weighted by batch size.
Generated models must support partial batches.

Both roles use `train_config.target_standardization=training_pool_global`.
The framework fits one global target mean and population standard deviation
from the actual authorized training pool, never validation targets. Loss uses
standardized target and prediction values; exported inference restores the
original target units. Statistics travel with the checkpoint and fitting time
counts toward the attempt budget. Constant or nonfinite targets fail explicitly.
This does not change the frozen dataset or preprocessing.

These policies are staged against the repair branches. Review, CI, deployment
qualification and a final released dependency pin remain required before launch.

Both Trial and Formal export the earliest checkpoint with minimum loss on
their fixed training-validation snapshot, through the workflow rule
`train_config.checkpoint_selection=best_validation_loss`. Training still runs
until its time budget or epoch cap is reached; scientific early stopping is
not enabled. Final scoring does not select checkpoints. The exported epoch
and its validation loss are recorded in `selected_checkpoint`.

This policy supersedes the agent-owned Formal fractions used by run-2, which
was stopped for diagnosis. Historical results and workspaces retain their
original settings; this change requires a fresh run and does not authorize a
restart by itself. The frozen task, splits and preprocessing are unchanged.

## Native short qualification

Run from the exact exp checkout after `uv sync --group dev --frozen`:

```bash
OMP_NUM_THREADS=2 .venv/bin/python -m experiments.shared.prepared_regression_smoke \
  --composition tasks/phyts_project8/compositions/regression.yaml \
  --data-dir /path/to/prepared/project8 \
  --workspace /path/to/new-qualification-workspace --device cuda --attempts 2
```

The workspace must not exist. The tiny operator-owned model trains on 128
rows for one epoch, validates on the actual frozen 10%, and scores the whole
validation split twice. Receipts include per-stage timings, exact populations,
export/restore loss parity and an independent global RMSE calculation.
This is not an autonomous-agent smoke or a private-worker isolation test.

Before a formal launch: qualify the real agent loop (including a second
iteration), effective resource admission, deadline/collection behavior,
provider credentials and the execution-account boundary; review/freeze the
source pair; collect and physically remove qualification artifacts from the
fresh campaign area. Keep all runtime artifacts outside repositories and
prepared data. Formal launch identity must record tags/SHAs and UTC deadline.

## Formal launch and resume

The experiment's [unit.json](unit.json) owns the campaign duration. The trusted
supervisor hashes all prepared arrays and checks both clean Git revisions and
the installed framework pin before creating a clock. Invoke it using the exact
exp checkout environment, with the dedicated non-root worker account already
provisioned:

```bash
sudo .venv/bin/python -m experiments.shared.prepared_workflow_unit \
  --experiment experiments/phyts_project8/main_fixed_workflow \
  --siderius-checkout /path/to/SIDERIUS \
  --data-dir /path/to/prepared/project8 \
  --unit-dir /work/units/project8-no-prior-run1 \
  --run-name project8-no-prior-run1 --runner phyts-workflow
```

This prints preflight evidence and starts nothing. After review, add `--launch`
and `--credential-file /etc/siderius/phyts-openai.json`. Keep that credential
file root-owned, mode 0600, outside source and backups. The operator owns the
unit directory, `launch.json`, events and logs; the worker owns only workspace
and calibration directories. Sources and prepared arrays remain read-only.

A resume reuses the same clock and refuses changed inputs. A permanent chain
halt is preserved. At the deadline the supervisor terminates the process group;
the deployment service must additionally use `KillMode=control-group`.

The fixed workflow's native evaluator/trainer account can materialize validation
arrays for loss and scoring. This is the native fixed-workflow execution boundary,
not the separate external-orchestrator private-worker service. Prepared data
remove raw clean/noise/auxiliary-truth paths; they do not provide a proof against
arbitrary malicious generated Python. No coding-agent shell is part of this arm.

Collect the entire unit directory to operator storage with checksums, excluding
credential files (which are outside the unit). Qualification units and formal
units use separate names and directories. Never carry a qualification model,
calibration, generated plugin library or launch record into a fresh formal unit.

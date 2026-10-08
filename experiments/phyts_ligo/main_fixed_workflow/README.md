# PhyTS ligo: NoPrior fixed workflow

This experiment binds [the prepared task](../../../tasks/phyts_ligo/README.md)
to the native fixed workflow. The paper archive records the historical
`ligo-no-prior-run2` launch and planner startup. See the
[paper artifact reference](../../paper-artifacts.md) for its exact source pair
and evidence limits; those records do not qualify a new deployment.

- [workflow.json](workflow.json): one Trial followed by one Formal per proposal,
  agent-controlled training fractions, fixed 10% epoch-loss validation, full
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
20-epoch recipe. The campaign clock is 12 hours;
Trial/Formal wall-clock and VRAM values are declared once in workflow.json.
No final offline test evaluation is enabled.

## Native short qualification

Run from the exact exp checkout after `uv sync --group dev --frozen`:

```bash
OMP_NUM_THREADS=2 .venv/bin/python -m experiments.shared.prepared_regression_smoke \
  --composition tasks/phyts_ligo/compositions/regression.yaml \
  --data-dir /path/to/prepared/ligo \
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
  --experiment experiments/phyts_ligo/main_fixed_workflow \
  --siderius-checkout /path/to/SIDERIUS \
  --data-dir /path/to/prepared/ligo \
  --unit-dir /work/units/ligo-no-prior-run1 \
  --run-name ligo-no-prior-run1 --runner phyts-workflow
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

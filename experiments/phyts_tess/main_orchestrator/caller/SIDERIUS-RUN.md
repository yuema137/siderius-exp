# SIDERIUS run declaration — PhyTS TESS, orchestrated, O-NoPrior

Run id **`onp_001`**. This is the operator-supplied run declaration the
toolkit's `AGENTS.md` tells you to read first. It names concrete paths on
the host **lilab**; it is not a template. `task.md` beside it is the task
brief and `TREATMENT_SCOPE.md` the information-treatment declaration; both
are yours to read, neither is yours to change.

Every path below is absolute on the host. `D` abbreviates
`/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration` in prose only.

## Identity

| what | value |
|---|---|
| condition | O-NoPrior (orchestrated, no operator prior) |
| task package | `tasks/phyts_tess`, agent view — see below |
| framework revision | SIDERIUS `0b44e40505b99fd752526c1ff9e9fc97c219dde2` (v0.2.9) |
| framework install | `D/framework`, its own venv `D/framework/.venv` (CPython 3.12.13 at `D/python`) |
| interpreter for every helper and node invocation | `/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration/framework/.venv/bin/python` |
| published exp runtime (source root for `experiments.*`) | `/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration/runtime` — its `public-runtime.json` records the exp revision it was published from |
| composition | `/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration/bundle/caller/composition.yaml` |
| execution policy | `/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration/bundle/execution-policy.json` |
| deployment receipt (operator-only, for the record) | `D/bundle/deployment.json` |

Protected, read-only to you: `D/framework`, `D/runtime`, `D/bundle/caller`,
`D/views/agent`, the data root. You do not have, and must not look for,
`D/bundle/evaluator`, `/var/lib/tess-native`, or any committed identity
manifest.

## Task instructions and data

- Task brief: `task.md` in this workspace. Task package (agent view):
  `/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration/bundle/caller/tasks/phyts_tess/`.
  Read `declared/task_config.yaml` first.
- Agent view of the identities:
  `/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration/views/agent/`
  (`manifests/train.csv` with targets, `manifests/predict.csv` without).
- Data root, for every `data_dir`:
  `/home/klz/Data/SIDEREIS_DATA/phyts_tess/rundata/`
  (`tess_rotation_train.npz`, `tess_rotation_val.npz`; flux only).

**Authorized scope.** The complete dataset the profile describes is
authorized: 3,338 training curves, 442 validation curves. TESS declares no
partition vocabulary — the data path refuses `subset_ref` and
`target_partitions` — so a `DataScope` on any request is `null` (the
complete dataset); a training `portion` below 1.0 is a star-grouped
sub-draw the task performs itself. Formal evaluation is always the
complete validation split (`formal_eval_portion` 1.0 in the execution
policy), and the evaluator scores the complete split regardless of what a
request says.

## Capabilities and execution routes

| capability | state | route |
|---|---|---|
| Literature review | **disabled** (see `TREATMENT_SCOPE.md`) | none |
| Data analysis | **disabled**, no findings injection | none; the composition says `data_analysis: enabled: false` |
| Interpretation, Proposal, Implementation, Validation | enabled | native Python interfaces per the toolkit |
| Tuning | enabled | native `HyperparamTuningAgent`, with the two bindings below |
| Native training (protected) | enabled | `sudo -n -u tess-coordinator /usr/local/sbin/tess-native-training …`, invoked by the framework as `training_launcher` |
| Candidate scoring (protected) | enabled | `sudo -n -u tess-coordinator /usr/local/sbin/tess-score …`, invoked by the bound evaluator |

Bind both in the process that runs the tuner, exactly as
`experiments/phyts_tess/main_orchestrator/SUBMISSION.md` in the runtime
shows. The two settings files it loads are in this workspace:

`run/evaluation-settings.json`:

```json
{
  "command": ["sudo", "-n", "-u", "tess-coordinator", "/usr/local/sbin/tess-score"],
  "candidate_root": "/var/lib/tess-candidates/onp_001",
  "evaluation_root": "/var/lib/tess-evaluations",
  "run_id": "onp_001",
  "metric_declaration": "/home/klz/Data/SIDEREIS_DATA/phyts_tess/orchestration/bundle/caller/tasks/phyts_tess/declared/metric_r2.json",
  "metric_declaration_sha256": "08f7cb79ecb8fa5a070c1fcc4dcf94ec0ca2fb291b00a4d708165e45ec9c0eda",
  "evaluator_uid": 995
}
```

`run/validation-settings.json`:

```json
{
  "factory": "experiments.shared.validation_client_factory:create_validation_client",
  "settings": {
    "row_declaration": "experiments.phyts_tess.main_orchestrator.validation_rows:declared_rows",
    "deadline_epoch": 0,
    "max_metadata_bytes": 1048576,
    "max_state_bytes": 268435456
  },
  "training_launcher": ["sudo", "-n", "-u", "tess-coordinator", "/usr/local/sbin/tess-native-training"]
}
```

Set `deadline_epoch` to the unit deadline from `run/launch.json` (written by
the supervisor at launch); the launcher replaces every other validation
setting with its own. Every training request must select the composition
above as its `task_manifest`; the launcher admits it by path and digest.

Writable paths: your workspace `/home/tess-caller/workspace/onp_001` (this
directory), your tuner storage and generated-library root
`/home/tess-caller/work/onp_001` (the only path native training writes into,
as the coordinator), and your candidate root `/var/lib/tess-candidates/onp_001`.
Create the two run-scoped directories yourself before the first call.

## Execution bounds

From the execution policy, fixed for every tuner request; do not substitute
API defaults:

| field | value |
|---|---|
| `max_epochs`, `trial_max_epochs`, `formal_max_epochs` | 100 |
| `trial_time_budget_minutes` / `formal_time_budget_minutes` | 5 / 15 |
| `trial_vram_budget_gb` / `formal_vram_budget_gb` | 8 / 8 |
| `formal_training_scope_source` | `operator` |
| `formal_portion`, `formal_train_portion`, `formal_eval_portion` | 1.0 |
| `training_budget_reserve_fraction` | 0.2 |
| `runtime_watchdog` | false |

Trial portions are not fixed; they are yours.

## Model routing

All roles: provider `openai`, model `gpt-5.6-sol`, reasoning effort
`medium` — interpretation, proposal (comparison, reasoning, proposing),
implementation, validation, tuning (planner, reflector). The credential
arrives as `OPENAI_API_KEY` in your environment at launch; no other
provider is enabled. Which outer controller runs this workspace (product
and version) is recorded by the operator in `run/launch.json`, not chosen
here.

## Clock and resources

One unit of **six hours** on one RTX 5090, enforced by
`experiments/phyts_tess/main_orchestrator/supervisor.py`, which shares the
fixed workflow's `UNIT_SECONDS` and kills the whole process group at the
deadline. `run/launch.json` carries the immutable launch record and the
deadline epoch. Every capability call, your own reasoning, custom code,
failures and retries spend this one allocation; a restarted process does
not reset it. The 8 GiB VRAM budget is per training attempt, not the
card's capacity.

## Evidence and information sources

Authorized: the task package's agent view, the training data with its
targets, the receipts `tess-score` returns, and your own run history under
this workspace. No advice artifact, analysis findings or other run's
history exist for this condition, and their absence is not a setup error
(`TREATMENT_SCOPE.md`). Provider access does not authorize retrieving
scientific information from another source.

## Required artifacts

For every candidate you want evaluated: the exported candidate directory
(`model.pt`, `weights.pth`, `contract.json`, `native_reconstruction.json`,
`train_config.json`, retained `model/` source) under your candidate root,
and the receipt path it earned. Keep your request/output records per the
toolkit's artifact rules. After the deadline the operator takes the
eligible candidate with the highest receipt R-squared; there is no
final-scoring command for you to call.

## If something here is wrong

A missing path, an unreadable authorized input, a refused invocation or a
setting that contradicts the task package is a setup issue. Record it in
this workspace with the exact command and error, and report it before the
affected operation rather than working around it.

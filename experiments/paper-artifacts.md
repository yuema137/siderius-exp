# Paper artifact and reproduction reference

## Scope and authority

This is the agent-facing entry to the paper's experiment configurations,
recorded source revisions, compatibility evidence and known gaps. It is an
index of existing authorities, not a new treatment, launch authorization or
complete artifact bundle. The [tutorials](../tutorials/README.md) are simplified
workflow demonstrations; their three-iteration outputs are separate evidence.

The repository-root [SIDERIUS_REVISION](../SIDERIUS_REVISION),
[pyproject.toml](../pyproject.toml) and [uv.lock](../uv.lock) identify the installed
consumer dependency. Historical units identify their own source pairs. A new
framework default branch, installed compatibility adapter, or passing prompt
comparison does not silently update a historical unit's identity.

## Start from the recorded unit

The frozen [paper launch inventory](shared/planner_compat/paper-replay-369.json)
records eleven native workflow units: TESS, LIGO, Project8 dual representation,
four TIDMAD NoPrior bands and four TIDMAD analysis-on bands. Each entry records
launch parameters, source evidence, task/configuration references and the
historical planner selection. Its schema explicitly states that it is neither
an executable launcher configuration nor a complete artifact-replay receipt.

| Unit family | Scientific input and configuration owners | Source/evidence entry |
| --- | --- | --- |
| TESS `nop_004` | [task](../tasks/phyts_tess/README.md), [composition](../tasks/phyts_tess/compositions/rotation_regression.yaml), [workflow settings](phyts_tess/main_fixed_workflow/workflow.json), [agent routing](phyts_tess/main_fixed_workflow/agents.json) | [run record](phyts_tess/main_fixed_workflow/runs/nop_004/results.json), [dated analysis](phyts_tess/main_fixed_workflow/runs/nop_004/RESULTS.md) |
| LIGO `ligo-no-prior-run2` | [task](../tasks/phyts_ligo/README.md), [workflow](phyts_ligo/main_fixed_workflow/README.md), its `workflow.json`, `agents.json`, `information_treatment.yaml` and `literature_review.yaml` | [launch inventory](shared/planner_compat/paper-replay-369.json), [startup capture](shared/planner_compat/paper-startup-parity.md) |
| Project8 dual representation | [dual task contract](../tasks/phyts_project8/DUAL_REPRESENTATION.md), [experiment](phyts_project8/main_fixed_workflow_dual_representation/README.md), its frozen workflow and agent files | [launch inventory](shared/planner_compat/paper-replay-369.json), [startup capture](shared/planner_compat/paper-startup-parity.md) |
| TIDMAD NoPrior / analysis-on | [task](../tasks/tidmad/README.md), [fixed workflow](tidmad/main_fixed_workflow/README.md), [information treatment](tidmad/information_treatments/README.md) | [per-band launch inventory](shared/planner_compat/paper-replay-369.json), [recovered analysis inputs](shared/planner_compat/paper_inputs/tidmad-analysis/) |

The links above locate owners in this checkout. For historical replay, read the
files at the entry's recorded revision, not their latest contents. The inventory
pins infra `7689fd58…` for TESS, `0ab15736…` for LIGO, `349b6cd6…` for Project8,
`345c802d…` for TIDMAD NoPrior and `c0467447…` for analysis-on. Full hashes and
per-unit exp revisions belong to that inventory; do not replace them with the
root dependency pin.

TESS has a specific provenance limit. The run record reports exp
`12bd80af795be8402bab0dacfca6968054554b1d`; the later planner-replay inventory
leaves `exp_revision` null, and its startup report does not certify the original
exp revision. It instead demonstrates that assets from `8513deab…` reproduce
the archived task fingerprint. Those are different evidence claims. This page
preserves both and does not infer a fully certified source pair from a matching
fingerprint. The dated TESS record is still evidence that execution and scoring
occurred; it is not proof of complete recoverability of every artifact.

## Choose the claim before executing

| Goal | Required inputs and appropriate evidence |
| --- | --- |
| Learn how the system runs | [Tutorial notebooks](../tutorials/paper/notebooks/README.md), their external project settings and [demo receipts](../tutorials/paper/examples/README.md) |
| Inspect recorded scientific results | The selected unit's persisted records, treatment/data identity and dated analysis; retain omissions and failed attempts |
| Compare historical prompt inputs on newer infra | [Planner compatibility](shared/planner_compat/README.md), [prompt compatibility](shared/prompt_compat/README.md), their qualified framework assemblies and frozen fixtures |
| Re-evaluate an archived model | Exact model source, configuration, checkpoint, task and data identity, compatible execution code and independent evaluation receipt |
| Repeat a historical search treatment | Recorded source pair and launch settings, verified data, explicit provider/model availability and fresh workspace; stochastic trajectories and scores may differ |

The last two goals need artifacts that are not all distributed here. The tutorial
example bundle excludes full workspaces and original checkpoints. The planner
startup check requires the original SHA-checked model plugin. Missing artifacts
must remain a named limitation; they cannot be replaced by newly generated files
with the same names.

## Compatibility and version boundaries

The compatibility packages under [shared support](shared/README.md) preserve
selected historical presentation or resource decisions. Their contracts name
supported source assemblies, explicit selectors, comparison populations and
refusals. They do not restore all old runtime behavior or every conversation.
Installing a package is separate from selecting its profile in copied task/LLM
configuration, and a changed profile identity requires a fresh workspace.

At this documentation baseline, exp installs infra `e800fc1f…`. Newer framework
changes and their adapter-specific qualification remain separate from that
installation. In particular, the presence of newer storage or preflight profiles
does not establish that the root pinned installation supports their producers.
Read the adapter's qualification contract before choosing a profile.

Use a frozen environment in each selected checkout, as specified by
[CLAUDE.md](../CLAUDE.md#environment-and-launch-credentials). Remap machine paths
in external copies while preserving declared scientific meaning. Retain original
receipts and hashes; do not alter an old workspace lock to accept a new pair.
There is no repository-wide one-command paper reproduction route.

## Task documentation and bundle identity

The TIDMAD coding-agent builder includes tracked task documentation in its
agent-visible task view as well as its evaluator snapshot. The source owner is
[build_bundle.py](../deployments/tidmad_coding_agent_baseline/tools/build_bundle.py):
`_tracked_task_files` requires a clean task tree, `_copy_task_views` applies the
explicit scoring exclusions, and the bundle records exp HEAD, the task Git tree
and `public_task_view_sha256`. Visibility does not prove an agent read a file,
but changing a current README or STATUS file changes those view bytes.

The current documentation refresh therefore creates a new task-tree/view
identity without changing frozen scientific declarations, prompts or run records.
A historical paper condition must use its recorded exp checkout and builder,
or its verified archived bundle. The builder CLI locates the repository through
its installed module's `_repo_root`; it has no `--repo` switch. Run that revision's
builder from its own frozen environment. Do not substitute the latest task tree
or describe it as byte-identical to a historical agent view.

## Evidence limits

- The startup report captures four actual task startup pairs. It does not
  establish eleven complete conversation replays or recover every iteration.
- TIDMAD analysis-on composition/policy bytes match recorded receipt hashes;
  that does not replay the analysis agent's full conversation.
- Prompt equality and replayed saved replies do not imply identical future LLM
  responses, new trained checkpoints or scores.
- TESS validation R² is not a PhyTS held-out test score. Project8 input variants
  and different data splits must remain separate scientific conditions.
- Coding-agent and orchestrator experiments have their own
  [execution boundaries](tidmad/main_orchestrator/EXECUTION_BOUNDARY.md),
  launch records and frozen treatments. The native workflow inventory does not
  certify their artifacts or retrospective reviews.

This reference adds navigation and source/evidence reconciliation. No new API
calls, training, GPU qualification, artifact download or paper replay was
performed for this documentation change.

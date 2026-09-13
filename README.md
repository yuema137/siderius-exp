# siderius-exp

Private scientific task packages, campaigns, deployment configuration, and experiment provenance for SIDERIUS.

This repository is a consumer of the [SIDERIUS](https://github.com/Galileo-Sandbox/SIDERIUS) framework. It contains no framework fork. Every qualified experiment pins an exact SIDERIUS commit and uses only supported task-composition and plugin contracts.

## Repository boundary

- `tasks/` owns real scientific task packages and task-specific plugins.
- `campaigns/` owns frozen treatments, launch policy, budgets, and campaign records.
- `deployments/` owns explicitly configured infrastructure and scheduler surfaces.
- `experiments/` owns run manifests, result indexes, and reproducibility receipts.
- `provenance/` owns migration and source-lineage records.

Lightweight synthetic examples remain in SIDERIUS so the framework can validate its complete supported lifecycle without this repository.

## Independent ownership axes

| Axis | Owns |
|---|---|
| task | scientific semantics, data identity, objective, metrics, validity definitions, and task plugins |
| workflow | execution procedure, including Trial/Formal roles, round progression, promotion, retry, and persistence mechanics |
| experiment | one concrete task + workflow selection and its treatment values, advice, budgets, and result identity |
| campaign | coordination of multiple runs, arms, bands, or stages, including authorization and cross-run selection |

Trial and Formal belong to a workflow. Their presence does not make a run a
campaign: an ordinary experiment and a campaign stage may select the same
Trial/Formal workflow with different approved treatment values.

## Framework revision

The active dependency is pinned in `pyproject.toml`, repeated in
`SIDERIUS_REVISION`, and resolved to the same VCS commit in `uv.lock`. A
scientific run must additionally record both repository commit SHAs in its run
provenance.

There are deliberately two environments. This repository's `.venv` owns the
installed SIDERIUS dependency used by task plugins and tests. An explicitly
selected SIDERIUS checkout owns the interpreter used for framework scripts and
node children. Both must resolve the commit in `SIDERIUS_REVISION`; neither may
borrow the other's environment or use `PYTHONPATH` to overlay framework source.

## API-backed launch preparation

Before an API-backed experiment, prepare credentials in the same shell that
will own the launcher. Follow the pinned framework's detailed installation
procedure in [SIDERIUS installation](https://github.com/Galileo-Sandbox/SIDERIUS/blob/644975846ff95cb68aa07eacb1a49d63d54ef85c/docs/getting-started/installation.md),
using either a trusted external file with mode `600` or managed secret
injection. Enable shell export only around the source step (`set -a`, source,
`set +a`), and before any effectful launch verify that every key required by
the enabled providers/services is non-empty in the selected checkout's
`.venv/bin/python`. A missing file, source failure, whitespace-only value, or
missing required key aborts before effects. Offline and dry-run commands do
not require provider keys.

Presence is not proof of validity, quota, or network reachability. Never print
or persist credential values, and do not rely on an environment prepared by
another shell or process. Clear only inherited conflicting `PYTHONPATH` and
plugin/loss path overrides; retain explicitly reviewed workspace plugin
bindings. Use a fresh workspace for each new run identity (an explicitly
validated resume may use its existing workspace), external logs, and datasets
outside both repositories. Record exact checkout revisions and managed
process exit status.

## Repository identity and linked worktrees

A linked Git worktree may live outside the primary checkout, including under
`/tmp`. Its filesystem location does not determine repository ownership. Before
editing, committing, launching, or reporting task work, verify all four values:

```bash
git rev-parse --show-toplevel
git rev-parse --git-common-dir
git branch --show-current
git remote get-url origin
```

Task, experiment, campaign, deployment, and scientific-provenance changes must
resolve to this repository's common Git directory and remote. They must never be
added to the SIDERIUS framework checkout. A temporary-looking linked-worktree
path must be described as a linked worktree, not as an unowned temporary output.
Work is not durably part of `siderius-exp` until it is committed on an identified
branch and pushed to this repository's remote.

Raw data, generated workspaces, model artifacts, caches, and secrets are runtime
state rather than repository content. Their configured external paths may be
temporary or machine-persistent, but they must not be committed here.

## Active classification tasks

- `tasks/supernemo_signal_background/` owns event-level SuperNEMO
  signal/background classification with fixed 25-keV energy matching.
- `tasks/majorana_low_avse/` owns fixed-length Majorana Demonstrator waveform
  classification for `psd_label_low_avse`, also with fixed 25-keV energy
  matching. It uses the Zenodo partial release's official Train/Test boundary;
  unlabeled NPML files never enter supervised execution.

The corresponding `experiments/` launchers keep bounded qualification separate
from 20-iteration scientific campaigns. Literature ON and OFF runs must use
fresh workspaces and differ only in the declared literature switch.

## Running the live tests

The live suite includes checks that read framework scripts, so even collection
requires `SIDERIUS_CHECKOUT`. Point it at an explicit checkout of the pin (not
at this exp repository or an arbitrary latest framework revision), synchronize
that checkout's own environment, then run from this exp checkout:

```bash
uv sync --group dev --frozen
export SIDERIUS_CHECKOUT=/absolute/path/to/pinned/SIDERIUS
test "$(git -C "$SIDERIUS_CHECKOUT" rev-parse HEAD)" = "$(tr -d '\n' < SIDERIUS_REVISION)"
(cd "$SIDERIUS_CHECKOUT" && uv sync --group dev --frozen)
export MAJORANA_DATA_DIR=/absolute/path/to/verified/MAJORANA
env -u PYTHONPATH .venv/bin/python -m pytest
```

For the explicitly configured local pair, the bounded full-suite invocation is
below. These absolute paths describe this deployment only; other machines must
substitute their own verified checkout and dataset. Run from the exact exp
checkout after both frozen environment syncs above:

```bash
exp_test_basetemp=$(mktemp -d /tmp/siderius-exp-tests-XXXXXX)
env -u PYTHONPATH -u VIRTUAL_ENV \
  SIDERIUS_CHECKOUT=/home/yuema137/SIDERIUS \
  MAJORANA_DATA_DIR=/home/klz/Data/MAJORANA \
  CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  PYTHON_DOTENV_DISABLED=1 timeout --signal=TERM --kill-after=30s 600s \
  .venv/bin/python -m pytest -q --basetemp="$exp_test_basetemp"
```

Use a fresh external basetemp each time: pytest may clear it. Never use an
existing result directory or dataset root. This runs synthetic CPU lifecycle
witnesses and the read-only official-ID check, not an API-backed campaign.

Pytest collects `tests/` using importlib mode, so separate tasks can have
same-named test modules.
Pytest also adds this exp root to its import path for task plugins; it does not
add another framework checkout or set the runtime `PYTHONPATH` environment.
`provenance/legacy_siderius/` is an archive, not a second
executable test suite. Do not delete or rewrite archived evidence to fix live
collection. To inspect the selected tests without executing them, append
`--collect-only -q` to the command above.

The default suite includes a `real_data` check of the official MAJORANA release's
Train/Test event IDs (16 Train files and 6 Test files). It reads IDs, not waveform
training batches, and requires `MAJORANA_DATA_DIR`; missing or incomplete data
fails rather than silently choosing a developer's directory. Raw files remain
outside Git. For an explicitly partial, synthetic/code-only run use
`.venv/bin/python -m pytest -m 'not real_data'`; this does **not** establish the
real release's split integrity or a full-suite pass. The separate optional
legacy FCNet oracle checks report skips when their external reference checkout
is unavailable; retain those skip reasons in validation reports.

The framework checkout must be clean. The installed dependency alone does not
supply repository scripts. Comparison and Gold launch helpers validate the
selected checkout's HEAD, src layout, own `.venv`, and neutral-working-directory
import resolution before effectful work. An explicit `SIDERIUS_PYTHON` that
points elsewhere is a refusal; an ambient `VIRTUAL_ENV` is not a fallback.
See the
[Gold qualification command](campaigns/tidmad_gold/README.md) for its exact
checkout assertion and invocation. This setup does not authorize campaign runs.

## Migration status

The repository boundary is being established from the SIDERIUS `v0.1.4`
release and the unpublished `v0.1.5` Gold repair lineage. See the
[migration index](provenance/MIGRATION.md). The P0 03C1
[source manifest](provenance/legacy_siderius/p0_03c1/manifest.json) and
[archive guide](provenance/legacy_siderius/p0_03c1/README.md) preserve selected
framework history; those scripts, tests, reports, and configurations are not
live entrypoints or current experiment inputs.

The three additional literature pilot/full test sources are preserved in the
[P0 03C1c archive](provenance/legacy_siderius/p0_literature_pilots/README.md)
as fixed-corpus, non-live history. They are not collected by the live suite;
the fixed pilot originals were retired by infra #434.

The live TIDMAD anchor authority is
[`tasks/tidmad/runtime/anchor_map.py`](tasks/tidmad/runtime/anchor_map.py), and
the canonical ruler remains
[`tasks/tidmad/reference_data/segment_anchors.json`](tasks/tidmad/reference_data/segment_anchors.json).
Routine use has nothing to precompute. The module's `python -m` builder is
retained only for an explicitly reviewed reconstruction with caller-supplied
data and output paths. The #430 cleanup removed 44 duplicated originals plus
the root anchor from the framework; current launch readers now use the
relocated framework owners.
No campaign is authorized to launch merely because its files exist here.

The pinned framework (see `SIDERIUS_REVISION` for the exact revision)
exposes launch scripts under `scripts/launch/` and the workflow entry under
`src/workflows/`. Required generic Health defaults are packaged with the
installed framework. Consumers use
`execute_tools.health_checks.config.default_health_policy_path()` when they
need an explicit default-policy path; omitted overrides use the same default.
The former `configs/health/health_checks.yaml` path is removed, not a fallback.
An explicitly missing or invalid override is refused. Optional checkout policy
variants remain under `configs/health/`, and LLM configuration under `configs/llm/`;
task-owned Health declarations and thresholds remain in this repository.
This compatibility update changes no task declaration,
scientific treatment, metric, Health policy, budget, advice, or campaign
authorization. The historical C12 driver is preserved non-live in the
[03C2 archive](provenance/legacy_siderius/p0_03c2_c12/README.md) pending final
infra retirement.

## Declared Health roles and historical inputs

The pinned framework resolves scientific eligibility only from explicit
`gate_role` declarations. A missing role is UNKNOWN, not an empty required-gate
set; gate names, execution actions and historical config hashes cannot supply
it. Consumers use `resolve_scientific_gate_ids` (or the run/workspace resolver)
and must distinguish `None` from an explicitly empty set. The deprecated
`required_blocking_gate_ids` shim and historical SHA-role helpers are removed.

Older materializations containing `peek_file_indices: task_health_peek` or
another string are unsupported. For new work, declare the task-owned Health
inputs and use concrete `peek_file_indices` lists where required; every gate in
an effective roster must declare its role. Explicit no-Health composition and
explicitly disabled Health remain supported, distinct from missing declarations.

Health-enabled candidates with unknown roles cannot become scientific winners
or resumed incumbents. For Health-enabled candidates, resume also requires
independently valid evidence from the effective policy matching the recorded
hash: stored-valid verdicts and committed-best fields cannot replace a missing
or mismatched policy artifact.
Preserve old results and workspaces unchanged; this update provides no historical
migration and does not qualify a new campaign. Shared summary aggregation's
separate evidence limitation remains tracked in
[SIDERIUS #445](https://github.com/Galileo-Sandbox/SIDERIUS/issues/445).

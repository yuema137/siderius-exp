# SuperNEMO tutorial contract

## Owners and boundaries

This treatment initializes external editable projects and delegates to the native
fixed workflow. It preserves the existing scientific task, original event split,
CE/mean objective, energy-matched AUC and explicit no-Health declaration. It is
not a paper reproduction. The historical launcher/profiles and profiler remain
unchanged. `experiments/supernemo_signal_background/tutorial_demo/workflow.json`
owns the distinct no-Data-Analysis/no-literature/no-advice diagnostic treatment.

`settings.SuperNemoExperiment` validates absolute paths and supported settings.
All four scope fractions use the native CLI interval [0.01,1]. Both per-epoch
fractions remain 1. The default is three iterations, two rounds, one epoch,
0.01 for all scopes, 2/5-minute Trial/Formal training allowances and 10-GiB role
VRAM budgets. These are experiment settings, not framework defaults, total
spending limits or claims that every generated model fits.

## Raw data, prepared data and user project

`declared/source_files.json` is task-owned current source-file metadata. Its
names/sizes/MD5 values match Zenodo record 20698789; the old PROVENANCE table
remains dated acquisition evidence. No machine-specific paths are declarations.

`prepare.prepare` checks all official raw sizes and MD5s, creates a fresh external
prepared directory with four absolute symlinks and `.incomplete`, and invokes
the unchanged task `tools/profile_dataset.py` in a subprocess. It does not copy
or download raw data. The task profiler owns event grouping, process-salted
splitmix64 80/10/10 assignment, index arrays, counts and scientific checks.
The preparation helper implements none of that arithmetic.

Only after successful profiling and a stable raw binding check does preparation
write `preparation.json` and remove `.incomplete`. Existing destinations refuse
overwrite. Failures preserve incomplete evidence and require a new destination;
there is no silent retry or partial-index fallback.

The Pydantic receipt version `supernemo-preparation-v1` binds source manifest and
profiler SHA256, raw resolved targets/size/mtime/official MD5, all four index
SHA256s and the profiler report SHA256. Reuse compares scientific content IDs,
not Git HEAD: documentation commits do not require reindexing. A modified
profiler or source manifest does. Receipt verification is provenance checking,
not security certification against forged receipts or concurrent file mutation.

`verify_prepared` checks source identity, complete generated-file set, current raw
bindings and all index/report hashes. With `hashes=True`, it additionally reads
all raw bytes to verify official MD5. Preview and cache checks use the former;
launch and explicit `prepare --verify` use the latter. A copied task source
manifest must still match the repository-owned authority.

`project.create_project` copies task/notebook/workflow and Luna test routing into
a new external project, then writes saved JSON and shared-generated shell script.
No indexing, provider call or GPU work happens during initialization. The project,
prepared directory, original raw parents and both checkouts are separate; saved
output workspaces are also rejected inside raw parents behind the prepared links.
The source notebook may eventually hold a measured gallery; initialized copies
always clear code outputs and execution counts.

## Sample and execution semantics

The task trains on split 0 and evaluates during search on split 1. Split 2 is
reserved and not exposed by its training/evaluation loader. This tutorial adds no
final-test launcher or resplit interface. Fractions/seed change within-split
selection, not membership. Scope fraction, epoch fraction and exact energy-bin
class balancing remain ordered by the task implementation.

`data.scope_counts` calls the selected copied task using illustrative seed 42.
`data.show_event` plots one Train event's actual capped/padded tensor; it uses
already task-scaled coordinates, avoiding duplicate normalization constants.
Event identity is whole-event membership, while input geometry caps retained hits
at 224. The displayed filename/event ID is provenance, not a model feature.

`runner.build_command` maps saved knobs to native flags. The runner verifies
framework/package/planner identity, composition, preparation and required key
names; live mode additionally requires keys, GPU admission and raw MD5. It writes
a launch receipt and delegates to the native chain. Native checks are not weakened.

`demo.review` reloads saved JSON and verifies literal script bindings. Save-as
creates a fresh named JSON/script/workspace and preserves prior inputs. Notebook
Run All invokes that saved script only at its disclosed live cell; it never
constructs a provider or trains inside notebook code. The native preview is
skipped when the workspace already exists, allowing completed-cache verification.

Shared `saved_run` owns subprocess supervision, timeout/descendant cleanup,
completion receipt, nonzero refusal and unchanged-success reuse. SuperNEMO's
input digest binds saved JSON/script/routing/workflow, copied task files,
prepared receipt/index/report bytes, both checkout paths/HEADs and tracked diffs.
Raw full bytes, untracked source files, provider state and result bytes are not
included. Raw binding changes are checked separately before cache reuse. Do not
edit inputs during an active run; this is not forensic replay or atomic snapshotting.

`plot_results` needs only saved experiment/composition and native records, not raw
data, keys or a new launch. It requires explicit no-Health and the expected AUC
identity/direction. Shared progress rendering keeps failed scored Formal attempts
hollow and missing scores absent; no finite Formal observation means no chart.
CSV `validity=pass` means successful scored execution, never measured Health PASS.

## Validation and current qualification boundary

Focused tests cover source/index drift, incomplete preparation, immutable raw
sources, actual task-profiler grouping/splits on explicit synthetic fixtures,
actual native parser and normalization of default argv, invalid saved portions,
raw-parent isolation, saved variants, cache identity, missing credentials,
no-Health plotting and real notebook cells with live work disabled/cached.
Real CPU preparation uses official files and the unchanged profiler; real loader
counts and event visualization are separate from fixture results. Native dry-run
arguments must also pass the actual per-iteration parser, not just shell printing.

No current three-iteration API/GPU qualification has been completed for this new
treatment. A later authorized run and independently reviewed provenance are
required before publishing a measured score gallery or claiming live completion.

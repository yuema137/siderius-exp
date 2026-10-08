# Paper tutorial support contract

## Scope and owners

Project8 dual representation and LIGO use the [prepared-demo contract](prepared/implementation.md).
Its data preparation, explicit no-Health plotting policy and external experiment
schema are distinct from TESS/TIDMAD; shared script orchestration and environment
checks serve all four. The task-specific sections below describe TESS unless
marked otherwise; dated validation entries retain their original scope.

The TESS modules support the TESS NoPrior fixed workflow. TIDMAD has a separate
[one-band support contract](tidmad/implementation.md); its treatment and fraction
semantics must not be inferred from TESS. It reuses task
staging, composition, workflow rendering, information-treatment rendering,
provider-key derivation and framework pin verification. It does not modify
task science, the historical supervisor or infra runtime behavior.

`runner.TutorialExperiment` validates the external experiment JSON boundary. `build_command`
overrides iteration/epoch/time/VRAM settings on the existing rendered workflow,
then adds the production treatment. The CLI requires explicit external composition and routing files; internal
renderer defaults are not the public tutorial path. `TutorialReceipt` carries typed settings, argv and evidence
into execution. `inspect` resolves composition and validates routing without
provider requests.

Preview requires the clean source pair and exact exp virtualenv, but no GPU,
key or data. Launch checks key names only, validates staged curve keys and
finite data, hashes both archives, and uses the [shared GPU setup adapter](../shared/gpu-runtime.md)
through infra's own Python. Root execution, unavailable required GPU capabilities,
insufficient headroom, existing workspace and nested source/data/output paths
refuse before model calls. This is a trusted-user teaching tool, not a security
sandbox or private evaluator.

The command uses diagnostic result authority and explicit blocking Health.
No campaign wall deadline or money limit is promised. `os.execvpe` replaces
the wrapper with the native chain, preserving its signal and phase semantics.
The fresh sibling receipt uses exclusive creation so it cannot make the native
workspace nonempty. Retry means new workspace/name; there is no resume path.

`prepare_tess` downloads only the two committed source-manifest entries,
verifies content digests and calls the existing staging function. It requires
fresh external raw/data roots. Interrupted preparation may leave a partial
directory; no recursive cleanup is automatic. Hashes come from the pinned
Hugging Face LFS objects and are verified again locally. No test file is requested.

## Planner installation and identity

`tutorials.shared.llm_setup.write_test_llm_config` validates and exclusively
copies `tutorials/shared/openai_smoke_luna.json` into a fresh project. It does
not read scientific experiment routing. All eleven configured workflow routes
select OpenAI `gpt-6-luna`, reasoning `medium`; the planner explicitly selects
`native-timing-v1`. The same helper serves TESS, TIDMAD, Project8, LIGO and Pet.
The old paper-specific strategy-injection helper is removed. No historical
experiment configuration or existing external project is rewritten. Native
selection does not require installing the historical planner package.

The [shared contract](../shared/llm-profile.md) owns route coverage, retry limits,
validation scope and the distinction between workflow routing and an external
orchestrator's model.

All three `inspect` implementations call `verify_planner_setup` before native
execution. It parses the selected routing and resolves the public provider in
both interpreters, using the same sanitized child environment as launch.
`PlannerStrategyIdentity` equality includes provider content and infra assembly.
Absence, loading failure or disagreement refuses before an LLM client is created;
child stderr is suppressed in the repair message. Preview receipts carry the
resolved identity. Existing user configurations remain read-only; omitted
selectors use infra's declared installed-default contract, not an inferred
historical version. No provider installation happens during preview or launch.

## Notebook effects

Code cells are committed without execution outputs or counts. Markdown cells
embed explicitly labeled archived data/result images as notebook attachments;
these survive copying to an external project and require no runtime environment
to view. `examples/` owns the matching PNG/CSV/provenance files. They are actual
recorded runs, not evidence that the reader has executed their notebook. The
operator's
Run All onboarding route supersedes the earlier read-only default: it writes a
named external quick-demo JSON/script, reviews it, invokes that script with
`--launch`, and renders real progress records. RUN_QUICK_DEMO=False suppresses
execution. Re-running a completed unchanged demo reuses its result; edited
settings require a new name. Advanced example/split saves remain opt-in. Data
must be prepared and keys exported before Jupyter starts. No raw data download
occurs implicitly. The exact exp kernel owns notebook execution.

## Validation ownership

Focused regressions cover command flag collisions/lost NoPrior switches,
source/data/workspace overlap, GPU capacity mismatch, secret omission from
receipts, corrupt/wrong-population staged data, checksum substitution, and
notebook/runner schema drift. Do not add tests of Pydantic's own field defaults.
Execute the notebook offline with nbclient and the exact interpreter; syntax
and nbformat alone do not prove Run All. Download/staging and command preview
witnesses are distinct from a paid real-agent or GPU training qualification.


## Tutorial responsibility boundary

The notebook owns explanation, external configuration editing, saved-file
review, delegation to its saved script, and plotting. `quick_demo.run_demo`
executes that script, not native training or provider constructors. The script
owns parsing the saved experiment, task resolution, credential/data/GPU/source
checks, native argv construction and launch. This explicit Run All orchestration
route was requested after the original no-notebook-launch boundary. Manual
terminal execution remains available. Final-test selection is not automatic;
the notebook does not select a winner or consume the holdout to make a graph.

Credential status is derived from enabled routing and contains names/booleans
only. Preview warns but stays offline; launch rejects absent/whitespace values
before creating a receipt/workspace or making provider calls. A local secret
file is not read automatically. The user must export its values in the parent
terminal of Jupyter and separately in the launching terminal as needed.


## Observed RTX 5090 smoke run (2026-09-29)

The API-backed run `api_smoke_001` used exp commit `4762036`, infra pin
`349b6cd6d9766abbf3d87515b22e1005599a694b`, the shipped OpenAI `gpt-5.6-sol`
routing, external mode-600 credentials exported into the launch process,
1 iteration, 1 epoch ceiling, 2/5-minute Trial/Formal budgets and 8 GiB VRAM.
The native chain exited 0 after 6 minutes 33 seconds with 2 completed rounds
and 3 attempts. Its token ledger records 12 calls and 122,548 total tokens;
this is one observation, not a promised duration or cost.

Attempt 1 was `skipped_time_risk`: 2 training and 1 validation observations
could not establish runtime calibration. The planner's existing retry selected
full scopes and batch size 4; attempt 2 scored Trial R²
`-0.008499914365340144`, and attempt 3 scored Formal R²
`-0.06247370099701155`. Both scored records failed the observational prediction
dispersion check; their configured action was continue. The Formal authority
was diagnostic/non-authoritative. No runtime or Health policy was weakened.
This qualifies launch/API/training/inference/record handling, not scientific
performance or archived paper reproduction. H100 has no local real-run witness.

The subsequent responsibility refactor renames the input to
`TutorialExperiment` / `--experiment`, changes notebook editing/inspection and
documentation, and leaves native command construction unchanged. The final script's saved-file handoff was executed against a notebook-created
task copy and two-epoch experiment: its fingerprint changed and its epoch
flags matched the saved file. For the original settings, its rendered native
argv matched the smoke receipt (apart from the fresh workspace needed for
preview). The final notebook executed all 12 code cells with actual smoke
records, including observational Health failures. No second paid run occurred.


## User-owned project layout and initialization

`project.create_project` requires a new root disjoint from exp/infra (resolved
paths, including symlink aliases). It copies the whole TESS task, notebook,
LLM routing and inactive advice example, then writes absolute project bindings,
a typed experiment and an external shell script. No secrets, data download,
provider requests or source edits belong to initialization. Partial creation
on an I/O failure is retained for inspection; retries need a new destination.

The project root contains editable `tasks/`, `experiments/`, `llm/`, `advice/`,
`notebooks/`, `scripts/`, plus `data/` and `runs/`. `workspace` is a fresh single
run output under `runs/`, never the project root. Receipt is its sibling.
Generated plugins and calibration remain in that run. The CLI rejects input
experiment/composition/routing paths inside source; config paths cannot be
inside data or the run output. Absolute bindings must be updated if moved.
`write_launcher` quotes paths with shell-safe quoting, requires fresh output,
and binds the exact exp venv plus selected experiment. Notebook calls it only
when its explicit write exercise is enabled. Run shell arguments are limited
to the runner's own flags; the normal generated-script path takes `--launch`.

Advice is an inactive structured JSON example. `advice_file: None` rejects
activation in this NoPrior adapter. An advice-enabled treatment remains separate
work requiring explicit identity/digest/routing; do not imply support merely
because an example file exists. Data preparation/verification still owns the
released population on download. Launch verification now reads the selected
composition's full train/validation scopes, so a re-split task is checked
against its own membership. Arbitrary split edits still need qualification.

Source `.venv` installation is allowed environment setup; tracked source is
unchanged during tutorial use. Generated scripts use Python `-B`, child
processes disable bytecode writes, and Jupyter registration uses the external
project prefix. This is write-location discipline, not an OS security sandbox.


### External project validation (2026-09-29)

All 12 tutorial regressions pass, including quoted/space-containing project
paths, source-alias refusal, independent task-copy editing and script execution
from another cwd. A real external project was initialized with the pinned
infra checkout, its notebook executed all 12 code cells with staged data and
both editing exercises enabled, and its generated script was previewed from
`/tmp`. Preview selected the edited task fingerprint, project-local LLM routing,
two epochs and project-local run workspace. Missing-key launch refused with no
run output. Exp and infra git status remained clean after these operations.
This is offline handoff verification; no second paid smoke run is claimed.


## Parameter demos and selected-task split verification

`trial_train_fraction` maps to `--trial_portion`, `trial_val_fraction` to
`--eval_portion`. Non-null values enter the framework's experiment-fixed plan
lock; None omits the flag and delegates to the agent. Initialized projects set
both to 1.0. `formal_train_fraction` maps to `--formal_portion` and
`formal_val_fraction` to `--formal_eval_portion`, with operator-owned scope.
The lower-level `formal_train_portion` stays 1.0: the TESS training adapter uses
its selected scope each epoch. Per-round optional VRAM values override the
shared `vram_gib`; GPU admission checks the maximum effective requirement.
Time budgets remain training-attempt allowances, not a total API/wall cap.

`task_view.inspect_task` uses the pinned infra interpreter, run-local plugin
environment and composition resolver. It reads actual full train/val scopes
and seed-42 fraction examples from the TESS data path; it does not replicate
its sampling algorithm. Typed `TaskView` rejects duplicate curve identities
and cross-split star overlap. `inspect` uses these selected populations for
archive verification before launch, rather than always using the original
repository's manifest. Read-only counts are illustrations, not attempt-seed
or sample-identity promises.

`resplit.resplit_task` supports the standard TESS package layout. It validates
the selected composition against the source manifest and archives, pools ONLY
train+validation, permutes sorted Gaia IDs with the requested seed, and assigns
ceil(star_count * validation_fraction) stars to validation (clamped so both
splits remain nonempty). All curves of a star move together. It copies the
task, rewrites membership and matching raw-flux NPZ archives, updates population
metadata and a fingerprint-bearing split digest, and writes provenance. It
preserves flux arrays and target values and leaves original task/data unchanged.
Destination trees must be fresh and disjoint from source inputs and both repos.
Interrupted writes remain for inspection; choose fresh destinations to retry.
No provider call or training occurs. Test data is neither read nor moved.

The notebook explains four separate demos before the task/experiment reference.
`WRITE_DEMOS` saves named experiment/script pairs; `MAKE_NEW_SPLIT` creates the
new task/data pair and its experiment/script. Both default false. They perform
preparation only; terminal scripts own launch. Old validation statements above
refer to earlier notebook revisions (12 code cells); revalidate the current
11-cell notebook, including both default and opt-in paths, after edits.


### Four-demo validation (2026-09-29)

Historical pre-quick-demo notebook had 11 code cells. Its default Run All completed without creating
example configurations or split outputs. Opt-in Run All completed with both
switches enabled, producing baseline plus four experiment/script pairs and
new split task/data. Five independent external-script previews and native
`run_chain.sh --dry-run` calls passed from an unrelated cwd; no run directory
or launch receipt was created. Selected-data verification passed for each.
The actual pinned task loader materialized the new split's 3,075 training and
705 validation examples with input shape (1, 1024). The seed-42 25%/50% Trial
scope example returned 843/222 curves against 3,338/442 full populations.

The 14 tutorial regressions plus 34 existing TESS task/workflow tests passed.
Coverage includes distinct Trial/Formal flag mapping, whole-star independence,
unchanged parent manifest, preserved targets/flux and deterministic star
assignment. The initialized baseline now fixes Trial fractions at 1.0; the
older paid smoke run delegated them to the planner. No paid run of the new
fraction/split recipes is claimed; scientific performance remains unqualified.


## Saved-file launch review

`launch_review.launch_review` is a read-only notebook presentation helper. It
reloads the selected experiment through the task's schema, checks the shell
entrypoint's literal `EXPERIMENT`/`EXP_CHECKOUT` bindings and task-specific search
module, and renders saved/effective parameters, task/split/routing paths, required
input filenames, credential names and output destinations. Missing input files
or an existing output workspace suppress executable command blocks; mismatched
script bindings raise before any command is offered. No shell is executed.
It does not certify arbitrary shell code, data hashes, CUDA or source pins;
these remain the native preview/launch owner's checks. Kernel credential state
is not a claim about a separately launched terminal.

The TESS checklist follows all four save examples, including re-splitting.
TIDMAD section 6 serves the same role before section 8's final-test lifecycle.
Both default to one named saved demo and offer an explicit initial/demo mapping.
User-facing repository links and the locked framework dependency use the
operator's yuema137 release repositories at the unchanged framework revision;
Galileo-Sandbox remains the development/PR destination.


Launch-review validation (2026-09-29): 31 tutorial tests passed, including eight
new cases covering disk re-read, quoted external paths, missing data/used
workspace command suppression, mismatched script binding, and rejection of a
final-test launcher as a search launcher. Three framework-preflight tests also
passed after the dependency-origin update. Both notebooks executed against
existing external projects and rendered the exact selected search command;
TIDMAD's section-7 search review precedes section-8 seal/evaluate. Local README
links and empty committed notebook outputs were checked. Frozen installation
from yuema137/SIDERIUS succeeded at unchanged revision 349b6cd6d9766abbf3d87515b22e1005599a694b.
No new paid model search was needed for these presentation changes.


## Three-iteration Run All and progress plotting

`quick_demo.prepare_demo` validates settings through the selected task-specific
experiment schema, saves a uniquely named external JSON/script, and refuses a
same-name settings change. TIDMAD uses a separate copied file-holdout task.
`run_demo` delegates to the saved bash launcher after key/presence/binding review,
logs outside source, and records a versioned local-input identity with completion.
Only matching completed runs with an existing workspace are reused;
interrupted/existing unreceipted runs require inspection and a new name, not
automatic resume. Kernel interruption terminates its owned child
process group. Nonzero chain exits remain visible; plotted failure records do
not become successful scientific results.

### Completed-demo reuse identity

`result_identity.DemoCompletion` owns the `paper-demo-completion-v2` notebook
receipt boundary. The saved experiment is reloaded through its task-specific
schema before reuse. Its workspace must match `DemoFiles.workspace`; a receipt
must name that same existing directory. This is local cache reuse, not training
resume, scientific provenance or fresh source/GPU qualification.

`input_identity` hashes the saved experiment, shell script, selected LLM routing,
and every regular file in the selected task package (the directory above
`compositions/`), excluding `__pycache__` and `.pyc`. Prepared Project8/LIGO also
include their copied sibling `tasks/shared/` adapter files and the selected
`literature_config`. TIDMAD's literature YAML is already inside its task tree.
The task runner's `workflow_files` owner supplies the actual fixed workflow and
information-treatment paths to both command construction and hashing. Absolute
selected paths, resolved file targets and contents enter the digest; additions,
deletions and byte edits change it. This deliberately conservative package
identity may invalidate reuse after a task README edit too.

Both source checkout paths, Git HEAD revisions and tracked working-tree diffs
against HEAD are included. Even an unrelated tracked source edit or a new
source commit requires a fresh demo name rather than relabeling an old run.
Untracked checkout files, installed dependencies, environment variables,
provider/account state, external raw data and result contents are not hashed.
Data identity declarations inside the task are included; rehashing dataset bytes
remains launch preflight's responsibility. This helper covers the standard
initialized package layout, not arbitrary external imports, directory symlink
closures or a forensic replay of all runtime dependencies. Its Git/file reads do
not execute task plugins, import the selected framework checkout, contact a
provider, require credentials, or perform native composition/GPU preflight.

New runs capture the identity before launch checks, verify it again immediately
before spawning the saved script, and compare after child exit. An observed
mid-run change or unreadable input writes `inputs_unchanged=false` beside the
real exit code and elapsed time. That receipt never permits automatic reuse,
even if the old bytes are later restored. These snapshots do not lock mutable
files or detect a change restored entirely between snapshots. Concurrent editing
of launch inputs is unsupported; a changed run remains evidence for inspection,
not a newly qualified experiment.

Old experiment-only receipts and malformed receipts refuse reuse with explicit
read-only plotting and new-name guidance. They are never upgraded, overwritten,
or treated as authorization to run again. Missing input files or result workspace
also refuse without invoking launch checks or the script. All original records
remain available: select `PLOT_WORKSPACE` in TESS/TIDMAD or `PLOT_EXPERIMENT` in
Project8/LIGO and execute only the plotting cell. A valid unchanged v2 receipt
with a nonzero script exit remains reusable for inspecting recorded scores; its
exit code is printed and preserved, never converted into a successful search.

Focused regressions drive actual `run_demo` decisions using initialized external
projects and a fake saved-script process. They cover all four task routes, linked
input changes, bytecode exclusion, missing/mismatched workspace, legacy/malformed
receipts, unchanged no-preflight reuse, nonzero outcomes, and preflight/mid-run
edits. These deterministic witnesses do not qualify paid or GPU execution.

`progress.read_progress` validates native HyperparamTuningOutput, uses outer
chain `iter_NNN` as x, keeps Formal records only, and reads `metric_result.scalar`
even when accepted denoising_score has been nullified for invalidity. It never
substitutes Trial, invents zero for missing/nonfinite values, mixes metrics or
merges duplicate iteration/attempt identities. Filled/hollow markers record
Health PASS/FAIL or failed attempt status; unknown Health remains in the CSV without a verdict marker.
This follows the paper cross-task figure's Health fill convention but is not
retrospective behavioral certification. The running-best raw-score line includes
invalid observations, respecting metric direction. Figure 4 styling uses serif typography, inward ticks, no grid, dashed Formal
results, a solid current-best line and stars for new bests with Health PASS
(invalid improvements retain their hollow marker). The R² axis is 0–1;
out-of-range R² scores use boundary triangles and exact CSV values. TIDMAD’s
custom denoising score uses its actual range instead of the R² bounds. Missing
values/no Formal records remain in the CSV, without an extra diagnostic panel. PNG/SVG/CSV outputs live externally;
the CSV retains source-record paths. A user can replot another workspace without
executing any search.


Operator sizing adjustment before TIDMAD Run All qualification: its quick demo
uses Trial train/eval .01/.01 and Formal .02/.02, with 2/5-minute training
allowances and five-epoch ceilings. The existing workflow's separate
training_validation_portion=.1 is unchanged and explicitly explained: it
materializes 20 validation-file segments even when scoring uses 2/4. The TESS
quick demo retains full data and 1/2-minute allowances. Source-level policies
and Health/runtime checks are unchanged.


## User-environment diagnostics

`preflight.require_ready` aggregates missing interpreter paths, task/LLM files,
required exported key names, data files and NVIDIA utility availability, with
repair instructions. It runs in both runner CLIs before launch and in
`quick_demo.run_demo` before opening a log. The notebook additionally calls the
selected native `inspect(launch=True)` so source/hash/CUDA failures appear in the
cell before API work rather than only in a child log. The saved script repeats
validation independently. This adds read-only preflight cost, not provider calls.
Generated scripts contain dependency-independent shell guards for absent checkout,
Python, experiment JSON and failed dependency imports. Notebook bootstrap checks
TUTORIAL_HOME/project.json, the selected kernel and required Python modules before
importing tutorial tools. CUDA/VRAM/device errors include configuration repair
steps. Provider key presence is not authentication; no network key probe is made.
Completed cached runs continue to bypass launch preflight and use no credentials.

Operator acceptance clarification: this is a workflow demonstration, not a
Health-PASS search objective. Qualify configuration → script → real attempts →
recorded scores/validity → plot. Keep the three-iteration limit regardless of
Health outcomes; distinguish model rejection from setup/runtime failure, and do
not extend runs or relax checks to obtain valid points.

## Archived visual examples and live data previews

`examples/README.md` indexes the four recorded runs and their limits. Each
`*-example.json` allowlists run metadata and numerical settings, records exact
exp/infra revisions and original receipt/record hashes, and hashes the exported
assets. CSVs preserve every record classified as non-Trial by the native schema,
including absent metrics, with workspace-relative source paths. Do not publish entire receipts or execution
logs: they contain operator-local bindings. Raw data and checkpoints stay external.

The two image attachments in each notebook match its checked-in data/progress
PNGs byte-for-byte. Markdown labels distinguish permanent archived examples
from Quick C's live results. Never replace invalid or negative scores for
presentation. The existing progress renderer owns the paper-style plot.

`data_preview.plot_training_example(experiment, task=..., row=0)` validates the
saved experiment with its existing task-specific schema and reads training data
only. TESS selects a manifest identity and reuses the task normalization function;
TIDMAD requires the Quick A file-holdout experiment, validates its split and
topology, then reads one 40,000-sample window
from the first assigned training file and displays a contiguous 600-sample prefix;
Project8/LIGO memory-map one already prepared event. It returns a figure and
description, writes nothing, and never accesses evaluation/final-test data.
The notebook calls it after Quick A saves the effective experiment. Runtime
execution remains owned by the existing saved launcher.

Missing data/fields produce setup and saved-config repair guidance. Out-of-range
rows report the valid PREVIEW_ROW interval. These local-only checks do not
require provider credentials or a GPU and do not replace launch preflight.

## Saved quick-demo modification lesson

`tutorials.paper.saved_demo` serves only the TESS/TIDMAD lesson after Quick C.
`load_demo` reads the selected named JSON through `read_settings`, checks run
identity and the existing literal launcher contract, and creates no files.
`save_variant` revalidates the selected pair, merges explicit changes through
the existing experiment model and derives a fresh run name/workspace. It checks
JSON, script, workspace and sibling receipts/logs for collisions before writing
a new JSON and calling the existing task launcher writer. Existing files are
never overwritten; task trees are not copied or regenerated. Scientific/data
validation and launch/reuse semantics remain with their existing owners.

The opt-in notebook lesson preserves unedited saved fields, including TIDMAD's
file-holdout composition/protocol and all fractions. Task/routing/data bindings
remain shared references. SAVE_CHANGED_DEMO defaults to false. Saving selects
the new pair for review and result-path display but never calls run_demo. Later
sessions explicitly select SELECTED_DEMO_NAME with quick execution and saving
disabled. Advanced paper-pool/split/final-test lessons retain their separate
initializer baseline. No initial-creator, cache identity, archived result or
paper scientific contract changes.

Focused tests use different initializer and saved settings, execute the actual
notebook selection/save/review cells, inspect rendered native commands and test
read-only reopening plus existing-destination and invalid-change refusal. The
lesson needs no additional live API/GPU run: execution is still the existing
saved script, and the changed behavior is validated file selection/persistence.

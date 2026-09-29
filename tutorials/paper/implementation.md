# TESS tutorial support contract

## Scope and owners

This first tutorial supports TESS NoPrior fixed workflow only. It reuses task
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
finite data, hashes both archives, probes the physical NVIDIA GPU and executes
a CUDA allocation through infra's own Python. Root execution, unknown GPU,
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

## Notebook effects

The notebook is committed without outputs or execution counts. Default Run All
only reads source and optional staged data. It does not download, write config,
call providers or train. Two named opt-in booleans control external config
writing and task-copy creation. Tensor normalization uses the task authority.
Long execution is shown as a terminal command. The kernel must use the exact
exp virtualenv; editable notebooks and configs belong outside source.

## Validation ownership

Focused regressions cover command flag collisions/lost NoPrior switches,
source/data/workspace overlap, GPU capacity mismatch, secret omission from
receipts, corrupt/wrong-population staged data, checksum substitution, and
notebook/runner schema drift. Do not add tests of Pydantic's own field defaults.
Execute the notebook offline with nbclient and the exact interpreter; syntax
and nbformat alone do not prove Run All. Download/staging and command preview
witnesses are distinct from a paid real-agent or GPU training qualification.


## Tutorial responsibility boundary

The notebook owns explanation, opt-in external task-copy/experiment editing,
and read-only inspection. It must not execute `run.sh`, native framework launch,
or provider calls. The script owns parsing the saved experiment, resolving its
selected task, credential/data/GPU/source checks, argv construction and launch.
The notebook imports the experiment schema and read-only credential checker;
it does not construct native framework argv. `--experiment` is the only input
configuration flag. The workflow and information treatment remain fixed by this
TESS entrypoint; composition/routing and budget changes are explicit fields.

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

Current notebook has 11 code cells. Default Run All completed without creating
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

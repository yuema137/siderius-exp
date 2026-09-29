# TESS tutorial support contract

## Scope and owners

This first tutorial supports TESS NoPrior fixed workflow only. It reuses task
staging, composition, workflow rendering, information-treatment rendering,
provider-key derivation and framework pin verification. It does not modify
task science, the historical supervisor or infra runtime behavior.

`runner.TutorialExperiment` validates the external experiment JSON boundary. `build_command`
overrides iteration/epoch/time/VRAM settings on the existing rendered workflow,
then adds the production treatment. External composition and routing files are
explicit opt-ins. `TutorialReceipt` carries typed settings, argv and evidence
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

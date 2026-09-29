# TESS tutorial support contract

## Scope and owners

This first tutorial supports TESS NoPrior fixed workflow only. It reuses task
staging, composition, workflow rendering, information-treatment rendering,
provider-key derivation and framework pin verification. It does not modify
task science, the historical supervisor or infra runtime behavior.

`runner.DemoSettings` validates the external JSON boundary. `build_command`
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

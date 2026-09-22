# Add the orchestrator documentation to a common task package

Status: documentation assembly qualified locally; scientific execution is not
qualified by this document. This adds no launcher, executor, runtime feature or
information-treatment declaration.

## Authorities and layout

Build the common package with the existing
[baseline builder](../../../deployments/tidmad_coding_agent_baseline/README.md#before-renting-gpus)
from this checkout and its exact `SIDERIUS_REVISION`. Select one of `0-3`, `4-9`,
`10-14`, `15-19`; each unit covers all files in its band. Preserve the generated
public `input/` directory, including its task, treatment, provenance and checksum
files. Keep evaluator material private.

Add the generic infra documentation to the actual coding-agent workspace:

```text
work/
  input/                         unchanged common public package
  agent/                         coding-agent cwd
    AGENTS.md                    infra payload
    SIDERIUS-RUN.md               concrete operator run declaration
    .agents/skills/siderius-toolkit/
      SKILL.md
      references/...
```

The generic package is `docs/agent-reference/orchestrator-toolkit/payload` in
SIDERIUS. Its sibling `ASSEMBLY.md` owns generic copying, collision and discovery
rules. Record the exact documentation commit separately from the installed
runtime commit; a Markdown-only overlay does not justify changing the runtime
pin. Reject existing destination paths rather than overwriting instructions.
Do not copy this operator document or the private evaluator into the agent input.

Inventory every public input path, byte size and SHA256 before assembly, then
verify all original entries and separately inventory the additions. Reject
symlinks unless the deployment explicitly defines their visibility. A task-only
checksum cannot prove full-package parity.

## Additive run declaration

Fill `SIDERIUS-RUN.md` with concrete deployed paths and decisions:

- Common task path `/work/input/task.md`, package identity, band and run ID.
- Explicit typed data scope matching the declared band. For band `0-3`, requests
  carrying `DataScope` must use `file_indices=[0, 1, 2, 3]`; `null` means the
  complete dataset. Verify persisted requests and downstream handoffs against
  this scope. A band constraint in prompt text alone does not set it.
- Exact installed framework revision and its own Python environment.
- Existing authorized execution route for each enabled native agent, including
  task composition, physical data root and writable storage/generated-library
  paths. An importable interface alone is not an execution route.
- Per-role provider/model/effort and which choices remain open.
- A link to the unchanged run clock/resource/deadline authority. Every native
  call, controller action, retry and failure spends that same allocation.
- Separately declared orchestrator information treatment and permitted sources.
  The unchanged CLI treatment receipt describes the common baseline package;
  do not silently interpret its `not_applicable` states as an orchestrator
  declaration. Preserve it and record the added treatment's identity separately.
- Common evaluator/submission interface and required retained artifacts.

For the frozen band `0-3` public package, the additional run declaration must
state the existing native scope explicitly, for example:

```text
Scope source: input/provenance.json band, consistent with input/task.md.
Band-to-file mapping: input/tasks/tidmad/reference_data/official_paper_result/README.md.
Dataset profile: input/tasks/tidmad/resolved/dataset_profile.json (20 files total).
Authorized DataScope: {"file_indices": [0, 1, 2, 3]}.
```

Resolve the corresponding values for the selected existing frozen package;
do not copy this band's values into another run. This restates an existing run
restriction in native terms and changes no input file. The global 20-file profile
and 20-segment-per-file training pool are different declarations; neither means
that all 20 files belong to this band. The earlier diagnostic declaration omitted
this resolved scope, despite the assembly rule above; retain that preparation
failure in its report rather than treating it as a qualified assembly.

Use the existing agents for supported work. Caller code may construct typed
requests, transfer artifacts and format results. Native implementation artifacts
still need to satisfy the common candidate submission contract; an
`ImplementorOutput` or tuner success is not itself an evaluator submission.

Do not prescribe serial order, number of proposers/implementers, branching or
parallelism. Shared paths still need an actual collision-free ownership plan.
The generic toolkit documents those effects without selecting a strategy.

An experiment treatment may separately provide controller strategy advice. For
O-StrategyOnly, follow [the V3 deployment contract](../main_orchestrator/STRATEGY_ONLY.md):
retain NoPrior's disabled DA and absent model advice, and bind the protected
prompt supplement at every new outer invocation. For historical
O-Full, copy the prepared `controller-work-strategy.md` into `run/`, verify the
digest recorded in `deployment.json`, and link it from `SIDERIUS-RUN.md` for the
outer controller only. Keep it separate from `run/advice.json`, which serves the
model research roles. O-NoPrior and fixed workflows must not receive the
controller strategy artifact. This treatment-specific layer does not change the
generic wrapper guidance above.

For O-Full, put both advice paths and their verified SHA-256 values directly in
`SIDERIUS-RUN.md`, with an instruction to open both at startup and after context
recovery. Keep those paths in the agent's continuation summary. At every new
baseline-harness invocation, the same immutable run declaration and files must
still be present and rechecked before the agent starts work. The generic
toolkit's `AGENTS.md` already requires reopening the run declaration on context
recovery. File presence, checksums, startup links and invocation checks can be
enforced by deployment; whether a model acts on advice during an uninterrupted
long invocation remains observable behavior, not a guarantee.

## Approved TIDMAD advice-scope declaration

For O-Full/O-NoPrior, also copy
[`TREATMENT_SCOPE.md`](../main_orchestrator/TREATMENT_SCOPE.md) into `agent/`
and require reading it via an explicit link in `SIDERIUS-RUN.md`. The operator
approved this experiment-level interpretation on 2026-09-18: the common
package's no-advice restrictions describe CLI; the added orchestrator treatment
authorizes O-Full advice outside `input/`. Preserve all original input bytes.
Declare the exact on/off state and advice identity; the scope document is not
itself a treatment selector or a general task-override rule. It belongs to the
TIDMAD experiment, never the generic toolbox payload. Runtime readiness remains
a separate requirement.

## Scientific and execution boundaries

The current common main package declares the frozen training pool in
`continuous_regression_frozen_pool.yaml`: all fitting is confined to the
content-pinned 20-of-200 parent per training file, with full validation-band
scoring. The current fixed workflow uses that same parent. This document changes
neither declaration. Consult the generated task and
[fixed-workflow configuration](../main_fixed_workflow/README.md) for their own
parameters; do not copy fixed-workflow scheduling into the free orchestrator.

The public task view deliberately omits private evaluator implementation files.
Some composed native operations require those bindings. Do not grant the coding
agent evaluator-tree access to make an import succeed. Before scientific use,
qualify an already-authorized execution environment exposing the needed existing
operations while preserving the common access boundary. No such environment is
created by this documentation.

Human advice, dedicated Data Analysis and literature retrieval require their
own explicit treatment and usable bindings. In particular, the fixed Full arm
is not a ready-made orchestrator declaration. Do not silently inherit it or
bundle advice into generic interface documentation.

## Local assembly evidence — 2026-09-18

At exp `7f72196226c73b70da1ded32c467126916068f8f`, infra runtime
`1c68bc81d7e44bbdc6e03a445a8422c3f77f45ff`, the existing builder produced a
band `0-3` common archive with SHA256
`3d392e9f1b99015cf07c2bd2d550f3727847cc83d3243e2bfea8ba9c364367f9`.
A local public-only assembly preserved all **96 original files** byte for byte
and added **28 Markdown files** under `agent/` (27 payload files and one
inspection-only run declaration). No evaluator files were exposed.

The builder correctly rejected the documentation worktree while it had tracked
changes; the successful build used a separate clean checkout of the exact pin.
No guard was relaxed. Raw inventory and build receipts are retained in the local
orchestrator work plan; they are not agent instructions or scientific results.
This is one band's assembly witness, not a claim of four deployed units or an
end-to-end training/submission qualification.

## Real task-package rehearsal — 2026-09-18

[The actual task-package rehearsal](REHEARSAL.md) uses current exp main
`e1f2218` and its infra pin `7add8006`, with generic documentation `19528597`.
Discovery and native invocation were observed, but integration is not qualified:
proposal paths failed, structured band scope was omitted, and the diagnostic
ended without final readiness artifacts. This is separate from the earlier
assembly-only witness above. The added scope guidance has not yet been tested
in another actor session.


## Protected inputs and qualified runtime

The orchestrator overlay protects the installed infra and entire frozen common
input tree. It adds no blanket restriction requiring all scratch/cache writes to
one directory; the common task's own write/deliverable rules remain unchanged.
Use process/container read-only mounts for protected roots and the linked infra
Git metadata, with generated artifacts outside them. Do not change shared host
checkout permissions. Check the mount behavior inside the launched environment
and retain input/infra inventories.

The successful preparation witnesses used isolated runtime repair `49330e46`,
while this frozen common package records dependency `7add8006`. Keep both facts
visible. Before formal use, select an integrated infra revision containing the
repair, record the wrapper revision separately, and verify that deployed pair.
These docs do not update `SIDERIUS_REVISION`, rewrite frozen provenance, merge
the repair or authorize production execution.

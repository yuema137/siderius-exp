# Tutorial hardware setup boundary

`hardware.HardwareSettings` owns a resource-only projection of saved experiment
JSON. `runtime.gpu_report` transports the typed request and response;
`runtime.verify_gpu` retains the saved launch adapters' existing string receipt.
`gpu_check.check_gpu` consumes the selected framework's hardware, accounting and
aggregate-admission owners. It does not implement model admission or monitoring.

## Independent hardware command

From the exp checkout, run:

```bash
.venv/bin/python -m tutorials.shared.hardware --experiment /absolute/project/experiments/example.json
```

The projection requires explicit absolute `infra_checkout`, absolute `workspace`
and positive finite, non-Boolean `vram_gib`. Optional `gpu` is a stripped,
nonempty, case-sensitive substring of the detected device name; null means no
name constraint. Optional `trial_vram_gib` and `formal_vram_gib` override the
shared budget. There is no
GPU-model whitelist, guessed budget or fixed upper budget.

The projection intentionally ignores other fields. Passing validates hardware
resource settings only, not the complete experiment schema, task composition,
data integrity, planner identity, provider credentials or provider access. The
saved tutorial runner remains responsible for those contracts. The eight saved
experiment classes expose these common fields across nine tutorial tasks;
Project8 and LIGO share `PreparedExperiment`.

The command checks the clean exact source/dependency pair with
`verify_framework_pin` and the exp installation with `verify_installed_framework`.
The selected infra child also requires its own `.venv` and source installation.
It needs no API key, imports no task, downloads no data, trains no model, and
creates no run workspace, receipt or completion marker. It does perform the
explicit GPU queries and tiny kernel described below. Ordinary tutorial preview
and supplementary `--dry-run` remain GPU-free.

## GPU transport and ordering

The request travels as JSON on stdin to
`<infra_checkout>/.venv/bin/python <exp_checkout>/tutorials/shared/gpu_check.py`.
The child's working directory is infra. `child_environment` removes inherited
source/plugin overlays; no `PYTHONPATH` or borrowed environment is used. Existing
launch paths invoke this same check before native chain/provider execution.

The child requires these facts in order:

1. `core.hardware_context.inspect_gpu_runtime` reports an available GPU backend
   and exactly one visible logical GPU. Physical numbering may map to logical
   zero; select visibility before running the command.
2. The optional name expectation matches, and both effective stage budgets are
   strictly below physical capacity, preserving the existing tutorial contract.
3. An implemented accounting adapter and real stable device identity exist.
4. `gpu_accounting.sample(os.getpid(), identity)` queries current device/process
   usage. The PID is the existing check process, not a fabricated model candidate.
   Missing telemetry or a wrong device refuses. Native `OccupancyBound` validates
   complete coherent accounting quantities; unknowns never become zeros.
5. `pair_admission.resolve_gpu_ceiling` resolves environment operator ceiling,
   declared host quota and measured capacity. The conservative measured capacity
   is the smaller of discovery capacity and driver total. Native
   `evaluate_resolved_pair_admission` compares **all device-level occupied usage
   plus max(Trial cap, Formal cap)** against that resolved ceiling. Stages execute
   sequentially, so their caps are not summed. Existing occupied usage includes
   the check process, other programs and unattributed/context bytes; visible
   process sums are never substituted for device occupancy. Zero occupancy adds
   no member to the positive-only native member type. Equality is admitted by the
   native aggregate rule.
6. Only after these checks: allocate one zero tensor on `cuda:0`, add one, then
   synchronize. This namespace is also PyTorch's ROCm namespace; no vendor policy
   is reimplemented in the adapter.

`SIDERIUS_PAIR_VRAM_CEILING_GIB` uses GiB;
`SIDERIUS_GPU_VRAM_QUOTA_MIB` uses MiB. Native resolution remains authoritative;
malformed values refuse. An undeclared quota is unknown, not unlimited. The
configured-cap member is labeled as an allowance, never measured model demand.
A conservative refusal may exclude a model that would use less than the cap.
Users may wait, select another GPU, or deliberately reduce their saved allowance
and choose a smaller model; the check never silently changes either budget.

## Report and limitations

The discriminated extra-forbid report includes backend/runtime, name/logical
index/UUID, physical capacity, occupied GiB, largest configured phase cap,
effective ceiling, remaining room after that cap, declared host/operator limits,
and successful query/kernel witnesses. Failures are actionable. Child exceptions,
raw stdout/stderr and environment values are not dumped into diagnostics. The
transport refuses invalid JSON, missing interpreter or a 60-second timeout. That
timeout is not an experiment wall-clock or spending cap.

Passing is a point-in-time configured-cap check. It reserves no memory and proves
neither generated-model fit nor future headroom. Native measured model admission,
resource monitoring and failure handling still apply. A tiny kernel is not a
training qualification. Changes to availability after the observation may still
cause a correct later refusal.

`hardware.host_observations` reports host RAM total/available bytes using psutil
when available, explicitly **not** a container/job RAM allowance. That allowance
remains unknown. It reports free disk on the nearest existing workspace ancestor
and checks directory write/search access without creating it. Generated output
size and required RAM remain unknown. These observations are not RAM/disk
admission; data-specific storage and measured preparation footprints belong in
the owning tutorial. Existing raw data is not counted as another download.

## Backend and compatibility boundary

CPU and Intel GPU training are unsupported in these tutorials. The current locks
select CUDA. ROCm discovery carries experimental/untested limitations; its
required driver/process accounting adapter is absent at the selected revision,
so protected tutorial execution refuses without disabling protection. This is
not a promise that every NVIDIA model, dataset or generated architecture fits.

The current qualified root pin is recorded by `SIDERIUS_REVISION`,
`pyproject.toml` and `uv.lock`; it includes `inspect_gpu_runtime`. No source pin or
lock change is part of this adapter change. The earlier pending-API narrative no
longer describes the current installation.

The new early occupancy/quota refusal intentionally improves current tutorial
setup behavior. Task science, native training arithmetic, historical paper
plugins/configuration, prompt fixtures and archived results are untouched.
Focused tests use synthetic hardware with the actual native coherence/aggregate
owners. The [saved-resource projection test](../../tests/tutorials/test_hardware_command.py)
currently covers seven task cases across six experiment classes (TESS, TIDMAD,
Project8/LIGO, Pet, MJD and SuperNEMO); DAVIS and Cancer are not included in that
parameterization. These tests are not real GPU or training qualification.

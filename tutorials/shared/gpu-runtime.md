# Tutorial GPU setup boundary

Owners: `runtime.verify_gpu` transports a validated request; `gpu_check.check_gpu`
checks tutorial launch requirements in the selected framework interpreter.
`core.hardware_context.inspect_gpu_runtime` remains the sole device/backend
discovery authority. This adapter is not a GPU sampler, admission resolver or
resource monitor.

## Interface and order

Paper and Pet settings use an optional stripped, nonempty `gpu` string as a name
expectation. Null/omitted means no name expectation. Positive finite, non-Boolean
VRAM budgets have no device-model-specific or fixed 80 GiB maximum. Explicit
Trial/Formal overrides take precedence over the shared budget.

`verify_gpu` sends `GpuCheckRequest` as JSON on stdin to
`<infra_checkout>/.venv/bin/python <exp_checkout>/tutorials/shared/gpu_check.py`.
It sets the child working directory to infra and uses the existing environment
owner to remove inherited source/plugin overlays. It never sets `PYTHONPATH` or
loads source from another checkout. The existing launch owners still verify the
single exact framework pin, installed package binding and clean source pair.

The child obtains fresh typed framework facts, then requires:

1. A GPU backend and an available device, with exactly one visible logical GPU.
   A host may have several physical GPUs; visibility can remap any selected one
   to logical zero. This is a single-device tutorial, not distributed execution.
2. A matching explicit name expectation when supplied.
3. Effective Trial/Formal budgets strictly below the selected physical capacity.
4. An implemented required accounting adapter and the framework's actual stable
   device identity. No index/name-based or synthetic UUID fallback is allowed.
5. One zero-initialized tensor, one addition and synchronization on `cuda:0`.
   PyTorch uses this namespace on both CUDA and ROCm; no vendor check is copied
   into the adapter. Missing capabilities refuse before this kernel witness.

Accounting implementation and identity do not prove live samples are available,
coherent or sufficient. Actual framework measurement/admission/protection must
still validate those facts. A tiny kernel cannot prove model fit or peak safety.

## Outputs, failures and effects

The child returns one discriminated, extra-forbid JSON response: `GpuCheckReport`
contains backend/runtime, name, logical index, capacity, real UUID, limitations
and successful kernel witness; `GpuCheckFailure` contains an actionable message.
The parent validates this response and preserves the existing string receipt
interface. Child failure, malformed JSON, missing interpreter or a 60-second
setup timeout refuses launch. This timeout bounds this check only, not the
campaign or provider spend. Raw child stdout/stderr and exception payloads are
not included in failure messages.

Importing the adapter defines schemas only. Preview never calls `verify_gpu`.
Cheap setup checks validate files/environments/key names without requiring an
NVIDIA binary; hardware capability and kernel checks occur only during launch,
before any provider or model execution. No environment or key values are logged.

ROCm facts carry experimental/untested limitations. Its driver/process accounting
adapter is currently absent, so the protected tutorial route refuses without
disabling resource protection. This is not a blanket restriction on other
framework consumers using ROCm tensor operations. Intel GPU and CPU training are
not supported by these tutorials. Current locks select CUDA; no ROCm install
command, wheel replacement or dependency-profile change is introduced here.

## Qualification and history

This change deliberately does not promote `SIDERIUS_REVISION`, `pyproject.toml`
or `uv.lock`. The current root pin predates `inspect_gpu_runtime`; launch refuses
its missing API until final paired qualification. No older discovery fallback is
allowed. CPU tests mock the reviewed API while executing the actual adapter,
transport and settings boundaries.

The reviewed framework interface at `38f6131dd8043b7932cb1afbfb604c4cf2215b0b`
has `hardware_context.py` SHA256
`ac33fd4d6a4cb79b6ffc242cdcd7bd60c22c7b87ac34366bdf24183e44f85234`.
Future paired qualification must record the actual selected owner hash and
framework commit. Existing renderer/estimator assembly digests do not include
this discovery owner and cannot attest its behavior.

Historical task/scientific configurations, prompt fixtures, notebooks and saved
outputs remain unchanged. Only current tutorial builders and the current TESS
example input select automatic GPU naming. An old explicit name remains a
constraint; an old runtime result does not qualify a new backend or device.

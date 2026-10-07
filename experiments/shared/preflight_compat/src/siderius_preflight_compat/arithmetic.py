"""Frozen completed-estimate arithmetic from infra 078b23ca7d88.

This explicitly selected experiment policy retains leaf-call parameter sums
and the old optimizer lookup. It does not claim these are corrected physical
allocations. Admission, candidate order and failure attribution remain infra
responsibilities. Reference source hashes are retained in provenance.json.
"""

from core.preflight_observations import PhaseEstimate, PhaseObservations

CUDA_CONTEXT_BYTES = 185 * 1024**2
CUDNN_BACKWARD_BYTES = 50 * 1024**2
OPTIMIZER_STATE_MULTIPLIER = {"adam": 2, "adamw": 2, "sgd": 0}


def estimate_historical_phase(observations: PhaseObservations) -> PhaseEstimate:
    params = observations.leaf_parameter_bytes
    if observations.phase == "training":
        optimizer = str(observations.training_config.get("optimizer") or "adam").lower()
        if optimizer not in OPTIMIZER_STATE_MULTIPLIER:
            raise ValueError(
                f"Unknown optimizer: {optimizer!r}. Known optimizers: "
                f"{sorted(OPTIMIZER_STATE_MULTIPLIER)}. Add an explicit entry "
                "to _OPTIMIZER_STATE_MULTIPLIER rather than guessing."
            )
        assert observations.saved_tensor_bytes is not None
        overhead = params + OPTIMIZER_STATE_MULTIPLIER[optimizer] * params
        breakdown = {
            "autograd_tape_bytes": observations.saved_tensor_bytes,
            "input_bytes": observations.input_bytes,
            "output_bytes": observations.output_bytes,
            "param_bytes": params,
            "training_overhead_bytes": overhead,
            "cuda_context_bytes": CUDA_CONTEXT_BYTES,
            "cudnn_backward_bytes": CUDNN_BACKWARD_BYTES,
        }
        diagnostic = sum(breakdown.values())
        admission = diagnostic
        estimator = "training_saved_tensors_v1"
    else:
        breakdown = {
            "input_bytes": observations.input_bytes,
            "max_output_bytes": max(
                observations.output_bytes, observations.leaf_output_bytes_max
            ),
            "param_bytes": params,
            "cuda_context_bytes": CUDA_CONTEXT_BYTES,
        }
        diagnostic = sum(breakdown.values())
        admission = params + observations.leaf_output_bytes_sum + CUDA_CONTEXT_BYTES
        estimator = "inference_leaf_sum_v1"
    return PhaseEstimate(
        phase=observations.phase,
        admission_bytes=admission,
        diagnostic_bytes=diagnostic,
        estimator=estimator,
        breakdown=breakdown,
    )

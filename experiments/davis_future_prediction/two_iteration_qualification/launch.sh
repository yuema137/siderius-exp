#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_ROOT="$(cd "${EXPERIMENT_DIR}/../../.." && pwd)"
PACK_DIR="${EXP_ROOT}/tasks/davis_future_prediction"

usage() {
    cat <<USAGE
Usage: bash experiments/davis_future_prediction/two_iteration_qualification/launch.sh \
  --siderius-checkout DIR --workspace DIR --data_dir DIR \
  [extra run_chain.sh args...]

Required:
  --siderius-checkout DIR   exact SIDERIUS checkout to execute
  --workspace DIR           fresh qualification workspace
  --data_dir DIR            DAVIS root containing DAVIS/JPEGImages/480p

Bounded defaults:
  two iterations, two tuner rounds, one epoch
  complete 60-clip training and 15-clip validation qualification manifests
  lower-is-better MSE with externally fixed Formal scope
USAGE
}

fail() {
    echo "experiments/davis_future_prediction/two_iteration_qualification/launch.sh: $1" >&2
    usage >&2
    exit 2
}

SIDERIUS_CHECKOUT=""
WORKSPACE=""
DATA_DIR=""
PASSTHROUGH=()
while [ $# -gt 0 ]; do
    case "$1" in
        --siderius-checkout)
            [ $# -ge 2 ] || fail "missing value for --siderius-checkout"
            SIDERIUS_CHECKOUT="$2"
            shift 2
            ;;
        --workspace)
            [ $# -ge 2 ] || fail "missing value for --workspace"
            WORKSPACE="$2"
            shift 2
            ;;
        --data_dir)
            [ $# -ge 2 ] || fail "missing value for --data_dir"
            DATA_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            PASSTHROUGH+=("$1")
            shift
            ;;
    esac
done

[ -n "$SIDERIUS_CHECKOUT" ] || fail "missing required argument --siderius-checkout"
[ -d "$SIDERIUS_CHECKOUT" ] || fail "--siderius-checkout is not a directory: '$SIDERIUS_CHECKOUT'"
[ -n "$WORKSPACE" ] || fail "missing required argument --workspace"
[ -d "${DATA_DIR}/DAVIS/JPEGImages/480p" ] || fail "--data_dir must contain DAVIS/JPEGImages/480p: '$DATA_DIR'"

LAUNCHER="${SIDERIUS_CHECKOUT}/sdsc_submission_scripts/run_chain.sh"
COMPOSITION="${PACK_DIR}/compositions/bounded_qualification.yaml"
LLM_CONFIG="${SIDERIUS_CHECKOUT}/llm_configs/openai_tiered_pro.json"
GENERATED_LIBRARY_DIR="${WORKSPACE}/generated_library"
[ -f "$LAUNCHER" ] || fail "production launcher not found at '$LAUNCHER'"
[ -f "$COMPOSITION" ] || fail "task composition not found at '$COMPOSITION'"
[ -f "$LLM_CONFIG" ] || fail "LLM config not found at '$LLM_CONFIG'"

export SIDERIUS_GENERATED_LIBRARY_DIR="$GENERATED_LIBRARY_DIR"

exec bash "$LAUNCHER" \
    --mode lilab \
    --task_composition "$COMPOSITION" \
    --workspace "$WORKSPACE" \
    --data_dir "$DATA_DIR" \
    --run_name davis_qualification \
    --llm_config "$LLM_CONFIG" \
    --start_iter 1 \
    --num_iterations 2 \
    --max_rounds 2 \
    --max_epochs 1 \
    --allowed_output_types regressor \
    --min_formal_batch_size 1 \
    --trial_portion 1.0 \
    --train_portion 1.0 \
    --formal_portion 1.0 \
    --formal_train_portion 1.0 \
    --formal_eval_portion 1.0 \
    --validation_max_samples 15 \
    --trial_vram_budget_gb 10 \
    --formal_vram_budget_gb 16 \
    ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}

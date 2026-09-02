#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_ROOT="$(cd "${EXPERIMENT_ROOT}/../.." && pwd)"
PACK_DIR="${EXP_ROOT}/tasks/supernemo_signal_background"

fail() {
    echo "experiments/supernemo_signal_background/launch.sh: $1" >&2
    exit 2
}

SIDERIUS_CHECKOUT=""
WORKSPACE=""
DATA_DIR=""
PROFILE="qualification"
PASSTHROUGH=()
while [ $# -gt 0 ]; do
    case "$1" in
        --siderius-checkout) SIDERIUS_CHECKOUT="$2"; shift 2 ;;
        --workspace) WORKSPACE="$2"; shift 2 ;;
        --data_dir) DATA_DIR="$2"; shift 2 ;;
        --profile) PROFILE="$2"; shift 2 ;;
        *) PASSTHROUGH+=("$1"); shift ;;
    esac
done

[ -d "$SIDERIUS_CHECKOUT" ] || fail "--siderius-checkout must name a directory"
[ -n "$WORKSPACE" ] || fail "--workspace is required"
[ -d "$DATA_DIR" ] || fail "--data_dir must name the staged dataset directory"
for process in 0nubb 2nubb Bi214 Tl208; do
    [ -f "${DATA_DIR}/data_${process}_merged.h5" ] || fail "missing data_${process}_merged.h5"
    [ -f "${DATA_DIR}/event_indexes/${process}_event_index.npz" ] || fail "missing event index for ${process}"
done

LAUNCHER="${SIDERIUS_CHECKOUT}/sdsc_submission_scripts/run_chain.sh"
COMPOSITION="${PACK_DIR}/compositions/signal_background.yaml"
LIT_CONFIG="${PACK_DIR}/framework_configs/lit_review.yaml"
LLM_CONFIG="${SIDERIUS_CHECKOUT}/llm_configs/openai_tiered_pro.json"
[ -f "$LAUNCHER" ] || fail "production launcher is absent"
[ -f "$COMPOSITION" ] || fail "task composition is absent"
[ -f "$LIT_CONFIG" ] || fail "literature-review config is absent"
[ -f "$LLM_CONFIG" ] || fail "LLM config is absent"

case "$PROFILE" in
    qualification)
        PROFILE_ARGS=(
            --run_name supernemo_qualification
            --num_iterations 2
            --max_rounds 2
            --max_epochs 1
            --trial_portion 0.01
            --train_portion 0.01
            --eval_portion 0.01
            --formal_portion 0.01
            --formal_train_portion 0.01
            --formal_eval_portion 0.01
            --trial_time_budget_minutes 1
            --formal_time_budget_minutes 1
        )
        ;;
    campaign)
        PROFILE_ARGS=(
            --run_name supernemo_campaign_v1
            --num_iterations 20
            --max_rounds 3
            --max_epochs 50
            --workflow_parameter_rules '{"train_config.epochs":{"range":{"min":5,"max":50}}}'
            --trial_portion 0.20
            --train_portion 0.20
            --eval_portion 0.20
            --formal_portion 1.0
            --formal_train_portion 0.20
            --formal_eval_portion 1.0
            --trial_time_budget_minutes 10
            --formal_time_budget_minutes 30
        )
        ;;
    *) fail "--profile must be qualification or campaign" ;;
esac

mkdir -p "$WORKSPACE"
export SIDERIUS_GENERATED_LIBRARY_DIR="${WORKSPACE}/generated_library"
cd "$EXP_ROOT"
exec bash "$LAUNCHER" \
    --mode lilab \
    --task_composition "$COMPOSITION" \
    --workspace "$WORKSPACE" \
    --data_dir "$DATA_DIR" \
    --llm_config "$LLM_CONFIG" \
    --ml_lit_review_config "$LIT_CONFIG" \
    --ml_lit_review_enabled \
    --start_iter 1 \
    --allowed_output_types classifier \
    --min_formal_batch_size 1 \
    --trial_vram_budget_gb 10 \
    --formal_vram_budget_gb 10 \
    --trial_time_admission_source measured \
    --formal_time_admission_source measured \
    --vram_probe_step_timeout_seconds 300 \
    --vram_preflight_total_timeout_seconds 600 \
    "${PROFILE_ARGS[@]}" \
    ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}

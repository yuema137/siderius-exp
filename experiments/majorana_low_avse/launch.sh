#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_ROOT="$(cd "${EXPERIMENT_ROOT}/../.." && pwd)"
PACK_DIR="${EXP_ROOT}/tasks/majorana_low_avse"

fail() { echo "experiments/majorana_low_avse/launch.sh: $1" >&2; exit 2; }

SIDERIUS_CHECKOUT=""
WORKSPACE=""
DATA_DIR=""
PROFILE="qualification"
LITERATURE="on"
DRY_RUN=0
PASSTHROUGH=()
while [ $# -gt 0 ]; do
    case "$1" in
        --siderius-checkout) SIDERIUS_CHECKOUT="$2"; shift 2 ;;
        --workspace) WORKSPACE="$2"; shift 2 ;;
        --data_dir) DATA_DIR="$2"; shift 2 ;;
        --profile) PROFILE="$2"; shift 2 ;;
        --literature) LITERATURE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; PASSTHROUGH+=("$1"); shift ;;
        *) PASSTHROUGH+=("$1"); shift ;;
    esac
done

[ -d "$SIDERIUS_CHECKOUT" ] || fail "--siderius-checkout must name a directory"
[ -n "$WORKSPACE" ] || fail "--workspace is required"
[ -d "$DATA_DIR" ] || fail "--data_dir must name the official dataset directory"
for index in $(seq 0 15); do
    [ -f "${DATA_DIR}/MJD_Train_${index}.hdf5" ] || fail "missing MJD_Train_${index}.hdf5"
done
for index in $(seq 0 5); do
    [ -f "${DATA_DIR}/MJD_Test_${index}.hdf5" ] || fail "missing MJD_Test_${index}.hdf5"
done
if [ "$DRY_RUN" -eq 0 ]; then
    "${SIDERIUS_CHECKOUT}/.venv/bin/python" \
        "${PACK_DIR}/tools/verify_dataset.py" \
        "$DATA_DIR" \
        "${PACK_DIR}/declared/dataset_manifest.json" \
        --supervised-only
fi
case "$LITERATURE" in on|off) ;; *) fail "--literature must be on or off" ;; esac

case "$PROFILE" in
    qualification)
        PROFILE_ARGS=(
            --run_name "majorana_qualification_lit_${LITERATURE}"
            --num_iterations 2 --max_rounds 2 --max_epochs 1
            --trial_portion 0.05 --train_portion 0.10 --eval_portion 0.01
            --formal_portion 0.10 --formal_train_portion 0.10 --formal_eval_portion 0.01
            --trial_time_budget_minutes 1 --formal_time_budget_minutes 2
        ) ;;
    campaign)
        PROFILE_ARGS=(
            --run_name "majorana_campaign_v1_lit_${LITERATURE}"
            --num_iterations 20 --max_rounds 3 --max_epochs 50
            --workflow_parameter_rules '{"train_config.epochs":{"range":{"min":5,"max":50}}}'
            --trial_portion 0.20 --train_portion 0.20 --eval_portion 0.20
            --formal_portion 1.0 --formal_train_portion 0.20 --formal_eval_portion 1.0
            --trial_time_budget_minutes 10 --formal_time_budget_minutes 30
        ) ;;
    demo)
        PROFILE_ARGS=(
            --run_name "majorana_model_demo_v2_lit_${LITERATURE}"
            --num_iterations 30 --max_rounds 2 --max_epochs 50
            --workflow_parameter_rules '{"train_config.epochs":{"range":{"min":5,"max":50}}}'
            --trial_portion 0.50 --train_portion 0.05 --eval_portion 0.05
            --formal_portion 1.0 --formal_train_portion 0.10 --formal_eval_portion 0.10
            --trial_time_budget_minutes 5 --formal_time_budget_minutes 10
        ) ;;
    *) fail "--profile must be qualification, campaign, or demo" ;;
esac

LIT_ARGS=()
if [ "$LITERATURE" = on ]; then
    LIT_ARGS=(--ml_lit_review_enabled --ml_lit_review_config "${PACK_DIR}/framework_configs/lit_review.yaml")
fi

mkdir -p "$WORKSPACE"
export SIDERIUS_GENERATED_LIBRARY_DIR="${WORKSPACE}/generated_library"
cd "$EXP_ROOT"
exec bash "${SIDERIUS_CHECKOUT}/sdsc_submission_scripts/run_chain.sh" \
    --mode lilab \
    --task_composition "${PACK_DIR}/compositions/low_avse.yaml" \
    --workspace "$WORKSPACE" \
    --data_dir "$DATA_DIR" \
    --llm_config "${SIDERIUS_CHECKOUT}/llm_configs/openai_tiered_pro.json" \
    --start_iter 1 \
    --allowed_output_types classifier \
    --min_formal_batch_size 1 \
    --trial_vram_budget_gb 10 --formal_vram_budget_gb 10 \
    --trial_time_admission_source measured --formal_time_admission_source measured \
    --vram_probe_step_timeout_seconds 300 --vram_preflight_total_timeout_seconds 600 \
    "${LIT_ARGS[@]}" "${PROFILE_ARGS[@]}" \
    ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}

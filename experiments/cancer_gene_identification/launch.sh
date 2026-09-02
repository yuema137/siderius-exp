#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_ROOT="$(cd "${EXPERIMENT_ROOT}/../.." && pwd)"
PACK_DIR="${EXP_ROOT}/tasks/cancer_gene_identification"

usage() {
    cat <<USAGE
Usage: bash experiments/cancer_gene_identification/launch.sh \
  --siderius-checkout DIR --workspace DIR --data_dir DIR \
  [--experiment mtg_size_qualification|mtg_campaign|two_network_qualification|eight_network_comparison] \
  [--profile qualification|campaign] \
  [extra run_chain.sh args...]

Required:
  --siderius-checkout DIR   exact SIDERIUS checkout to execute
  --workspace DIR           run workspace
  --data_dir DIR            NatureBench problem/data directory

Common extras:
  --experiment NAME default: mtg_size_qualification
  --profile NAME default: qualification
  --run_name NAME   default: cancer_gene_quickstart
  --dry-run         print the resolved child command and run nothing
USAGE
}

fail() {
    echo "experiments/cancer_gene_identification/launch.sh: $1" >&2
    usage >&2
    exit 2
}

SIDERIUS_CHECKOUT=""
WORKSPACE=""
DATA_DIR=""
EXPERIMENT="mtg_size_qualification"
PROFILE="qualification"
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
        --experiment)
            [ $# -ge 2 ] || fail "missing value for --experiment"
            EXPERIMENT="$2"
            shift 2
            ;;
        --profile)
            [ $# -ge 2 ] || fail "missing value for --profile"
            PROFILE="$2"
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
[ -d "$DATA_DIR" ] || fail "--data_dir is not a directory: '$DATA_DIR'"
case "$EXPERIMENT" in
    mtg_size_qualification)
        NETWORKS=(mtg)
        COMPOSITION_NAME="mtg_size"
        ;;
    mtg_campaign)
        NETWORKS=(mtg)
        COMPOSITION_NAME="mtg_size"
        ;;
    two_network_qualification)
        NETWORKS=(cpdb ltg)
        COMPOSITION_NAME="two_network"
        ;;
    eight_network_comparison)
        NETWORKS=(cpdb stringdb pcnet iref_v15 iref_v9 multinet mtg ltg)
        COMPOSITION_NAME="eight_network"
        ;;
    *)
        fail "unknown experiment '$EXPERIMENT'; expected mtg_size_qualification, mtg_campaign, two_network_qualification, or eight_network_comparison"
        ;;
esac

case "$PROFILE" in
    qualification)
        PROFILE_ARGS=(
            --run_name cancer_gene_quickstart
            --num_iterations 2
            --max_rounds 2
            --max_epochs 1
            --trial_portion 1.0
            --train_portion 0.25
            --eval_portion 0.25
            --formal_portion 1.0
            --formal_train_portion 1.0
            --formal_eval_portion 1.0
            --trial_vram_budget_gb 10
            --formal_vram_budget_gb 16
        )
        LIT_ARGS=()
        ADVICE_ARGS=()
        ;;
    campaign)
        [ "$EXPERIMENT" = "mtg_campaign" ] || fail "--profile campaign requires --experiment mtg_campaign"
        PROFILE_ARGS=(
            --run_name cancer_mtg_campaign_v5_lit_on
            --num_iterations 30
            --max_rounds 2
            --max_epochs 50
            --workflow_parameter_rules '{"train_config.epochs":{"range":{"min":5,"max":50}}}'
            --trial_portion 0.25
            --train_portion 0.25
            --eval_portion 1.0
            --formal_portion 1.0
            --formal_train_portion 1.0
            --formal_eval_portion 1.0
            --trial_vram_budget_gb 20
            --formal_vram_budget_gb 20
            --trial_time_budget_minutes 10
            --formal_time_budget_minutes 15
            --runtime_verification_max_wall_seconds 420
        )
        LIT_ARGS=(
            --ml_lit_review_enabled
            --ml_lit_review_config "${PACK_DIR}/framework_configs/lit_review.yaml"
        )
        ADVICE_ARGS=(
            --advice "${EXPERIMENT_ROOT}/advice/mtg_campaign_v5.json"
            --advice_sha256 "c180d6a5238ccbabeb800c5c9bb539661a4f66c8bdced1b5cbff1cda14ab673f"
        )
        ;;
    *)
        fail "unknown profile '$PROFILE'; expected qualification or campaign"
        ;;
esac
for network in "${NETWORKS[@]}"; do
    [ -f "${DATA_DIR}/${network}/data.h5" ] || fail "missing ${network}/data.h5 under '$DATA_DIR'"
done

LAUNCHER="${SIDERIUS_CHECKOUT}/sdsc_submission_scripts/run_chain.sh"
COMPOSITION="${PACK_DIR}/compositions/${COMPOSITION_NAME}.yaml"
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
    --llm_config "$LLM_CONFIG" \
    --start_iter 1 \
    --trial_time_admission_source measured \
    --formal_time_admission_source measured \
    --allowed_output_types regressor \
    --min_formal_batch_size 1 \
    --vram_probe_step_timeout_seconds 600 \
    --vram_preflight_total_timeout_seconds 1800 \
    --no-runtime_watchdog \
    "${LIT_ARGS[@]}" \
    "${ADVICE_ARGS[@]}" \
    "${PROFILE_ARGS[@]}" \
    ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}

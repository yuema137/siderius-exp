#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
EXP_ROOT="$(cd "$EXPERIMENT_DIR/../../.." && pwd -P)"
fail() { echo "tidmad-data-analysis-pair: $1" >&2; exit 2; }

usage() {
    echo "Usage: bash $0 --arm on|off --siderius-checkout DIR --workspace DIR --data_dir DIR [--expected-exp-sha SHA] [--dry-run]"
}

arm=""
checkout=""
workspace=""
data_dir=""
expected_exp_sha=""
dry_run=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --arm|--siderius-checkout|--workspace|--data_dir|--expected-exp-sha)
            [[ $# -ge 2 ]] || fail "missing value for $1"
            case "$1" in
                --arm) arm="$2" ;;
                --siderius-checkout) checkout="$2" ;;
                --workspace) workspace="$2" ;;
                --data_dir) data_dir="$2" ;;
                --expected-exp-sha) expected_exp_sha="$2" ;;
            esac
            shift 2
            ;;
        --dry-run) dry_run=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) fail "locked treatment does not accept $1" ;;
    esac
done

case "$arm" in
    on) composition="$EXPERIMENT_DIR/task_composition_on.yaml" ;;
    off) composition="$EXPERIMENT_DIR/task_composition_off.yaml" ;;
    *) fail "--arm must be on or off" ;;
esac
[[ -d "$checkout" ]] || fail "--siderius-checkout must name an existing directory"
[[ -n "$workspace" ]] || fail "--workspace is required"
[[ -n "$data_dir" ]] || fail "--data_dir is required"
checkout="$(cd "$checkout" && pwd -P)"

pin="$(tr -d '[:space:]' < "$EXPERIMENT_DIR/SIDERIUS_REVISION")"
[[ "$pin" =~ ^[0-9a-f]{40}$ ]] || fail "invalid experiment SIDERIUS_REVISION"
[[ "$(git -C "$checkout" rev-parse HEAD)" == "$pin" ]] || fail "SIDERIUS checkout differs from the experiment pin"
[[ -x "$EXP_ROOT/.venv/bin/python" ]] || fail "run uv sync --group dev --frozen in this exact experiment checkout"
launcher="$checkout/scripts/launch/run_chain.sh"
llm_config="$checkout/configs/llm/openai_tiered_pro.json"
lit_config="$EXP_ROOT/tasks/tidmad/framework_configs/lit_review.yaml"
[[ -f "$launcher" && -f "$llm_config" && -f "$lit_config" ]] || fail "required pinned launcher or LLM configuration is missing"

"$EXP_ROOT/.venv/bin/python" -c \
    'import sys; from workflows.task_composition import compose_run_task_bindings; compose_run_task_bindings(sys.argv[1])' \
    "$composition" || fail "task composition failed validation"

if [[ "$dry_run" == 0 ]]; then
    [[ "$expected_exp_sha" =~ ^[0-9a-f]{40}$ ]] || fail "effectful launch requires --expected-exp-sha"
    [[ "$(git -C "$EXP_ROOT" rev-parse HEAD)" == "$expected_exp_sha" ]] || fail "experiment checkout differs from the frozen SHA"
    [[ -z "$(git -C "$EXP_ROOT" status --porcelain)" ]] || fail "experiment checkout is not clean"
    [[ -z "$(git -C "$checkout" status --porcelain)" ]] || fail "SIDERIUS checkout is not clean"
    [[ -n "${OPENAI_API_KEY:-}" ]] || fail "OPENAI_API_KEY is unavailable"
    [[ -n "${DEEPSEEK_API_KEY:-}" ]] || fail "DEEPSEEK_API_KEY is unavailable"
    gpu_names="$(nvidia-smi --query-gpu=name --format=csv,noheader)" || fail "NVIDIA driver is unavailable"
    [[ "$gpu_names" == *"RTX 5090"* ]] || fail "local RTX 5090 is unavailable"
    [[ -d "$data_dir" ]] || fail "--data_dir must name an existing directory"
    data_dir="$(cd "$data_dir" && pwd -P)"
    for index in 15 16 17 18 19; do
        [[ -f "$data_dir/abra_training_00${index}.h5" ]] || fail "training file $index is missing"
        [[ -f "$data_dir/abra_validation_00${index}.h5" ]] || fail "validation file $index is missing"
    done
    cmp -s "$data_dir/segment_anchors.json" "$EXP_ROOT/tasks/tidmad/reference_data/segment_anchors.json" \
        || fail "staged scoring anchor is missing or differs from the approved task ruler"
    workspace="$(realpath -m "$workspace")"
    case "$workspace/" in
        "$EXP_ROOT/"*|"$checkout/"*) fail "workspace must be outside both source checkouts" ;;
    esac
    [[ ! -e "$workspace" || -d "$workspace" ]] || fail "workspace path is not a directory"
    [[ ! -d "$workspace" || -z "$(find "$workspace" -mindepth 1 -maxdepth 1 -print -quit)" ]] \
        || fail "workspace must be fresh and empty"
fi

args=(
    --mode lilab
    --task_composition "$composition"
    --workspace "$workspace"
    --data_dir "$data_dir"
    --run_name tidmad_data_analysis_pair
    --experiment_arm "data-analysis-$arm"
    --llm_config "$llm_config"
    --llm_model gpt-5.5-2026-04-23
    --ml_lit_review_config "$lit_config"
    --ml_lit_review_enabled
    --scientific_evidence_order literature_then_analysis
    --human_advice_file "$EXPERIMENT_DIR/advice.json"
    --start_iter 1
    --num_iterations 2
    --max_rounds 2
    --max_epochs 1
    --min_formal_batch_size 1
    --trial_portion 0.02
    --formal_portion 0.02
    --formal_eval_portion 0.02
    --trial_time_budget_minutes 20
    --formal_time_budget_minutes 60
    --trial_vram_budget_gb 12
    --formal_vram_budget_gb 12
    --trial_time_admission_source measured
    --formal_time_admission_source measured
    --sampling_seed 20260915
    --data_scope 15-19
    --health_gate_files 15-19
    --order_strategy_override sequential
    --file_order_override 15,16,17,18,19
    --force_fresh
    --no_auto_resume
    --no-cleanup_denoised
)

if [[ "$dry_run" == 1 ]]; then
    printf 'DRY RUN: bash %q' "$launcher"
    printf ' %q' "${args[@]}"
    printf '\n'
    exec bash "$launcher" "${args[@]}" --dry-run
fi

mkdir -p "$workspace"
export SIDERIUS_GENERATED_LIBRARY_DIR="$workspace/generated_library"
exec bash "$launcher" "${args[@]}"

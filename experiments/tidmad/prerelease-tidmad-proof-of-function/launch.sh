#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
fail() { echo "prerelease-tidmad-proof-of-function: $1" >&2; exit 2; }
checkout=""; workspace=""; data_dir=""; dry_run=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --siderius-checkout|--workspace|--data_dir) [[ $# -ge 2 ]] || fail "missing value for $1"; case "$1" in --siderius-checkout) checkout="$2";; --workspace) workspace="$2";; --data_dir) data_dir="$2";; esac; shift 2;;
    --dry-run) dry_run=1; shift;;
    -h|--help) echo "Usage: $0 --siderius-checkout DIR --workspace DIR --data_dir DIR [--dry-run]"; exit 0;;
    *) fail "locked treatment cannot be overridden: $1";;
  esac
done
[[ -d "$checkout" ]] || fail "--siderius-checkout must name a directory"
[[ -n "$workspace" ]] || fail "missing --workspace"
[[ ! -e "$workspace" || -d "$workspace" ]] || fail "workspace must be new or a directory"
[[ ! -d "$workspace" || -z "$(find "$workspace" -mindepth 1 -maxdepth 1 -print -quit)" ]] || fail "workspace must be fresh and empty"
[[ -d "$data_dir" ]] || fail "--data_dir must name a directory"
for n in 15 16 17 18 19; do
  [[ -f "$data_dir/abra_training_00${n}.h5" && -f "$data_dir/abra_validation_00${n}.h5" ]] || fail "required TIDMAD file $n is missing"
done
cmp -s "$data_dir/segment_anchors.json" "$ROOT/tasks/tidmad/reference_data/segment_anchors.json" || fail "staged segment_anchors.json is missing or differs from the approved ruler"
expected="$(tr -d '[:space:]' < "$ROOT/SIDERIUS_REVISION")"
[[ "$expected" == "61d5e5b1bcb8d569cf9904aae904ffef312e28f6" ]] || fail "unexpected SIDERIUS_REVISION"
actual="$(git -C "$checkout" rev-parse HEAD 2>/dev/null)" || fail "cannot inspect SIDERIUS checkout"
[[ "$actual" == "$expected" ]] || fail "SIDERIUS checkout revision mismatch"
launcher="$checkout/scripts/launch/run_chain.sh"; [[ -f "$launcher" ]] || fail "run_chain.sh is missing"
mkdir -p "$workspace"; workspace="$(cd "$workspace" && pwd -P)"
export SIDERIUS_GENERATED_LIBRARY_DIR="$workspace/generated_library"
args=(
  --mode lilab --task_composition "$ROOT/tasks/tidmad/compositions/continuous_regression.yaml"
  --workspace "$workspace" --data_dir "$data_dir"
  --run_name prerelease-tidmad-proof-of-function
  --llm_config "$checkout/configs/llm/openai_tiered_pro.json"
  --num_iterations 10 --max_rounds 2 --max_epochs 1
  --trial_max_epochs 1 --formal_max_epochs 1
  --trial_portion 0.1 --train_portion 0.1 --eval_portion 0.1
  --formal_portion 1.0 --formal_train_portion 0.1 --formal_eval_portion 1.0
  --formal_round_strategy full_clone --force_formal_round
  --trial_time_budget_minutes 30 --formal_time_budget_minutes 120
  --trial_vram_budget_gb 16 --formal_vram_budget_gb 16
  --trial_time_admission_source measured --formal_time_admission_source measured
  --data_scope 15-19 --health_gate_files 15-19
  --order_strategy_override sequential --file_order_override 15,16,17,18,19
  --force_fresh --no_auto_resume --no-cleanup_denoised
)
args+=(--advice "$ROOT/experiments/tidmad/prerelease-tidmad-proof-of-function/advice.json" --advice_sha256 8ca95e88d44f41da4c95a81035728661f3f44731257c62d5c515d2d2c763e213)
if [[ "$dry_run" == 1 ]]; then
  args+=(--dry-run)
fi
exec bash "$launcher" "${args[@]}"

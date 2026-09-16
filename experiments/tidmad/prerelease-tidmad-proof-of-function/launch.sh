#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
fail() { echo "prerelease-tidmad-proof-of-function: $1" >&2; exit 2; }
EXP_PYTHON="$ROOT/.venv/bin/python"
[[ -x "$EXP_PYTHON" ]] || fail "run uv sync --group dev --frozen in this exact siderius-exp checkout"
checkout=""; workspace=""; data_dir=""; dry_run=0; advice_treatment="on"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --siderius-checkout|--workspace|--data_dir) [[ $# -ge 2 ]] || fail "missing value for $1"; case "$1" in --siderius-checkout) checkout="$2";; --workspace) workspace="$2";; --data_dir) data_dir="$2";; esac; shift 2;;
    --advice-treatment) [[ $# -ge 2 ]] || fail "missing value for $1"; advice_treatment="$2"; shift 2;;
    --dry-run) dry_run=1; shift;;
    -h|--help) echo "Usage: $0 --siderius-checkout DIR --workspace DIR --data_dir DIR [--advice-treatment on|off] [--dry-run]"; exit 0;;
    *) fail "locked treatment cannot be overridden: $1";;
  esac
done
case "$advice_treatment" in
  on)
    TREATMENT="$ROOT/experiments/tidmad/information_treatments/prerelease-with-advice.yaml"
    RUN_NAME="prerelease-tidmad-proof-of-function"
    ;;
  off)
    TREATMENT="$ROOT/experiments/tidmad/information_treatments/prerelease-without-advice.yaml"
    RUN_NAME="prerelease-tidmad-proof-of-function-no-advice"
    ;;
  *) fail "--advice-treatment must be 'on' or 'off'";;
esac
[[ -d "$checkout" ]] || fail "--siderius-checkout must name a directory"
[[ -n "$workspace" ]] || fail "missing --workspace"
[[ ! -e "$workspace" || -d "$workspace" ]] || fail "workspace must be new or a directory"
[[ ! -d "$workspace" || -z "$(find "$workspace" -mindepth 1 -maxdepth 1 -print -quit)" ]] || fail "workspace must be fresh and empty"
[[ -d "$data_dir" ]] || fail "--data_dir must name a directory"
for n in 15 16 17 18 19; do
  [[ -f "$data_dir/abra_training_00${n}.h5" && -f "$data_dir/abra_validation_00${n}.h5" ]] || fail "required TIDMAD file $n is missing"
done
cmp -s "$data_dir/segment_anchors.json" "$ROOT/tasks/tidmad/reference_data/segment_anchors.json" || fail "staged segment_anchors.json is missing or differs from the approved ruler"
pin_file="$ROOT/experiments/tidmad/prerelease-tidmad-proof-of-function/SIDERIUS_REVISION"
[[ -f "$pin_file" ]] || fail "missing historical SIDERIUS_REVISION"
expected="$(tr -d '[:space:]' < "$pin_file")"
[[ "$expected" =~ ^[0-9a-f]{40}$ ]] || fail "invalid historical SIDERIUS_REVISION"
actual="$(git -C "$checkout" rev-parse HEAD 2>/dev/null)" || fail "cannot inspect SIDERIUS checkout"
[[ "$actual" == "$expected" ]] || fail "SIDERIUS checkout revision mismatch"
launcher="$checkout/scripts/launch/run_chain.sh"; [[ -f "$launcher" ]] || fail "run_chain.sh is missing"
mkdir -p "$workspace"; workspace="$(cd "$workspace" && pwd -P)"
export SIDERIUS_GENERATED_LIBRARY_DIR="$workspace/generated_library"
treatment_output="$("$EXP_PYTHON" -m experiments.shared.information_treatment \
  siderius-args \
  --manifest "$TREATMENT" \
  --repository-root "$ROOT" \
  --adapter siderius \
  --require-module literature_review)" || fail "information treatment is invalid"
mapfile -t treatment_args <<< "$treatment_output"
workflow_output="$("$EXP_PYTHON" -m experiments.shared.fixed_workflow_config \
  --config "$ROOT/experiments/tidmad/prerelease-tidmad-proof-of-function/workflow.json" \
  --repository-root "$ROOT" \
  --siderius-checkout "$checkout")" || fail "fixed workflow config is invalid"
mapfile -t workflow_args <<< "$workflow_output"
args=(
  --mode lilab
  --workspace "$workspace" --data_dir "$data_dir"
  --run_name "$RUN_NAME"
)
args+=("${workflow_args[@]}")
args+=("${treatment_args[@]}")
if [[ "$dry_run" == 1 ]]; then
  args+=(--dry-run)
fi
exec bash "$launcher" "${args[@]}"

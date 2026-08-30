#!/usr/bin/env bash
set -euo pipefail

PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<USAGE
Usage: bash tasks/tidmad/quickstart.sh \
  --siderius-checkout DIR --workspace DIR --data_dir DIR \
  [extra run_chain.sh args...]

Required:
  --siderius-checkout DIR   exact SIDERIUS checkout to execute
  --workspace DIR           fresh run workspace
  --data_dir DIR            directory containing TIDMAD HDF5 files

Bounded defaults:
  one iteration, one tuner round, one epoch
  Trial/Formal batch parity (minimum Formal batch 1)
  trial/formal portion 0.02
  trial/formal time budget 20/60 minutes

Common extras:
  --run_name NAME   default: tidmad_quickstart
  --data_scope A-B  optional TIDMAD band restriction
  --dry-run         print the resolved child command and run nothing
USAGE
}

fail() {
    echo "tasks/tidmad/quickstart.sh: $1" >&2
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
[ -d "$DATA_DIR" ] || fail "--data_dir is not a directory: '$DATA_DIR'"
compgen -G "${DATA_DIR}/abra_training_*.h5" >/dev/null || fail "no abra_training_*.h5 files under '$DATA_DIR'"
compgen -G "${DATA_DIR}/abra_validation_*.h5" >/dev/null || fail "no abra_validation_*.h5 files under '$DATA_DIR'"

LAUNCHER="${SIDERIUS_CHECKOUT}/sdsc_submission_scripts/run_chain.sh"
COMPOSITION="${PACK_DIR}/composition.yaml"
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
    --run_name tidmad_quickstart \
    --llm_config "$LLM_CONFIG" \
    --start_iter 1 \
    --num_iterations 1 \
    --max_rounds 1 \
    --max_epochs 1 \
    --min_formal_batch_size 1 \
    --trial_portion 0.02 \
    --formal_portion 0.02 \
    --trial_time_budget_minutes 20 \
    --formal_time_budget_minutes 60 \
    ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}

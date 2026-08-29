#!/usr/bin/env bash
set -euo pipefail

PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<USAGE
Usage: bash tasks/cancer_gene_identification/quickstart.sh \
  --siderius-checkout DIR --workspace DIR --data_dir DIR \
  [--workflow qualification|formal] [extra run_chain.sh args...]

Required:
  --siderius-checkout DIR   exact SIDERIUS checkout to execute
  --workspace DIR           run workspace
  --data_dir DIR            NatureBench problem/data directory

Common extras:
  --workflow NAME   default: qualification
  --run_name NAME   default: cancer_gene_quickstart
  --dry-run         print the resolved child command and run nothing
USAGE
}

fail() {
    echo "tasks/cancer_gene_identification/quickstart.sh: $1" >&2
    usage >&2
    exit 2
}

SIDERIUS_CHECKOUT=""
WORKSPACE=""
DATA_DIR=""
WORKFLOW="qualification"
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
        --workflow)
            [ $# -ge 2 ] || fail "missing value for --workflow"
            WORKFLOW="$2"
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
case "$WORKFLOW" in
    qualification)
        NETWORKS=(cpdb ltg)
        ;;
    formal)
        NETWORKS=(cpdb stringdb pcnet iref_v15 iref_v9 multinet mtg ltg)
        ;;
    *)
        fail "unknown workflow '$WORKFLOW'; expected qualification or formal"
        ;;
esac
for network in "${NETWORKS[@]}"; do
    [ -f "${DATA_DIR}/${network}/data.h5" ] || fail "missing ${network}/data.h5 under '$DATA_DIR'"
done

LAUNCHER="${SIDERIUS_CHECKOUT}/sdsc_submission_scripts/run_chain.sh"
COMPOSITION="${PACK_DIR}/workflows/${WORKFLOW}/composition.yaml"
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
    --run_name cancer_gene_quickstart \
    --llm_config "$LLM_CONFIG" \
    --start_iter 1 \
    --num_iterations 1 \
    --max_rounds 2 \
    --max_epochs 1 \
    --min_formal_batch_size 1 \
    --trial_portion 0.25 \
    --eval_portion 0.25 \
    --formal_portion 1.0 \
    --no-runtime_watchdog \
    ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}

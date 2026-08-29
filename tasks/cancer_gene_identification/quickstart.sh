#!/usr/bin/env bash
set -euo pipefail

PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${PACK_DIR}/../.." && pwd)"
LAUNCHER="${REPO_ROOT}/sdsc_submission_scripts/run_chain.sh"
COMPOSITION="${REPO_ROOT}/configs/task_composition/cancer_gene.yaml"
LLM_CONFIG="${REPO_ROOT}/llm_configs/openai_tiered_pro.json"

usage() {
    cat <<USAGE
Usage: bash examples/cancer_gene_identification/quickstart.sh \\
  --workspace DIR --data_dir DIR [extra run_chain.sh args...]

Required:
  --workspace DIR   run workspace
  --data_dir DIR    NatureBench problem/data directory containing eight network folders

Common extras:
  --run_name NAME   default: cancer_gene_quickstart
  --dry-run         print the resolved child command and run nothing
USAGE
}

fail() {
    echo "examples/cancer_gene_identification/quickstart.sh: $1" >&2
    usage >&2
    exit 2
}

WORKSPACE=""
DATA_DIR=""
PASSTHROUGH=()
while [ $# -gt 0 ]; do
    case "$1" in
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

[ -n "$WORKSPACE" ] || fail "missing required argument --workspace"
[ -d "$DATA_DIR" ] || fail "--data_dir is not a directory: '$DATA_DIR'"
for network in cpdb stringdb pcnet iref_v15 iref_v9 multinet mtg ltg; do
    [ -f "${DATA_DIR}/${network}/data.h5" ] || fail "missing ${network}/data.h5 under '$DATA_DIR'"
done
[ -f "$LAUNCHER" ] || fail "production launcher not found at '$LAUNCHER'"
[ -f "$COMPOSITION" ] || fail "task composition not found at '$COMPOSITION'"

exec bash "$LAUNCHER" \
    --mode lilab \
    --task_composition "$COMPOSITION" \
    --workspace "$WORKSPACE" \
    --data_dir "$DATA_DIR" \
    --run_name cancer_gene_quickstart \
    --llm_config "$LLM_CONFIG" \
    --start_iter 1 \
    --num_iterations 1 \
    --max_rounds 1 \
    --max_epochs 1 \
    --min_formal_batch_size 1 \
    --trial_portion 0.25 \
    --eval_portion 0.25 \
    --formal_portion 1.0 \
    ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}

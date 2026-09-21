#!/usr/bin/env bash
set -euo pipefail

EXP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
EXP_PYTHON="$EXP_ROOT/.venv/bin/python"
if [[ ! -x "$EXP_PYTHON" ]]; then
    echo "Fixed-workflow launcher requires uv sync --group dev --frozen in this exp checkout" >&2
    exit 2
fi
cd "$EXP_ROOT"
exec "$EXP_PYTHON" -m experiments.phyts_tess.main_fixed_workflow.supervisor "$@"

#!/usr/bin/env bash
set -euo pipefail
EXP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
if [[ ! -x "$EXP_ROOT/.venv/bin/python" ]]; then
    echo "Run uv sync --python 3.12 --group dev --group tutorial --frozen in $EXP_ROOT" >&2
    exit 2
fi
cd "$EXP_ROOT"
exec "$EXP_ROOT/.venv/bin/python" -m tutorials.paper.runner "$@"

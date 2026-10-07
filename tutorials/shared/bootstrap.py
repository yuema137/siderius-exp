"""Shell bootstrap checks before Python dependencies can be imported."""


def shell_setup_guard() -> str:
    """Bootstrap checks work even when Python dependencies cannot be imported."""
    return """if [[ ! -d "$EXP_CHECKOUT" ]]; then
  echo "ERROR: exp checkout is missing: $EXP_CHECKOUT. Fix EXP_CHECKOUT in this script to your cloned siderius-exp directory." >&2
  exit 2
fi
if [[ ! -x "$EXP_CHECKOUT/.venv/bin/python" ]]; then
  echo "ERROR: exp Python environment is missing. Run: cd \\"$EXP_CHECKOUT\\" && uv sync --group dev --group tutorial --frozen" >&2
  exit 2
fi
if [[ ! -f "$EXPERIMENT" ]]; then
  echo "ERROR: experiment JSON is missing: $EXPERIMENT. Save it from the notebook, then set EXPERIMENT in this script to that file." >&2
  exit 2
fi
if ! "$EXP_CHECKOUT/.venv/bin/python" -c 'import pydantic, yaml, numpy, h5py, torch, workflows' >/dev/null 2>&1; then
  echo "ERROR: exp dependencies cannot be imported. Run uv sync --group dev --group tutorial --frozen in $EXP_CHECKOUT. Do not reuse another checkout’s virtualenv." >&2
  exit 2
fi
"""

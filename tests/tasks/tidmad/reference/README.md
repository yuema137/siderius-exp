# TIDMAD reference tests

These tests own TIDMAD-specific rulers, historical numeric parity, and frozen
reference artifacts. They are scientific task evidence, not framework tests.

The ordinary synthetic/reference cohort is:

```bash
.venv/bin/python -m pytest tests/tasks/tidmad/reference/test_numeric_baselines.py -q
```

The historical fine-scalar parity test is optional and requires one explicitly
configured real validation file. It never falls back to a developer path:

```bash
TIDMAD_DATA_DIR=/absolute/path/to/TIDMAD \
  .venv/bin/python -m pytest \
  tests/tasks/tidmad/reference/test_legacy_numeric_parity.py -q
```

An absent `TIDMAD_DATA_DIR` produces a visible optional skip. Once the variable
is supplied, an invalid directory or missing `abra_validation_0000.h5` is a
test failure before scoring. This test runs the task-owned scorer against the
reference-only five-function legacy oracle; neither the oracle nor real data is
imported by production code or committed to the repository.

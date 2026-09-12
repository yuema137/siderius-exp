# Shared final-pair wrapper boundary

`common.sh` owns only checkout identity, required-input checks, fresh-workspace
refusal, inherited-environment clearing, and delegation. Task treatment values
remain in each task wrapper so their effective argv is visible and reviewable.

| task | Trial/Formal | train/eval cap | batch | VRAM GiB | probe s | worker GiB |
|---|---:|---:|---:|---:|---:|---:|
| TIDMAD | .01/.01 | 1024/omitted | 16 | 8/12 | 60/240 | 24 |
| Pets | 1/1 | 370/74 | 16 | 8/12 | 60/180 | 24 |
| DAVIS | .05/.05; eval .20 | 3/3 | 1 | 10/16 | 60/240 | 32 |
| Cancer MTG | 1/1 | full graph | 1 | 10/16 | 180/600 | 32 |

Every wrapper requests two iterations with two rounds each, one epoch, measured
Trial/Formal admission, and keeps runtime outputs outside this repository.
Actual stages require fresh runtime evidence; configuration alone is not a
qualification result.

## CPU task-format witnesses

The bounded SuperNEMO and MAJORANA witnesses exercise real CPU training,
inference, and scoring with synthetic task-format fixtures (no agent/API,
GPU, original data, or scientific claim):

```bash
cd /path/to/exact/siderius-exp-current
uv sync --group dev --frozen
.venv/bin/python -m pytest -q \
  --basetemp=/path/to/fresh/external/step04-basetemp \
  tests/test_step04_cpu_lifecycle.py -s
```

Use the exact pinned exp checkout and choose a new external basetemp for each
run. Pytest may clear that directory; never point it at original data,
existing results, or a shared repository location.

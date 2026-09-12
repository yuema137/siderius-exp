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

Every wrapper runs two iterations with two rounds each, one epoch, measured
Trial/Formal admission, and keeps runtime outputs outside this repository.

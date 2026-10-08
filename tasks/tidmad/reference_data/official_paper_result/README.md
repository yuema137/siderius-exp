# TIDMAD Official Paper-Model Denoising Scores

Denoising scores for the official band-split TIDMAD paper checkpoints, evaluated with the SIDERIUS `score_vector` pipeline on the canonical anchor map.

The four model pages and three Health JSON files are frozen evidence. Their
commands and machine paths record the historical runs; use the current
[reproduction guide](reproduction.md) for new work. Some historical experiments
use these exact saved reports, so generate new reports separately.

## Aggregation

Every headline number below is the CANONICAL `denoising_score`:

```
denoising_score = log_5.27( Σ_(f,i) per_segment[f,i] / Σ_f |S_f| )
```

Grand mean over every sampled segment across every sampled file, then log. The
reference tool retains the pinned framework helper
`execute_tools/scoring_utils.py` (§3). The current task composition instead binds
[the task scorer](../../runtime/scoring.py); both use this aggregation. Recorded
scores retain their original source and scope.

## Ruler

- Raw baseline (no denoising): **1.0007** — floor
- Ground-truth ceiling (perfect denoiser): **10.1134**

All scores are on the same log_5.27 scale, using the global s_max (295715680.14) from the committed `reference_data/segment_anchors.json`.

## Band-checkpoint mapping (from `train.py::ifile_checkpoint`)

| Band | Frequency range | Validation files | Checkpoint |
|:-----|:----------------|:-----------------|:-----------|
| 0-3   | low          | 0, 1, 2, 3         | `{Model}_0_4.pth`   |
| 4-9   | mid          | 4, 5, 6, 7, 8, 9   | `{Model}_4_10.pth`  |
| 10-14 | mid-high     | 10, 11, 12, 13, 14 | `{Model}_10_15.pth` |
| 15-19 | high         | 15, 16, 17, 18, 19 | `{Model}_15_20.pth` |

*Wavenet is intentionally excluded* (per the request that spawned this
evaluation); the paper's official wavenet is a single generalist checkpoint
scored separately by [the task-owned WaveNet scorer](../../tools/score_tidmad_official_wavenet.py).

## Summary

| Model | denoising_score | vs raw floor | vs GT ceiling | HealthGate | Details |
|:------|----------------:|-------------:|--------------:|:-----------|:--------|
| fcnet | **6.4348** | 5.4341 | -3.6786 | 20/20 healthy | [`fcnet.md`](fcnet.md) |
| punet | **3.6918** | 2.6911 | -6.4216 | 10/20 healthy | [`punet.md`](punet.md) |
| rnn | **1.5056** | 0.5049 | -8.6078 | *not scanned* | [`rnn.md`](rnn.md) |
| transformer | *pending* | — | — | 0/18 healthy, 2 missing | [`transformer.md`](transformer.md) |

The historical healthy count means all three checks passed: diversity, output
standard deviation and amplitude. The current [regression workflow](../../framework_configs/health_regression.yaml)
blocks only on amplitude collapse and records the other two checks for inspection.
The reference scan uses 1,000,000 samples; the current workflow uses its own
configured sample window. Score and health can disagree: a collapsed model can
score well through a PSD artifact.

**The score ordering and the health ordering are not the same ordering.**
`fcnet > punet > rnn` by score; by health, fcnet is clean everywhere, punet is
clean only on the two high bands, and rnn has not been scanned because its
denoised outputs were deleted. Collapse is band-dependent, so a single scalar
per model hides where a model actually works.

`rnn` requires a fresh inference run before it can be scanned — see
[reproduction guide](reproduction.md).

## Reproducibility

Render saved summary JSONs into a new external report directory, from the exp
repository root after `uv sync --group dev --frozen`:

```bash
.venv/bin/python -m tasks.tidmad.tools.render_official_paper_result \
  --summary-dir /external/tidmad-reference/summaries \
  --out-dir /external/tidmad-reference/new-report
```

This reads local evidence and writes Markdown. Optional Health JSON is read from
**the output directory**, so copy selected saved Health files there first if
needed. Missing summaries can produce pending entries. See the
[guide](reproduction.md) for saved-evidence rendering, new inference and Health
scanning with the correct filename layout.

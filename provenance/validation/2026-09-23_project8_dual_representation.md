# Project8 dual-representation preparation — 2026-09-23

Base exp master: `bf21a8c87edbb16a86c6569c195e404b386f406f` (fetched again before
freezing). Infra pin unchanged: `ae7810788fbda79c582a9cfa0097fff1262eea0e`.
Environment: this exp checkout's own `uv sync --group dev --frozen`.

## Scientific change

New task identity `phyts_project8_energy_dual`; four real channels encode two
views. Both views must contribute to model predictions. Full complex FFT of
already normalized noisy I/Q, orthonormal and unshifted, retaining all 24576
samples/bins. English physical context is in the actual composition-loaded task
configuration. No baseline score, student solution or reproduced model enters
the agent context. Original composition and scientific assets remain available.
The experiment retains existing NoPrior module switches and numerical settings.

## Verification

- Targeted command: `.venv/bin/python -m pytest -q tests/tasks/test_project8_dual_representation.py tests/tasks/test_prepared_regression.py tests/experiments/test_prepared_unit.py` — **30 passed**.
- Fixed a pre-existing stale assertion which expected agent-selected Formal
  fractions for Project8; master already freezes both to 1.0. No workflow
  parameter was changed to make the test pass.
- New transform tests cover signed spectral peaks, complex phase, inverse FFT,
  Parseval energy, event independence, nonfinite refusal, checksum corruption,
  target/snapshot preservation and no overwrite.
- Composition loaded in an independent subprocess from an unrelated directory;
  four-channel contract and physical task text are delivered, populations remain
  40000/5000/500, metric remains R2.
- New immutable data manifest SHA256:
  `8a0e2217f4ad4d28e01fac3a6826685d29c504d0c22a320425ff2871acbdedd1`.
- Independent complete-data check: all 45000 events finite; time components
  bitwise identical to source; targets and loss indices byte identical.
  SciPy inverse FFT maximum absolute error: training `1.612e-7`, validation
  `1.569e-7`; per-event Parseval check passed. All five array hashes matched.
- Two real native CPU attempts, each two epochs on 128 qualification rows,
  validation on the frozen 500 rows and inference/scoring on all 5000 rows.
  Both passed training, export, inference and independent R2/RMSE recomputation;
  restored selected-checkpoint loss and training-only target scaling agreed.
  All six native phases together took about 14 seconds. No external API call.
- The qualification fixture now sizes its head from the declared number of
  channels; its default remains two. The fixture is operator-only, never a
  candidate seed or a source of human advice.

## Claim boundary

This is data-contract and native execution qualification. It is not evidence of
an autonomous agent using both views, H100 deployment isolation, or model
quality. A fresh formal run remains unstarted. Before start, freeze the exp
revision, verify deployment/data access, inspect an actual proposed model's use
of both representations and create a clean unit with a new clock. Shape alone
cannot establish compliance with the both-views requirement. Published test
performance is not directly comparable to this campaign's validation scores.

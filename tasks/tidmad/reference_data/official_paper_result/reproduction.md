# Reproduce TIDMAD reference reports

Run these commands from the exp repository root after `uv sync --group dev
--frozen`, using this checkout's `.venv`. Replace `/external/...` placeholders
with your external source, data and output paths. Keep new outputs outside both
source repositories.

The [directory README](README.md) summarizes frozen results. Its four model
pages and three Health JSON files retain historical commands, machine paths and
observations. In particular, FCNet is pinned advice provenance; do not overwrite
these artifacts or treat an old command as a current invocation.

## Render saved evidence

The [renderer](../../tools/render_official_paper_result.py) reads
`tidmad_official_<model>_banded_score.json` from `--summary-dir`. It reads optional
`<model>_health.json` from **`--out-dir`**, then writes Markdown there. It performs
no inference or Health scan.

Create a new external report directory. To include saved Health observations,
copy the selected committed Health JSON files into it first, preserving their
identity and recording that they came from this repository revision. This is
reuse of recorded evidence, not a new scan. For example:

```bash
mkdir -p /external/tidmad-reference/new-report
cp tasks/tidmad/reference_data/official_paper_result/fcnet_health.json \
  /external/tidmad-reference/new-report/
.venv/bin/python -m tasks.tidmad.tools.render_official_paper_result \
  --summary-dir /external/tidmad-reference/summaries \
  --out-dir /external/tidmad-reference/new-report
```

Supply the saved summaries you intend to render; they are not recovered from
model Markdown. Missing summaries can produce pending rows or Health-only pages.
The renderer also refuses to replace an existing scored page with a Health-only
page, or an existing summary README with an all-pending table. These protections
do not make the frozen report tree an appropriate output directory.

## Generate new inference and scores

The [banded reference scorer](../../tools/score_tidmad_official_banded.py)
requires all five location arguments below. Use external TIDMAD source,
checkpoints and data matching the intended scientific identity and the committed
[anchor map](../segment_anchors.json). This performs new inference and scoring,
writing large denoised HDF5 files and summary JSON; rendering alone does not need
this step.

```bash
.venv/bin/python -m tasks.tidmad.tools.score_tidmad_official_banded \
  --models fcnet \
  --tidmad-repo /external/TIDMAD-source \
  --checkpoint-dir /external/TIDMAD-checkpoints \
  --data-dir /external/TIDMAD-data \
  --anchor-map tasks/tidmad/reference_data/segment_anchors.json \
  --work-dir /external/tidmad-reference/new-inference
```

Model choices are `fcnet`, `punet`, `rnn` and `transformer`. Omitting
`--file-indices` selects all 20 validation files. A subset produces a
partial-scope scalar, which is not comparable to the full-scope score. The
scorer keeps denoised outputs by default; do not select
`--delete-denoised-after-score` when a Health scan is still needed.

Each model writes `denoised_<model>/` and
`tidmad_official_<model>_banded_score.json` under `--work-dir`. Use that work
directory as the renderer's `--summary-dir` for these new results.

The reference scorer imports `execute_tools.scoring_utils.score_vector` from the
pinned framework. The current task composition binds
[the task-owned scorer](../../runtime/scoring.py). Both use the linear grand mean
across sampled segments, followed by log base 5.27; this distinction does not
change the source or scope of any recorded result.

## Scan Health with an explicit filename layout

The [scanner](../../tools/official_paper_health_scan.py) reads existing denoised
and target HDF5 files and writes metrics JSON. For fresh output from the banded
scorer above, use its filename pattern explicitly; the scanner's default is the
older pattern and will not match these files:

```bash
.venv/bin/python -m tasks.tidmad.tools.official_paper_health_scan \
  --model fcnet \
  --denoised-dir /external/tidmad-reference/new-inference/denoised_fcnet \
  --target-dir /external/TIDMAD-data \
  --pattern 'abra_validation_denoised_{model}_tidmad_official_banded_{index:04d}.h5' \
  --peek-samples 1000000 \
  --json-out /external/tidmad-reference/new-report/fcnet_health.json
```

For legacy `tidmad_reproduction/<model>/full_20_files` outputs, point
`--denoised-dir` at that existing directory and instead use:

```bash
--pattern 'abra_validation_denoised_{model}_{index:04d}.h5'
```

Choose from the actual filenames, not the model name. Generated Health sections
show an explicitly labelled legacy-layout recipe using recorded input paths;
relocate those paths and change the pattern when using fresh banded outputs.
Older Health records may omit `target_dir`, in which case the generated recipe
uses an external placeholder that you must fill in.

For an intentionally incomplete scan, add `--allow-partial`. It reports missing
files without generating replacements; zero matching files still fails. The
frozen Transformer record scanned 18 files, missing indices 18 and 19, and has no
scalar score. RNN's denoised outputs were deleted, so its Health result requires
fresh inference; no recorded Health result can be inferred from its score.

The reference scan peeks at 1,000,000 samples. Its healthy count is the conjunction
of diversity, output standard deviation and amplitude checks, not today's
regression blocking verdict or proof of model quality. Historical production
blocking gates used 100,000 samples; the selected roster independently owns
sampling and dispositions. The current [regression roster](../../framework_configs/health_regression.yaml)
records diversity/std and blocks only on amplitude collapse. Preserve recorded
thresholds, scope and source when comparing scans.

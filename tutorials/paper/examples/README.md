# Recorded tutorial examples

Open any of the [four notebooks](../notebooks/README.md) to see real training
samples and results before installing anything. Each notebook embeds its images,
so the examples remain visible on GitHub and in a copied external notebook.
They are clearly labeled **archived examples**, separate from your own run.

| Task | Training sample | Three-iteration result | Exact scores | Provenance |
|---|---|---|---|---|
| TESS | [Light curve before/after preprocessing](tess-data.png) | [Progress](tess-progress.png) | [CSV](tess-progress.csv) | [JSON](tess-example.json) |
| TIDMAD | [Noisy input and injected target](tidmad-data.png) | [Progress](tidmad-progress.png) | [CSV](tidmad-progress.csv) | [JSON](tidmad-example.json) |
| Project8 | [Time I/Q and complex FFT](project8-data.png) | [Progress](project8-progress.png) | [CSV](project8-progress.csv) | [JSON](project8-example.json) |
| LIGO | [Two prepared detector channels](ligo-data.png) | [Progress](ligo-progress.png) | [CSV](ligo-progress.csv) | [JSON](ligo-example.json) |

These examples come from real RTX 5090 runs on September 29–30, 2026. The JSON
files record their source revisions, numerical settings, elapsed time, launcher
exit code and verification records for the original results. CSV source paths are relative to the original
run workspace; the original model checkpoints and full run directories are not
included. No API keys, machine-local paths or raw datasets are published here.
The data figures show the first training observation/window, not a selected
successful prediction or held-out test example.

Read the outcome honestly: TESS's scored attempts passed their configured checks;
TIDMAD's scored attempts failed mode-collapse checks and remain hollow points.
Project8 and LIGO completed with negative R², worse than the validation-mean
baseline. Their tasks explicitly declare no Health checks. All four examples
show a working workflow, not paper artifact reproduction or a quality guarantee.
The solid line means highest recorded score, including invalid results.
Unscored attempts stay in the CSV and are not plotted as zero.

To make **your own** figures, follow your notebook's setup guide, then:

1. Quick A saves and reviews the actual task and experiment files.
2. **Inspect your own training data** plots one training observation from the
   saved experiment. Change `PREVIEW_ROW` to inspect another. This reads local
   data only and needs no provider key or GPU.
3. Quick B invokes your saved script. This requires the configured environment,
   data, exported keys and supported GPU; it incurs API/GPU work.
4. Quick C plots your actual run records and saves PNG, SVG and CSV under your
   external project's `plots/` directory. The archived images above do not change.

The sample plot calls `tutorials.paper.data_preview.plot_training_example`;
progress uses the existing `plot_progress`/prepared `plot_demo` helpers. Neither
plotting path trains a model, downloads data or calls an LLM.

# Tutorials: learn a task, save your experiment, run it

**Browse first:** each notebook includes real training-sample pictures, a recorded
three-iteration result plot and exact scores. No setup is needed to view these
archived examples; your own results appear after you configure and run the demo.
See the [example gallery](paper/examples/README.md) for provenance and limitations.

These tutorials are for readers who are new to SIDERIUS. They show how to copy a
scientific task into your own project, change its experiment settings, inspect
the saved files, and start a run from a terminal script. The notebooks teach and
edit configuration, then their Run All quick demo invokes the saved script and
plots three iterations of real results. The scripts own research execution.
Run All requires prepared data/exported keys and incurs API/GPU work;
`RUN_QUICK_DEMO=False` skips API/GPU execution. Quick demo A still saves
input files in your external project.

New projects use **GPT-6 Luna across all workflow LLM stages** to check the
process before spending more on scientific searches. Read the
[LLM configuration levels](shared/README.md): offline checks, inexpensive live
demos, the paper's recommended research LLM configuration or your own model
choices, and separately archived paper replay.
The gallery contains earlier recorded runs; it is not evidence of a Luna run.

**Start with [the paper tutorial guide](paper/README.md).** It explains installation,
API keys, data preparation, supported hardware, and what the demos can establish.

| Tutorial | What you will learn | Open |
|---|---|---|
| TESS: stellar rotation from light curves | Change iterations, Trial/Formal data fractions, time/VRAM budgets and whole-star train/validation membership | [TESS notebook](paper/notebooks/01_tess_tutorial.ipynb) · [setup guide](paper/README.md#1-install-in-the-two-exact-checkouts) |
| TIDMAD: waveform denoising, one band | Change budgets and fractions; assign file indices to training, workflow validation and a separate final test | [TIDMAD guide](paper/tidmad/README.md) · [notebook](paper/notebooks/02_tidmad_tutorial.ipynb) |
| Project8: electron energy from time and frequency views | Inspect four-channel inputs, change budgets/fractions and create a new event split | [Project8 notebook](paper/notebooks/03_project8_tutorial.ipynb) · [setup](paper/prepared/README.md) |
| LIGO: chirp mass from two detector channels | Prepare a tiny real-data subset, run three iterations and inspect R² | [LIGO notebook](paper/notebooks/04_ligo_tutorial.ipynb) · [setup](paper/prepared/README.md) |

The `paper/` directory groups teaching examples based on the paper's tasks.
**These four tutorials are workflow demos, not reproductions of paper artifacts.** The
[paper artifact reference](../experiments/paper-artifacts.md) points to frozen
settings, recorded source pairs and missing-evidence limits. New LLM searches are not guaranteed to recover the paper's models or
scores, and very small training budgets can yield unusable models.

Read notebooks here to browse, but execute only the copies initialized in your
own external project. Keep datasets, API keys and run outputs out of both source
repositories. The intended public sources are
[yuema137/siderius-exp](https://github.com/yuema137/siderius-exp) and
[yuema137/SIDERIUS](https://github.com/yuema137/SIDERIUS).

## Supplementary tasks

[Supplementary process demos](supplementary/README.md) start with Oxford-IIIT Pet image classification. These use the same notebook/edit/save/script/plot sequence and are not paper artifacts.

# Tutorials: learn a task, save your experiment, run it

These tutorials are for readers who are new to SIDERIUS. They show how to copy a
scientific task into your own project, change its experiment settings, inspect
the saved files, and start a run from a terminal script. The notebooks teach and
edit configuration; the scripts run the research workflow.

**Start with [the paper tutorial guide](paper/README.md).** It explains installation,
API keys, data preparation, supported hardware, and what the demos can establish.

| Tutorial | What you will learn | Open |
|---|---|---|
| TESS: stellar rotation from light curves | Change iterations, Trial/Formal data fractions, time/VRAM budgets and whole-star train/validation membership | [TESS notebook](paper/notebooks/01_tess_tutorial.ipynb) · [setup guide](paper/README.md#1-install-in-the-two-exact-checkouts) |
| TIDMAD: waveform denoising, one band | Change budgets and fractions; assign file indices to training, workflow validation and a separate final test | [TIDMAD guide](paper/tidmad/README.md) · [notebook](paper/notebooks/02_tidmad_tutorial.ipynb) |

The `paper/` directory groups teaching examples based on the paper's tasks.
**It does not yet contain four completed paper-reproduction tutorials:** TESS
and one-band TIDMAD are implemented; LIGO and Project 8 do not yet have runnable
notebooks. New LLM searches are not guaranteed to recover the paper's models or
scores, and very small training budgets can yield unusable models.

Read notebooks here to browse, but execute only the copies initialized in your
own external project. Keep datasets, API keys and run outputs out of both source
repositories. The intended public sources are
[yuema137/siderius-exp](https://github.com/yuema137/siderius-exp) and
[yuema137/SIDERIUS](https://github.com/yuema137/SIDERIUS).

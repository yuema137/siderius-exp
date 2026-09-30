# TESS configuration templates

These files support the TESS tutorial. They are not a shared launch
configuration for all four tasks, and users should not edit them in this repo.

| File | Purpose |
|---|---|
| [tess_experiment.json](tess_experiment.json) | Illustrates the TESS runner's experiment fields. Its absolute paths are placeholders and its one-iteration values are not the notebook's three-iteration quick-demo settings. |
| [tess_source.json](tess_source.json) | Pins the public dataset revision, training/validation source filenames and expected SHA-256 values used for TESS data preparation. It contains no credentials. |

Start with the [TESS setup guide](../README.md). Initialize a separate project,
then use its copied notebook to save actual settings in `experiments/*.json`.
Quick A reopens the saved settings and shows which generated `scripts/run-*.sh`
will read them. Change data membership through the demonstrated task/data
preparation helpers; do not hand-edit hashes to make unrelated data fit.

For the other tasks, use their own setup and generated experiment files:
[TIDMAD](../tidmad/README.md) or [Project8/LIGO](../prepared/README.md).

# TESS configuration templates

These files support the TESS tutorial. They are not a shared launch
configuration for all four tasks, and users should not edit them in this repo.

| File | Purpose |
|---|---|
| [tess_experiment.json](tess_experiment.json) | Illustrates the TESS runner's experiment fields. Its absolute paths are placeholders and its one-iteration values are not the notebook's three-iteration quick-demo settings. |
| [tess_source.json](tess_source.json) | Pins the public dataset revision, training/validation source filenames and verification records used for TESS data preparation. It contains no credentials. |

Start with the [TESS setup guide](../tess/README.md). Initialize a separate project,
then use its copied notebook to save actual settings in `experiments/*.json`.
Quick A creates or checks the named demo, then shows which generated
`scripts/run-*.sh` reads its settings. It refuses changed settings under an
already used name. Change data membership through the demonstrated task/data
preparation helpers; do not alter verification records to make unrelated data pass.

For the other tasks, use their own setup and generated experiment files:
[TIDMAD](../tidmad/README.md) or [Project8/LIGO](../prepared/README.md).

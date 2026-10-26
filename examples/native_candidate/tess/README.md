# TESS candidate example

First download and prepare the TESS training/validation data using the
[existing TESS data instructions](../../../tutorials/paper/tess/README.md#3-download-and-prepare-data-once),
or locate the matching data you already prepared. Follow that tutorial's own
pinned environment for its data tools. Then use the
[common candidate project steps](../README.md) with your resulting data directory.

This task predicts a star's rotation frequency from a normalized one-channel,
1,024-sample light curve. It returns one unbounded scalar, including valid negative
targets. Its selection metric is R², higher is better; the task does not force a
training objective. The original star splits remain task-owned; held-out test
stars are not selected.

Your data directory needs `tess_rotation_train.npz` and `tess_rotation_val.npz`.
The project keeps them as external references. Its saved
`tasks/phyts_tess/compositions/rotation_regression.yaml` selects the copied task;
`workflow.py` describes the candidate steps and `llm/agents.json` selects model
routes. Edit your project copies, preserve earlier runs, and review before launch.

The [profile](profile.json) selects the source combination for this example.
Composition and preparation checks do not establish dataset correctness or model
quality. Read the native inspection report before accepting your current snapshot.

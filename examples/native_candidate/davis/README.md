# DAVIS future-frame candidate example

First download and verify the official frames using the existing
[DAVIS data instructions](../../../tutorials/supplementary/davis/README.md#2-download-the-archive-and-extract-the-frames).
Use that tutorial's own pinned exp environment for its archive helper. The native
candidate steps use the separately selected framework checkout's own environment.

This task predicts the next four RGB frames from eight context frames. Inputs are
float32 [3,8,128,224] tensors per clip; outputs must be [3,4,128,224], with frame
values normalized to [0,1]. Its primary metric is MSE, lower-is-better; PSNR is
higher-is-better and MAE is lower-is-better. The task selects its exact mean-L1
custom loss, rather than smooth-L1. The copied bounded composition selects
60 training and 15 validation clips from disjoint sequences. The final-test split
is not selected.

Follow the [common project steps](../README.md), setting:

```bash
export EXAMPLE=davis
export TASK_ASSETS=tasks/davis_future_prediction
export TASK_DATA="/absolute/path/to/DAVIS_2017"
```

Keep `DAVIS/JPEGImages/480p/` beneath `TASK_DATA`; do not point at `JPEGImages`
itself. Export the task assets into your new external project before inspection.
Expect `mse (lower is better)`, and read the report before explicit acceptance.
The [profile](profile.json) selects the copied composition; edit your project copies
of `workflow.py`, task declarations and `llm/agents.json`, then review again.

This candidate-only slice prepares Propose → Implement → Validate, with no training
or scientific score. Composition/preparation checks do not verify frame availability
or video decode quality. Keep earlier runs; launch only after reviewing task, source,
routes, private credential readiness and the paid API effects in the common guide.

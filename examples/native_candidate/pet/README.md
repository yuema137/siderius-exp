# Oxford-IIIT Pet candidate example

First download and verify the official images using the existing
[Pet data instructions](../../../tutorials/supplementary/pet/README.md#2-download-the-images).
Use that tutorial's own pinned exp environment for its download helper. The native
candidate steps use the separately selected framework checkout's own environment.

This task classifies one RGB photograph into 37 pet breeds. Its fixed preprocessing
resizes the shorter side to 160 pixels and center-crops to 144×144, with float32
pixels in [0,1]. Models return 37 logits without softmax. Accuracy is higher-is-better;
the task selects categorical cross-entropy. The copied bounded composition selects
370 training and 74 validation images; the independent final set is unselected.

Follow the [common project steps](../README.md), setting:

```bash
export EXAMPLE=pet
export TASK_ASSETS=tasks/oxford_iiit_pet
export TASK_DATA="/absolute/path/to/OXFORD_IIIT_PET/images"
```

Point `TASK_DATA` at the directory containing individual JPEGs, not its parent.
Export the task assets into your new external project before inspection. Expect
`accuracy (higher is better)`, and read the report before explicit acceptance.
The [profile](profile.json) selects the copied composition; edit your project copies
of `workflow.py`, task declarations and `llm/agents.json`, then review again.

This candidate-only slice prepares Propose → Implement → Validate, with no training
or scientific score. Composition/preparation checks do not verify image availability
or decode quality. Keep earlier runs; launch only after reviewing task, source,
routes, private credential readiness and the paid API effects described in the
common guide.

# Recorded Pet demo

These are measured outputs from a completed three-iteration process demo,
not paper results. The [provenance receipt](provenance.json) records exact
source revisions, task identity, source-record hashes, dataset counts and the
conservative validation-budget accounting.

![Task-materialized training images](images.png)

![Measured Formal accuracy versus iteration](score-versus-iteration.png)

| Iteration | Trial accuracy | Trial Health | Formal accuracy | Formal Health |
|---|---:|---|---:|---|
| 1 | 0.0000 | FAIL: collapsed predictions | 0.1486 | PASS |
| 2 | 0.1081 | PASS | 0.2162 | PASS |
| 3 | 0.1081 | PASS | 0.1892 | PASS |

The chart uses the same renderer/style as the four paper-task tutorials. It
plots Formal records only. All Formal points passed Health in this run; it
therefore has no hollow points. Measured failed Formal records are drawn hollow
when present. The solid line is the best recorded score, including failed
records if present; it is not a scientific-certification frontier.

The first eight-epoch calibration was stopped because validation produced only
eight timing observations and did not establish steady state. Its cost/time is
included in the qualification totals. A separate experiment with a 32-epoch
ceiling completed; no framework verification or Health thresholds were weakened.
This is one qualified hardware/model sequence, not a guarantee for every generated
model or device.

The complete notebook took about 19.4 minutes. Including the initial calibration,
API usage was conservatively accounted at $2.96 and the GPU-time upper bound was
23.6 minutes (counting all API waiting as GPU time). Those numbers describe this
qualification, not limits automatically imposed by the public notebook.

[CSV](score-versus-iteration.csv) and [SVG](score-versus-iteration.svg) accompany
the PNG. CSV paths and notebook text use portable display paths; values are
unchanged. The notebook does not load this example as the user's result. Follow
the [tutorial](../README.md) to generate a fresh run in your own project.

Images are from the Oxford-IIIT Pet dataset and use the task's declared
preprocessing. Dataset identity and acquisition details live in the
[task package](../../../../tasks/oxford_iiit_pet/README.md).

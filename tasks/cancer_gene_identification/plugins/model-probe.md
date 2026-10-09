# Cancer candidate input fixture

`CancerGeneTaskDataPath.model_validation_input` implements the framework's optional
`ModelProbeRequest` capability. It creates deterministic CPU float32 packed graph
inputs for candidate forward/backward checks without reading NatureBench files.

The input is `[1, R, 68]`, matching the task's existing one-graph batch constraint.
It uses enough leading node rows to support the remaining distinct directed edge
rows. Node IDs are contiguous integers, edge endpoints identify existing nodes,
and edges contain no self-loops. Node/split markers are binary; edge feature and
split columns remain zero. Node features are synthetic, finite values. Even a
single-record request is valid and contains one node and no edges.

The shared framework checker owns concrete geometry, task parameter-rule
resolution, source identity and candidate verdicts. The task owns packed-graph
semantics. This fixture does not alter the real data loader, original label
masks, objective, metrics, graph sampling or training budgets. It is not a memory
calibration sample, a score benchmark, or a substitute for validation data.

The capability changes task source identity. New runs use freshly initialized
external projects and the current pinned framework. Existing copied tasks and
archived run records are not rewritten; replay uses their explicit source pins.
Tests in `tests/tasks/cancer_gene_identification/test_candidate_probe.py` verify
semantic properties independently and exercise all native candidate consumers.

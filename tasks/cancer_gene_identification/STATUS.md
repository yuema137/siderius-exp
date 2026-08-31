# STATUS — NatureBench cancer-gene identification

## Maturity: **L2 — real-data GPU training proven; no complete discovery-chain witness**

The maturity vocabulary and pack-governance authority are
`docs/design/siderius_generic_framework_upgrade.md` §22.23. This pack is an
exploratory fourth task, not one of the persistent §22.9a tracks.

Proven on the `ligroup` development server:

- the shipped composition resolves every required authority fail-closed;
- a synthetic complete graph materializes as node plus edge records;
- train and validation labels remain separated by their declared masks;
- the reference message-passing plugin, masked BCE, prediction codec, and
  unweighted mean AUPRC execute together on synthetic HDF5 data;
- the external experiment launcher completes `--dry-run` and emits the
  expected composed child command;
- all eight official NatureBench HDF5 files match their source SHA-256 values;
- the bounded `cpdb` and `ltg` task composition materializes real graph
  records while preserving node counts and train masks;
- the source-provided train, validation, and test masks are mutually disjoint.
- one real `cpdb` epoch completed on an RTX 5090 through the task-owned data
  path, custom model, custom objective, validation, checkpoint, and result
  persistence surfaces.
- one cold-start LLM-driven Trial completed training, inference, and validation
  AUPRC scoring on `cpdb` (`0.18473163467815523`); its subsequent two-network
  Formal attempt was killed by the generic setup-only watchdog defect tracked
  in SIDERIUS issue `#388` before validation completed;
- a second cold-start Trial scored `ltg` validation AUPRC at
  `0.20331661762333703`;
- a second cold-start run completed Formal training after disabling the broken
  watchdog, then exposed the variable-shape generic inference batching defect
  tracked in SIDERIUS issue `#389` (`inference_batch=64` attempted to stack the
  complete `cpdb` and `ltg` graph tensors);
- a phase-only replay of that exact Formal checkpoint with inference batch 1
  completed task-owned inference and scoring: `cpdb=0.3519765294390681`,
  `ltg=0.18345607540350573`, and unweighted mean validation
  AUPRC `0.2677163024212869`.
- SIDERIUS `60fffb1e` makes that batch limit task-owned and transports it
  through admission and execution. A real two-network checkpoint witness on
  the RTX 5090 selected batch 1, emitted two inference batches, and reproduced
  the same per-network and mean AUPRC values exactly.
- a fresh cold-start chain against `siderius-exp` `84bfdb0` and SIDERIUS
  `60fffb1e` reached proposal, implementation, correction, validation, and
  tuner preflight. Its generated `sparse_residual_appnp_gcn` candidate did not
  reach training: four completed configurations exhausted the bounded
  180-second training probe, and a fifth was operator-stopped after the same
  failure class was isolated. The artifacts remain diagnostic evidence and
  are not a scored result.

Not yet proven:

- acquisition and identity verification of the eight real NatureBench HDF5
  files on TestPod;
- complete two-network Formal inference and mean AUPRC scoring inside an
  uninterrupted discovery chain on the repaired batching revision;
- HealthGate behavior or campaign resume;
- a complete LLM-driven discovery iteration;
- reproduction or improvement of AI-Build-AI's artifact mean AUPRC
  `0.7725415502369475`;
- final train-plus-validation refit and hidden-test evaluation.

L3 and L4 are not claimed.

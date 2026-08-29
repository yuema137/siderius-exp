# STATUS — NatureBench cancer-gene identification

## Maturity: **L2 — real-data composition and materialization proven; no real GPU chain witness**

The maturity vocabulary and pack-governance authority are
`docs/design/siderius_generic_framework_upgrade.md` §22.23. This pack is an
exploratory fourth task, not one of the persistent §22.9a tracks.

Proven on the `ligroup` development server:

- the shipped composition resolves every required authority fail-closed;
- a synthetic complete graph materializes as node plus edge records;
- train and validation labels remain separated by their declared masks;
- the reference message-passing plugin, masked BCE, prediction codec, and
  unweighted mean AUPRC execute together on synthetic HDF5 data;
- the production quickstart completes `--dry-run` and emits the expected
  composed child command.
- all eight official NatureBench HDF5 files match their source SHA-256 values;
- the bounded `cpdb` and `ltg` qualification workflow materializes real graph
  records while preserving node counts and train masks;
- the source-provided train, validation, and test masks are mutually disjoint.

Not yet proven:

- acquisition and identity verification of the eight real NatureBench HDF5
  files on TestPod;
- real GPU training, inference, scoring, HealthGate behavior, or campaign
  resume;
- reproduction or improvement of AI-Build-AI's artifact mean AUPRC
  `0.7725415502369475`;
- final train-plus-validation refit and hidden-test evaluation.

L3 and L4 are not claimed.

# Cancer Gene Identification Real-Data Acquisition

Date: 2026-08-29

## Scope

This receipt records acquisition of the complete eight-network NatureBench task
`s41551-024-01312-5` for Cancer Gene Identification qualification and campaign
execution on the `ligroup` RTX 5090 server.

The complete dataset is required for campaign results comparable with
AI-Build-AI. Bounded qualification may select a smaller set of complete
networks, but it must not alter a network, replace real data with placeholders,
or be reported as an eight-network campaign result.

## Source

- Dataset: `FrontisAI/NatureBench`
- Source revision: `9e6a69f10865dd56f4991b49d1c974e2006b6b18`
- Task path: `tasks/s41551-024-01312-5/problem/data`
- Local data root: `/home/klz/Data/NatureBench/tasks/s41551-024-01312-5/problem/data`

Dataset bytes are external runtime inputs and are not committed to this
repository.

## Verified files

| Network | SHA-256 |
|---|---|
| `cpdb` | `9b94630a4a3fbdad208fe2c2ae558dd98b482e3b3bd61341b09fe2d991a6db2d` |
| `iref_v15` | `0b7b6a040d3a9d805897dee1bbcd09a178c03c5ad5f56e00a218bf28d6494d28` |
| `iref_v9` | `f7c097f195eb449e04a4ad855020ba604536b6130335cf1dd8f9ffeceb3c1b86` |
| `ltg` | `2f3d1eb412ec0b98f590fce0ff0f330799f28ce35cc97b1d600f7ec957d9b34f` |
| `mtg` | `5a3755bd6ec22e7792a73610b3df618fb8e6efc6128dc45757239aa9750e2285` |
| `multinet` | `62a9c5aebf610f2fbe6c615b6a91837b4aa6160117ce71204fa85d5aaf9da8b6` |
| `pcnet` | `9272d605ea378e60cf93f5a820b80e16ceed9bb03bce9adc37455c232d56f7cb` |
| `stringdb` | `7f08390adba2575f62fe52943810e9aa83526d84e4cc914778ce2ba95728a83a` |

Every file opened successfully with HDF5. Each network exposes the declared
`network`, `features`, `mask_train`, `mask_val`, `mask_test`, `y_train`, and
`y_val` datasets. The observed node counts and train, validation, and test mask
counts agree with the NatureBench task description.

The external checkpoint against SIDERIUS `8be2874d` also materialized the real
`cpdb` and `ltg` networks through the task-owned data path. It preserved 13,627
and 18,358 nodes respectively, preserved 2,013 and 2,311 active training nodes,
and produced 518,005 and 3,969,960 packed node-plus-edge records. The
checkpoint refused placeholder-sized files and verified pairwise-disjoint
train, validation, and test masks before composition.

## Execution policy

- Full campaign: all eight complete networks and the benchmark-provided split
  masks.
- Initial qualification: complete `cpdb` and `ltg` networks, representing a
  homogeneous PPI network and a heterogeneous regulatory network.
- Qualification scores must not be compared with AI-Build-AI's eight-network
  mean AUPRC.
- Hidden test labels remain outside model development and candidate selection.

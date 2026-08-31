# TIDMAD Gold external dry-run validation — 2026-08-30

## Scope

This validation proves path ownership and resolved launcher behavior only. It
does not authorize or qualify an H100 workload.

## Framework

- SIDERIUS revision: `2406dadd8dc3e80d87733cdc1a68494d3d8cead7`
- Execution entrypoint: the selected checkout's existing
  `sdsc_submission_scripts/run_chain.sh`
- Campaign entrypoint: `campaigns/tidmad_gold/scripts/run_gold_campaign.sh`

## Evidence

- Stage 1 dry-run resolved one selected band without launching or writing run
  state.
- The child command used the explicitly selected SIDERIUS checkout.
- Task config resolved from `campaigns/tidmad_gold/task/`.
- Stage-1 Health resolved from `campaigns/tidmad_gold/workflows/stage1/`.
- `min_formal_batch_size=1`, `formal_time_budget_minutes=180`, the v0.1.5 run
  identity, and the existing band-to-GPU map remained unchanged.
- A byte-different task-config override was refused before dispatch.
- Stage 2 was refused with `GOLD_STAGE2_AUTHORIZED=false` and no child launch.

## Remaining qualification

The imported deployment preflight still contains historical in-repository
assumptions and unrelated X9 surfaces. Runtime-profile binding, persistent
storage, dataset presence, four-H100 topology, and the final release revision
must be qualified separately before Stage 1 launch.

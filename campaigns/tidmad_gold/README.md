# TIDMAD Gold Campaign

- Status: stopped
- Launch authorization: not authorized
- Stage 2 authorization: not authorized
- Task package: `tasks/tidmad/`
- Planned deployment intent: four-H100 campaign pool

This existing campaign coordinates the TIDMAD Gold band and stage topology.
Its imported protocol, scripts, and frozen decisions remain under this package.
The planned hardware pool does not authorize relaunch and does not change the
campaign's scientific treatment.

## Campaign-owned workflows

- `workflows/stage1/health_checks.yaml` is the current calibrated Stage-1
  Health treatment: `amplitude_collapse` is the sole blocking gate;
  diversity and standard-deviation checks are observational.
- `workflows/stage2/` records the distinct Stage-2 boundary. It contains no
  executable launcher and Stage 2 remains unauthorized.
- `config/llm_routing.json` owns the frozen role-to-model routing consumed by
  every Gold chain. SIDERIUS owns the generic parser, not this campaign value.
- Stage 1 freezes Trial and Formal VRAM ceilings at `40/40` when no complete
  operator override pair is supplied. Dry-runs, child argv, and launch
  manifests report the same effective values.
- `task/health_checks_effective_gold.yaml` is a preserved historical
  materialization, not the authoring authority for a future fresh launch.

The Stage-1 launcher now requires an explicit SIDERIUS checkout and resolves
campaign-owned task and Health files from this package. Its separated dry-run
is qualified in `provenance/validation/2026-08-30_tidmad_gold_external_dry_run.md`.
This does not qualify an H100 launch: deployment preflight, runtime-profile
binding, dataset availability, and the final release revision remain pending.

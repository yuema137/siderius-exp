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
- `gold_advice_v6_regression.json` is the operator-approved Gold advice
  artifact. Its exact bytes are campaign treatment and must be hashed at
  launch.
- `fcnet_band_references.json` is the approved per-band FCNet reference used
  by the Stage-1 early-stop rule. Its recorded absolute paths are historical
  provenance only; the launcher consumes the band values from this file.
- Stage 1 freezes Trial and Formal VRAM ceilings at `40/40` when no complete
  operator override pair is supplied. Dry-runs, child argv, and launch
  manifests report the same effective values.
- `task/health_checks_effective_gold.yaml` is a preserved historical
  materialization, not the authoring authority for a future fresh launch.
- `runtime/wave_records.py` owns the append-only wave evidence and derived
  summary contract. `scripts/record_wave_summary.py` is its campaign CLI;
  neither file is part of generic SIDERIUS execution.
- `stage3/` owns the composed-best, strict-best, and reusable terminal-evaluation
  writers. This campaign reports Composed Best and Strict Best; terminal
  evaluation is explicitly out of scope because its current champion contract
  records one provenance workspace while a Strict Best design is assembled
  from four. No caller may collapse those four roots into a fabricated single
  provenance claim. Composed Best selects the Stage-1 winner in each band, verifies its
  checkpoint digest, reuses the task-owned inference executor over all 200
  segments per file, validates the complete deliverables, and then calls the
  canonical pooled scorer once. Stage-1's 10% deliverables remain search
  evidence and are not final-score inputs. The Gold launcher supplies one
  required explicit data root to inference and scoring; no framework-owned
  TIDMAD data default is used.
- `tasks/tidmad/reference_data/` owns byte-identical copies of the 54 frozen
  anchor, baseline, ground-truth, paper-result, and frequency artifacts.

The Stage-1 launcher now requires an explicit SIDERIUS checkout and resolves
campaign-owned task and Health files from this package. Its separated dry-run
is qualified in `provenance/validation/2026-08-30_tidmad_gold_external_dry_run.md`.
This does not qualify an H100 launch: deployment preflight, runtime-profile
binding, dataset availability, and the final release revision remain pending.

## Local launch-readiness qualification

The reachability witness deliberately fails when `SIDERIUS_CHECKOUT` is not
set. Use an absolute checkout path, verify that it is the revision pinned by
this experiment repository, prepare both frozen environments, and run the
consumer tests with this repository's own virtual environment:

```bash
export SIDERIUS_CHECKOUT=/absolute/path/to/SIDERIUS
test "$(git -C "$SIDERIUS_CHECKOUT" rev-parse HEAD)" = \
  "$(tr -d '[:space:]' < SIDERIUS_REVISION)"
(cd "$SIDERIUS_CHECKOUT" && uv sync --group dev --frozen)
uv sync --group dev --frozen
env -u PYTHONPATH .venv/bin/python -m pytest -q \
  tests/campaigns/test_capability_policy.py \
  tests/campaigns/test_tidmad_gold_nebius_preflight.py \
  tests/campaigns/tidmad_gold/stage3/test_terminal_eval.py \
  tests/campaigns/tidmad_gold/stage3/test_stage3_integration_witness.py
```

The tests import the pinned dependency installed in the exp `.venv`; Gold
framework children use `$SIDERIUS_CHECKOUT/.venv/bin/python`. Preflight R2
checks both repository revisions and R2b copies the framework's real probe to a
neutral working directory, then verifies the selected framework interpreter
without `PYTHONPATH`. Do not substitute another checkout's virtual environment.
An explicit conflicting `SIDERIUS_PYTHON` is rejected before campaign rows run;
an already activated exp `VIRTUAL_ENV` is ignored when choosing framework
Python.

The pinned revision still keeps its chain scripts in
`sdsc_submission_scripts/` and its current configuration in `configs/` and
`llm_configs/`. Their relocation belongs to later 03C work. These instructions
do not authorize Gold, Stage 2, an LLM smoke, or any scientific workload.

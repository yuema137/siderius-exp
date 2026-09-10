# TIDMAD X9 Campaign

This package owns the two-arm TIDMAD X9 experiment, its four-band H100
topology, preflight, resource posture, and campaign-specific validation.
Every launcher requires `SIDERIUS_CHECKOUT` and delegates execution to that
exact framework checkout.

## H100 posture

The posture runs four co-resident band chains per card. One card runs the
`with-prior-art` arm and one runs the `without-prior-art` arm. The values below
are machine-checked against `scripts/h100_posture.env`.

<!-- h100-posture-table:begin -->
| surface | H100 value | class | reason |
|---|---|---|---|
| `H100_POSTURE_VERSION` | `3` | policy | Version of the complete resource posture. |
| `H100_MAX_ACTIVE_PER_CARD` | `4` | policy | Four band chains share each H100. |
| `SIDERIUS_PAIR_VRAM_CEILING_GIB` | `72` | hardware-derived | Four 18-GiB chain slices under the card envelope. |
| `SIDERIUS_PREFLIGHT_WORKER_MEM_GIB` | `24` | policy | Host-memory ceiling for one preflight worker. |
| `SIDERIUS_SUBPROCESS_RSS_GB` | `unset` | deployment-owned | No campaign-wide subprocess RSS override. |
| `SIDERIUS_GPU_VRAM_QUOTA_MIB` | `unset` | deployment-owned | A fleet-wide user quota must be measured and declared separately. |
| `SIDERIUS_GPU_VRAM_QUOTA_GB` | `18` | policy | Per-chain capacity-attribution slice. |
| `--trial_vram_budget_gb` | `18` | hardware-derived | Trial attempt ceiling for one chain. |
| `--formal_vram_budget_gb` | `18` | hardware-derived | Formal attempt ceiling for one chain. |
| `--gpu_pair_ceiling_gib` | `72` | hardware-derived | Aggregate admission ceiling recorded on the run input. |
| `--gpu_admission_enforcement` | `enforce_resource_limits` | policy | Resource refusal remains blocking. |
| `--execution_regime` | `four_way_coresident` | policy | Runtime-profile topology key. |
| `--runtime_safety_factor` | `1.5` | policy | Base admission multiplier. |
| `--runtime_trial_safety_factor` | `3.0` | policy | Trial admission multiplier. |
| `--runtime_formal_safety_factor` | `2.25` | policy | Formal admission multiplier. |
<!-- h100-posture-table:end -->

No H100 watchdog values are borrowed from another device. Until this exact
device and execution regime have a measured runtime profile, the outer Trial
and Formal time budgets are the runaway bound.

## Validation

Run the campaign-owned checks against an explicit framework checkout:

```bash
uv sync --group dev --frozen
export SIDERIUS_CHECKOUT=/absolute/path/to/pinned/SIDERIUS
test "$(git -C "$SIDERIUS_CHECKOUT" rev-parse HEAD)" = "$(tr -d '\n' < SIDERIUS_REVISION)"
(cd "$SIDERIUS_CHECKOUT" && uv sync --group dev --frozen)
env -u PYTHONPATH .venv/bin/python -m pytest tests/campaigns/tidmad_x9
```

Run this from the exp root. The real prompt-capture child uses the framework
checkout's own interpreter and template resources; the installed exp dependency
alone is not a substitute for those checkout assets.

R7 captures the task declared in each arm's real resolved-launch output, using
`--resolved-launch`. A manual `campaign_arm_surface.py` call must instead supply
an absolute `--task-composition` manifest (the two inputs are mutually exclusive).
Missing, empty or relative task declarations refuse before a surface is written.
Capture reads task declarations and plugin visibility, not scientific datasets;
it does not start a run or require a fabricated data directory. Arm isolation,
comparison rules and scientific treatment are unchanged.

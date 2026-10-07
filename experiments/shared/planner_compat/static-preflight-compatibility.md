# Static-preflight historical presentation contract

## Scope and ownership

Issue #615 PR A adds structured static admission evidence in infra. It preserves
the completed estimator decisions and existing successful diagnostic numbers.
Infra owns the schema and truthful default feedback. Exp owns the optional
historical rendering of the additive successful evidence. No historical
scientific manifest, installation default, archived record, or published infra
revision is changed by the v6 planner providers.

`static_preflight_v6.py` composes the corresponding early/late runtime-v5
provider. Its identity hashes its own source and the complete v5 identity.
Selection is explicit through `tune.planner_strategy`; a new workspace is
required because the selected identity changes. V5's runtime feedback and
earlier ordering/attempt-role/manual transformations remain in force.

## Input contract and failure behavior

The input is the raw recorder history consumed by the planner. Each record is
copied recursively before projection. The following conditions apply to its
`memory` mapping:

- If neither `static_preflight_evidence` nor `preflight_outcome` exists, retain
  the record unchanged for the v5 renderer.
- If either exists, both must exist. Validate the evidence with infra's
  `StaticPreflightEvidence` schema, including its supported version, phase
  fields, estimator pairing, and computed binding caps.
- Projection requires `preflight_outcome="COMPLETED_MEASUREMENT"`, no binding
  caps, and a supplied VRAM estimate for each phase. The outcome spelling is
  the existing worker protocol identifier; it does not mean the new static
  estimate is a measured CUDA peak.
- Remove exactly the two additive fields from the rendering copy. Preserve
  status, conclusions, estimates, budgets, and all unrelated fields. Passing
  preflight does not require successful subsequent training or Health checks.
- Missing fields, unknown versions, contradictory evidence, and new static
  refusals raise before provider invocation. Do not synthesize historical
  explanations for these unqualified cases. Stored records are never changed.

The candidate's default refusal text remains truthful. This provider does not
restore incorrect execution decisions, alter batch search, or implement a
measurement fallback. Those estimator changes remain separate issue #615 work.

## Offline verification

`tests/test_static_preflight_v6.py` captures the actual final `LLMBridge.plan`
messages for both early and late providers. For successful preflight followed
by success, failed Health checks, or a training error, it compares v6 plus the
new fields against v5 without those fields. It also proves the unprojected v5
messages differ, verifies the supplied record remains unchanged, and rejects
invalid producers before any captured provider request. These are synthetic
boundary cases, not historical GPU measurements. Two additional cases pass
the current evidence through infra's record-field transport and combine it
with the archived runtime-refusal fixture, verifying that v6 composes with
v5 when preflight passes but a later time check refuses the attempt.

Run the tests using the selected candidate checkout's own environment with
this package installed normally:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/tests" -q
```

The published exp infra pin predates the evidence schema, so v6 tests skip
under that old pin. Candidate qualification must report actual execution of
the v6 tests, not count that skip as a pass. No API call or training is needed.

## Existing archive audit

[The machine-readable inventory](evidence/static-preflight-archive-audit.json)
records source paths and SHA-256 hashes. Its eleven roots cover TESS NoPrior
unit 004, LIGO run 2, Project8 dual-input NoPrior run 5, and all four TIDMAD
band groups (0–3, 4–9, 10–14, 15–19) for both workflow-v5 NoPrior and
workflow-da-only analysis-on. The roots cover every `native_workflow_units`
entry in [the paper source mapping](paper-source-inventory.json); the audit
also records that mapping's hash and each run's source revision. On 2026-10-07,
the listed source hashes, deduplicated record counts, statuses, worker outcomes,
and physical-rejection counts were checked against the local archives.
The installed v6 record projection also returned all 331 deduplicated archive
records unchanged without mutating the supplied inputs. This verifies the v6
layer itself; it is not a capture of 331 complete historical LLM requests.

| Archive | Run-output files | Unique records | Worker results |
| --- | ---: | ---: | ---: |
| TESS | 16 | 62 | 65 |
| LIGO | 17 | 34 | 36 |
| Project8 | 12 | 25 | 26 |
| TIDMAD 0–3 | 9 | 41 | 28 |
| TIDMAD 4–9 | 8 | 24 | 27 |
| TIDMAD 10–14 | 8 | 24 | 26 |
| TIDMAD 15–19 | 7 | 25 | 24 |
| TIDMAD analysis-on 0–3 | 8 | 24 | 27 |
| TIDMAD analysis-on 4–9 | 8 | 24 | 24 |
| TIDMAD analysis-on 10–14 | 8 | 24 | 25 |
| TIDMAD analysis-on 15–19 | 8 | 24 | 25 |
| Total | 109 | 331 | 333 |

All 333 present worker results report `COMPLETED_MEASUREMENT`. No listed
record has a static/VRAM skip, and no listed run output contains a physical
rejection. Some accepted attempts later fail Health checks or time admission;
these are distinct from a preflight refusal and remain unchanged in history.

The 96 analysis-on records contain the legacy `vram_estimate_gb` and
`vram_budget_gb` fields and no new static-evidence markers. They therefore pass
through v6 unchanged. The synthetic late-renderer checks separately establish
how accepted new evidence is projected for that provider.

This is an inventory of available files, not proof that every historical
attempt has a surviving worker receipt. It does not cover external CLI or
orchestration baselines separately listed in `tidmad_paper_scopes`, all
alternative seeds/treatments, missing attempts, or reconstructed decision
traces. A missing historical input cannot be inferred
from zero refusals in the files that remain. Existing frozen prompt tests and
this dynamic boundary test provide separate, explicitly scoped evidence;
neither establishes deterministic future model outputs or training artifacts.

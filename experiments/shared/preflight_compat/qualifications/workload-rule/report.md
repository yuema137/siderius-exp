# Explicit historical workload-rule qualification

## Source pair and scope

Framework: `6675f8ec1ce5952a0b8732f382e847185759f3ae` (infra #689).
Exp base: `1d02ca93fc5c34a84590051873deb728ea55e41b`.
Package: `siderius-preflight-compat` 0.2.3; planner 0.10.0, prompt 0.10.1
and runtime 0.1.0 remain unchanged. Exact closures and installed identity are
in [receipt.json](receipt.json).

The newer framework no longer assigns every task a batch-times-segmentation
limit. This package explicitly declares the historical limit of 800000 through
`BatchSegmentationLimit`. The unchanged root framework pin predates this field
and retains its existing internal threshold. Both APIs remain source-qualified;
there is no exception fallback or permission to load unknown framework code.

The estimator closure contains 78 files. Six changed from the previous source
pair: the estimator registry and the evaluate-VRAM skill's `compute_intensity`,
`batch_resolver`, `wrapper`, `evidence` and `killer_report` modules. Generic rule
selection replaces the former universal constant; exp's frozen formulas are
unchanged. All 160 prompt-closure files and 18 runtime-verifier closure files
are byte-identical to the previous pair, so their qualification is not expanded.

## Executed offline checks

All commands used their selected checkout's own environment. No API call, GPU
measurement, dataset loading or training was performed.

- The original 45 phase arithmetic cases and 32 complete batch-search cases
  match without changing fixtures. This includes threshold equality, mixed
  memory/workload rejection and intensity-only refusal.
- Removing the historical rule made the new boundary regression fail and
  changed 16 frozen batch-search outcomes. Restoring the explicit rule passes.
  Changing or omitting it also changes the profile identity.
- The final candidate suite passes 132 tests, with two baseline failures
  explicitly excluded as described below. Coverage includes installed discovery
  with a real small CPU forward, unknown-assembly refusal, parent/child identity,
  early/late v9 full-request parity and all eleven paper-unit cap/profile mappings.
- The unchanged root framework pin passes 80 focused tests; the new-API identity
  and two current-v9 request checks are skipped because those interfaces are absent. This verifies the retained
  old-API factory path and all frozen arithmetic/search cases.
- Four SHA-checked archived startup models (TESS, LIGO, Project8 and TIDMAD
  NoPrior band 0–3) produce complete system/user messages matching the original
  captures under explicit v9 selectors.
- All 47 fresh candidate prompt captures match preserved original full
  system/user files byte for byte. Fixture and capture-tool identities, and both
  preserved message identities, were verified first. Reference execution was
  **not rerun** for this qualification; the original capture bytes were reused.
- Installed preflight sources, selected clean checkout, child identity and
  unknown-assembly rejection pass. Prompt installation/source checks also pass.
- Root `uv sync --group dev --frozen`, focused Ruff and diff whitespace checks pass.
  The lock change is only the local preflight package version.

### Known test boundary

Two existing `test_qualified_historical_identity_keeps_full_request_bytes` cases
feed the current configuration manual to v5/v6, which intentionally reject the
manual changed by infra #684. Both failures also occur with unchanged exp source
and framework `fec37b60`, whose tree is identical to baseline `218483c6`.
Neither those tests, frozen manuals nor old selectors were changed here. The
new early/late v9 request comparisons exercise the qualified current-manual path.
This report does not claim the complete preflight directory is green.

## Rechecking the qualified pair

Set `EXP_CHECKOUT` and `INFRA_CHECKOUT` to the selected clean checkouts. Install
this exp's packages into the framework's own frozen environment following
[the epoch-manual migration](../../../planner_compat/epoch-manual-compatibility.md).
Then run from the exp checkout, creating a fresh directory for verification receipts:

```sh
OUTPUT=$(mktemp -d)
"$INFRA_CHECKOUT/.venv/bin/python" -m pytest -q \
  experiments/shared/preflight_compat/tests \
  experiments/shared/planner_compat/tests/test_epoch_manual_v9.py \
  experiments/shared/planner_compat/tests/test_runtime_verifier_v8.py \
  -k 'not test_qualified_historical_identity_keeps_full_request_bytes'
"$INFRA_CHECKOUT/.venv/bin/python" \
  experiments/shared/preflight_compat/check_installation.py \
  --infra-checkout "$INFRA_CHECKOUT" --output "$OUTPUT/preflight-installation.json"
```

Four startup commands and the 47-boundary capture/compare tools remain as
documented in the epoch-manual migration. Their archived inputs are not bundled
as new fixture copies in this change. An original-reference rerun additionally
requires each reference checkout and its own environment; preserved full captures
can instead be compared explicitly, as done here.

## Migration and limits

Use a new workspace with the explicit historical estimator and existing matching
v9 planner selection. Keep the original packages and framework for old locks.
Package source and policy identity change even though selectors remain stable.
All prior qualifications, scientific declarations, archives and the public
framework dependency pin remain unchanged.

This qualifies static arithmetic/search and the specified prompt comparisons.
New refusal evidence remains outside the guarded historical planner projection;
restoring its workload decision does not qualify arbitrary refusal prompt text.
It does not establish full conversation replay, measured GPU parity or identical
future models, weights, scores or predictions.

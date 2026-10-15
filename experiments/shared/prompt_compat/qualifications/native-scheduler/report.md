# Native scheduler historical qualification

## Qualified pair

Candidate framework: `0d851a5f6d74f937444e601261ce6273aa31e1b2`.
Exp base: `5f5c25b2d5d14241c2cd8b8c918a85ff696c5284`.
Packages: prompt `0.10.9`, planner `0.12.0`, preflight `0.2.6`, runtime `0.1.3`.
Select the [explicit historical overlay](../../scheduler-disabled.md) in a new
workspace. The root infra pin, lock, archived configurations and original
fixtures are unchanged. The [machine-readable receipt](receipt.json) records exact evidence.

## Contract

Ordinary infra retains its scheduler-capable defaults and native documentation.
The historical overlay explicitly locks scheduling off through native exact-null
parameter rules. Proposer presentation hides only that verified compatibility
rule; task and workflow restrictions remain enforced and visible. The standalone
renderer does not itself establish execution admission.

V11 accepts the actual current manual exactly and renders the frozen early/late
paper manual. Enabled scheduler records and recorded learning-rate histories
are refused. The frozen training appendix and rule projection activate only for
the new qualified scheduler assembly. Previously admitted assemblies retain
their prior native appendix dispatch, rather than inheriting this snapshot.

Preflight and runtime closure fingerprints change because their measured and
training source owners change. Neither historical arithmetic nor verifier
algorithms were edited. Their frozen numerical/search/verifier tests pass on
the candidate with explicit historical selection. Native disabled-path parity
and actual training-loop coverage belong to the paired infra tests.

## Evidence and limits

- 41 focused prompt-package and v11 tests passed, with no skips. These include
  five explicit overlays resolving an enabled proposed scheduler to null using
  native baseline resolution, preservation of task/workflow rules, strict
  unknown-manual rejection, and effective/proposed scheduler evidence refusal.
- 143 preflight and runtime tests passed against frozen estimates/search cases,
  verifier traces and installed policy identities.
- Installation validates 18 installed source files, 14 frozen-source entries
  and four unknown-assembly refusals.
- 47 frozen boundary comparisons, 48 proposer sequences (156 complete requests),
  20 complete reflector requests and eight repair-helper user strings all match.
  Supplementary message comparisons are recorded in the receipt. They use
  frozen recovered boundary inputs and synthetic branch requests, not recovered
  complete conversations. Repair comparisons are helper user strings rather
  than actual provider retry loops.

The overlay witness reaches native baseline resolution and the actual prompt
boundary; it does not execute a whole workflow. Manual comparisons call the
actual configuration-schema producer and historical manual renderer; they do
not reconstruct complete old planner conversations. No API, GPU, dataset,
training or inference operation occurred. Identical future LLM replies or
retrained model artifacts are not claimed.

## Reproduction

Use the candidate checkout's own frozen environment and explicitly install the
four standalone packages there. Keep the root exp environment binding unchanged.
Run these focused checks from the exp checkout, with absolute paths in the two
variables:

```bash
SIDERIUS_CHECKOUT="$INFRA_CHECKOUT" "$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  experiments/shared/planner_compat/tests/test_scheduler_manual_v11.py \
  experiments/shared/prompt_compat/tests -q
"$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  experiments/shared/preflight_compat/tests/test_historical_estimation.py \
  experiments/shared/runtime_compat/tests/test_frozen_verifiers.py \
  experiments/shared/runtime_compat/tests/test_installed_profiles.py -q
"$INFRA_CHECKOUT/.venv/bin/python" \
  experiments/shared/prompt_compat/check_installation.py --profile-version 2
```

The existing frozen corpus, proposer, reflector and repair capture commands are
specified in the [previous qualification](../downstream-constraints/report.md).
Use the candidate revision above, fresh output directories and the v2 task
profiles. The original `c7996a352d064229725ab1ebe886b9006bdbf36d` reference remains
in its own unchanged environment. None of these commands trains a model.

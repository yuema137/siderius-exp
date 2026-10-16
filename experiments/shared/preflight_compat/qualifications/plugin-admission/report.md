# Preflight qualification after plugin admission corrections

## Source boundary

This qualification admits exact infra
`e8a1a8f540d65a0df8f7504cbf6e908bb861a025` with standalone preflight package
`0.2.7`. The prior package rejected this assembly and also rejected both the
baseline before the reduction-metadata fix and the baseline after that fix.
This is an inherited admission gap; no intermediate source revision is newly
advertised as qualified.

Five of 80 estimation-closure files differ from the last admitted scheduler
candidate `0d851a5f6d74f937444e601261ce6273aa31e1b2`. The
[source review](source-review.json) records the exact files and identities:
custom-loss target contracts are checked and transported, stale reduction
metadata is cleared after successful replacement, and rejected legacy model/loss
imports restore the prior module binding. The phase arithmetic, batch resolver,
structural probe and observation schema are unchanged.

The retained paper execution audit found built-in `smooth_l1` objectives in
109 records, as documented in the
[loss-target qualification](../../../prompt_compat/qualifications/loss-target-contract/report.md).
This does not justify preserving invalid custom-plugin admission or corrupted
module bindings. Existing frozen arithmetic and historical projection code are
unchanged. The qualification covers `static_only` inference preflight, with
protected GPU execution unselected; it does not qualify arbitrary measured-GPU
policies or complete historical execution replay.

## Checks and test maintenance

Existing frozen fixtures cover 45 phase estimates and 32 batch decisions. A
separate actual CPU forward checks explicit historical batch selection versus
the native result. Installation checks compare installed and checkout source,
parent/child identity, explicit admission and unknown-assembly refusal.
Historical projection tests compare full planner requests and retain original
records unchanged.

Before admission, the package suite had eight failures and 100 passes. After
admission, six disappeared; two exposed an older test mismatch: a test labelled
"current paper profile" selected the obsolete v9 planner and supplied a frozen
pre-scheduler manual from a shared v6 helper. It now selects the documented
scheduler-disabled v11 profile and the actual native configuration manual. Its
full before/after request equality and input-preservation assertions remain.
The existing v11 tests separately compare the projected manual with unchanged
historical fixtures. No expected message, estimate or batch fixture is rewritten.

## Installation and reproduction

Use a new historical workspace with the current v2 scheduler-disabled overlay,
which declares preflight package `0.2.7`. Keep old package versions, records and
workspace locks unchanged. The root exp installation pin and lock are separate
from this explicit standalone qualification and are not upgraded here. Install
all four compatibility packages normally into the exact infra checkout's own
frozen environment; do not borrow another checkout or inject `PYTHONPATH`.

```bash
uv pip install --python "$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/planner_compat" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat" \
  "$EXP_CHECKOUT/experiments/shared/preflight_compat" \
  "$EXP_CHECKOUT/experiments/shared/runtime_compat"
SIDERIUS_CHECKOUT="$INFRA_CHECKOUT" "$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  "$EXP_CHECKOUT/experiments/shared/preflight_compat/tests" \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/tests/test_scheduler_manual_v11.py" -q
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/preflight_compat/check_installation.py" \
  --infra-checkout "$INFRA_CHECKOUT" --output "$NEW_INSTALLATION_RECEIPT"
```

The additional existing planner self-check binds `paper-early-v2`, invokes
`siderius_planner_compat.self_check.check()`, and compares 28 synthetic historical
message pairs plus registry behavior. No API requests, GPU work or scientific
training are performed. These checks do not promise identical future LLM replies
or retrained artifact bytes.

## Results

All 113 focused tests pass without skips, including all 45 frozen phase estimates
and 32 frozen batch decisions. Installed-source, parent/child identity and
unknown-assembly refusal checks pass. The existing planner self-check matches
all 28 message pairs and passes its registry checks. Ruff and diff checks pass.

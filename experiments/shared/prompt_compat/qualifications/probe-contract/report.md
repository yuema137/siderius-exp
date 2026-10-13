# Optional model-probe contract qualification

## Result and scope

Infra `a50c578a9b975f301122e65dfee11101cd83ba72` preserves all 47 frozen
historical rendering requests with the explicitly selected v2 profiles. Eight
supplementary repair requests also match pre-fix infra
`8f43fa1ac92aba6c09c4322480f95270ef1730ef`: one initial repair and one repair with
prior error history for each of TESS, LIGO, Project8 and TIDMAD.

[Receipt](receipt.json) records the compared message identities and revisions.
These checks make no provider, GPU or training calls. They do not reconstruct
missing historical responses, replay complete conversations or establish equal
future scores. Repair code and errors are synthetic; their task inputs come
from the unchanged frozen implementor fixtures.

The package suite passed 21 tests. The installation check verified all packaged
source files and frozen source entries; all four v2 profiles rejected an unknown
assembly. Focused Ruff and whitespace checks passed.

## Compatibility boundary

The four paper task packages declare no task-owned model-validation probe
provider. The new optional contract therefore adds no text or probe overrides
to their execution paths. Native temporal and fixed-geometry probe behavior
remains owned by infra; this qualification does not add historical behavior to
framework defaults or change scientific task declarations.

The rendering assembly includes implementor modules and schemas, so changing
those sources invalidates the historical package's explicit assembly allowlist
even when these messages remain identical. Version 0.10.5 adds only the verified
assembly to the v2 qualification. Frozen renderers, reference fixtures and v1
qualifications remain unchanged. Unsupported assemblies still fail closed.

The qualification changes profile content identity. Install the updated package
in the selected infra environment and use a new workspace; preserve existing
locks, records and environments. This change does not alter the repository-wide
infra dependency pin or authorize an experiment launch.

## Reproduce offline checks

Use the selected checkouts' own frozen environments. Run the existing
[comparison procedure](../../usage.md#3-inspect-the-offline-comparisons) with
`--profile-version 2`, the candidate revision above, and the historical reference
revisions declared in the fixtures. No original datasets are required.

For the supplementary repair differential, run this command separately with
`INFRA_CHECKOUT` and `INFRA_REVISION` set to the pre-fix and candidate checkouts,
and a different fresh `OUTPUT_DIRECTORY` for each:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/qualifications/probe-contract/capture_repair.py" \
  --fixtures "$EXP_CHECKOUT/experiments/shared/prompt_compat/fixtures" \
  --revision "$INFRA_REVISION" \
  --output "$OUTPUT_DIRECTORY"
```

Compare the eight corresponding `.txt` files byte for byte. The script refuses
wrong revisions, dirty source and a borrowed environment, disables network
connections, hides GPU devices and removes provider key variables before imports.

Verify installation and unknown-assembly rejection with:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_installation.py" \
  --profile-version 2
SIDERIUS_CHECKOUT="$INFRA_CHECKOUT" "$INFRA_CHECKOUT/.venv/bin/python" \
  -m pytest "$EXP_CHECKOUT/experiments/shared/prompt_compat/tests" -q
```

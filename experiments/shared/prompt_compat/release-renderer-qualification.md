# Release candidate renderer qualification

## Scope and result

Prompt compatibility 0.7.0 adds one accepted rendering assembly for infra
`34660bed0960f3bcad60ba30aaedffaaf617ff8b` (development PR #635). The existing
47 frozen rendering/producer requests match their historical reference messages.
All four paper proposer configurations also preserve their explicit historical
routes and bridge construction. API calls: 0. Training calls: 0.

The portable [receipt](release-renderer-qualification.json) records each case's
input and message hashes, reference revision, capture-tool hash, package
identities and routing results. This is qualification of those declared
boundaries, not complete conversation replay, scientific scores, new runtime
refusal records or successful tutorial/onboarding execution.

## Why a new qualification was needed

The installed 0.6.0 package refused all 47 candidate captures before rendering:
the current assembly was absent from its qualification inventory. Those were
errors before comparison, not message differences. The candidate 0.7.0 source
package adds the explicit assembly and retains the refusal check; it was then
installed into the candidate infra checkout's own frozen environment for the
offline comparisons. No installed package files or loader guards were patched.

Assembly SHA-256:
`76792a754d20d6ef34be8af993dd40900b2627e9cd145823fa7b01551364947b`.
It is identical at #635's base `8ad2ba0b3b0f3550d40f512a78365e0f00957962`;
the namespace admission repair itself does not modify the rendering assembly.

Compared with the previous qualified infra
`7c869e67f697d6bbc81eb554711ab77e23cb7362`, the covered node sources now obtain
constructor defaults and bridge keyword arguments from shared owners. The
proposer routing module re-exports the shared routing owner. Source audit found
preserved default values and keyword-omission behavior; the four configuration
checks independently cover effective proposer routes and constructed bridge
arguments. The newly extracted settings/routing owners and bridge transport
are outside the renderer digest. The receipt therefore records their actual
source hashes separately, alongside the exact clean infra revision; the routing
checker's original source list still includes the compatibility re-export.
These captures do not exercise provider transport.

Existing qualification entries, frozen renderers, task declarations, paper
configuration files and experiment identities are unchanged. The updated
qualification source changes all four profiles' content identities. New
workspaces must select the new package explicitly; old locks are not rewritten.
Keep the old package and infra revision for an old workspace whose identities
require them, even though the compared message text is unchanged.

## Re-run the checks

Use the candidate infra checkout's own frozen environment and install the
packages with the [installation steps](README.md#1-install-into-the-infra-environment).
Set `EXP_CHECKOUT` to the exp checkout containing this package, and prepare the
historical reference checkouts and references JSON described in the README.
Their Python environments must also belong to their exact checkouts.

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare.py" \
  --candidate "$INFRA_CHECKOUT" \
  --references /your/references.json \
  --output /your/new-comparison-directory

"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_installation.py"

"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_paper_proposer_routing.py" \
  --expected-revision 34660bed0960f3bcad60ba30aaedffaaf617ff8b \
  --exp-checkout "$EXP_CHECKOUT" \
  --output /your/new-routing-receipt.json
```

Observed results: 47 matching message cases; 14 installed source files match
the reviewed package; 11 frozen source inventory entries match; all four
profiles reject an unknown assembly; all four proposer configurations match.
Output directories/files must be new. These checks do not need datasets or
credentials and do not call a provider.

## Release boundaries

This qualification does not promote `SIDERIUS_REVISION`, `pyproject.toml` or
`uv.lock`, publish an unmerged infra revision through yuema137, or update any
historical experiment pin. Final release pairing and fresh-user tutorial checks
remain separate work. The orchestration toolkit instruction changes require
their own historical revision binding; these renderer fixtures do not cover
the toolkit's Markdown payload. Namespace trial/inference measurement and the
four independent onboarding runs remain pending under infra #585/#633.

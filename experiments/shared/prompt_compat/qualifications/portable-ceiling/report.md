# Portable-ceiling renderer qualification

## Result and scope

Prompt compatibility 0.8.0 qualifies the declared rendering assembly at infra
`5afbdcb2ed9eab61c99cb14192b116fe1a479a0f`. All 47 frozen rendering/producer
requests match their historical references, and all four historical paper
proposer configurations preserve their routes and constructed bridge arguments.
Provider calls: 0. Training calls: 0.

The [receipt](receipt.json) records the input, capture-tool and message hashes,
reference revisions, installed package file hashes, four profile identities and
routing results. The [source review](source-review.json) records the complete
157-file rendering closure at both the previous qualified revision and candidate.
The reviewed exp source commit used for installation and capture is
`b72890a13f5db66abf85dac3b530bb3f224b1a8c`; the final documentation/receipt commit
does not change the installed package sources or frozen requests.

These checks cover the declared request boundaries. They do not recover missing
intermediate replies, replay a complete conversation, reproduce scientific
scores, or qualify GPU/host resource enforcement and tutorial launch readiness.
The [0.7.0 report](../../release-renderer-qualification.md) remains unchanged as
historical evidence.

## Source change and qualification decision

The installed 0.7.0 package initially refused all 47 candidate requests before
rendering. They were errors from an unknown assembly, not message differences.
The refusal guard was retained. After source review, 0.8.0 appended only this
exact assembly and was installed normally, without dependency changes or edits
to installed files, into the candidate checkout's own environment. Actual
comparisons and negative installation checks then passed.

Assembly SHA256:
`fc99e9531aa06be76f383cc3cc0aee2480e5ba485836060d393571494e60987d`.

Compared with qualified `34660bed0960f3bcad60ba30aaedffaaf617ff8b`, only
`agent/schemas/hyperparam_tuning.py` differs among the 157 covered sources. It
imports and uses `PositiveGpuGiB` for the optional aggregate GPU ceiling and
updates its help text to describe configured limits, measured capacity and quota.
No renderer function changed. The stricter declaration and changed runtime
resource policy remain real behavior changes; frozen message equality does not
claim those policies behave like historical training runs.

The review separately records actual hashes for the shared node/settings/bridge
owners, `pair_admission.py` and `hardware_context.py`. These files are outside
the rendering closure. Their hashes identify inspected source, not additional
behavior exercised by the message captures. In particular, the hardware owner
hash does not qualify a real CUDA or ROCm device.

## Executed checks

- 47 message cases: 11 each for TESS, LIGO, Project8 and TIDMAD, plus three
  analysis-on requests. Every candidate and reference used its own checkout
  interpreter and the fixture's exact reference revision.
- Four paper proposer configurations: effective comparison/reasoning/proposing
  routes and bridge constructor arguments match their historical declarations.
- Installation: all 14 package source/data files match the reviewed source;
  all 11 frozen source-inventory entries match their recorded origins.
- All four profiles reject an unknown assembly. The guard was not bypassed.

Re-run through the existing [installation and selection procedure](../../usage.md).
The reference mapping comes from each frozen fixture's recorded provenance.
Set both checkout variables to your own paths and choose new output locations:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare.py" \
  --candidate "$INFRA_CHECKOUT" --references /your/references.json \
  --output /your/new-comparison-directory

"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_installation.py"

"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_paper_proposer_routing.py" \
  --expected-revision 5afbdcb2ed9eab61c99cb14192b116fe1a479a0f \
  --exp-checkout "$EXP_CHECKOUT" --output /your/new-routing-receipt.json
```

## Identity and release limits

The appended qualification data changes all four profile content identities.
Use a new workspace with this package; preserve old package/revision pairs for
old workspace locks. Existing qualification entries, frozen renderers/templates,
fixtures, paper settings and historical receipts are unchanged.

This qualification does not promote the root framework pin, dependency lock or
any historical experiment revision. It does not publish the candidate through
the public mirror. A later changed rendering closure requires another source
review and qualification. Final paired release, runtime protection, installation
profiles and real onboarding remain separate checks.

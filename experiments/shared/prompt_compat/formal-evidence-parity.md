# Formal-evidence recovery qualification

## Scope and revisions

Infra #445 requires independent formal-round evidence before a cached score
can enter a scientific aggregate. An old positive authority verdict alone is
insufficient. This companion provides explicit, consumer-owned input recovery;
it does not weaken infra's default or mutate historical workspaces.

The qualified candidate is `dfcb39045567076b752c4d30ac2b3a7a3bd6717c`.
The pre-change cache reference is
`7c3b4031a6930f5fe753a88dfccc07e6abc1b727`. The separate frozen prompt comparison
uses each fixture's historical revision, recorded in its receipt. Prompt
compatibility package 0.3.0 recognizes the candidate rendering assembly.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Existing frozen rendering cases, including four paper tasks and analysis branches | 47 MATCH | [Prompt receipts](evidence/formal-evidence-prompt-comparison.json) |
| Recovered score-bearing interpretation caches | 49 MATCH | [Cache receipts](evidence/formal-evidence-cache-comparison.json) |
| Recovery refusal and successful-copy tests, plus empty comparison refusal | 10 passed | `tests/test_recover_formal_evidence.py` and existing comparison tests |

The archive audit found 53 interpretation artifacts: TESS 16, LIGO 17,
Project8 12, and TIDMAD band 0–3 8. Four TIDMAD artifacts contain no formal
score and need no recovery. The remaining 49 cases include three single-model
inputs for which the production agent makes no synthesis request. Thus 46
cases compare actual synthesis message pairs; three compare the absence of
that request. Every case checks scientific-aggregate membership against the
archived result. All selected producing outputs and effective policies were
available and unambiguous.

The recovered inputs retain archived descriptions, numerical scores and
authority declarations. Only `formal_evidence` and its matching `run_name` are
added to each relevant cache entry. Recovery verifies source file hashes,
effective policy body identity, metric consistency, the selected formal round,
and cached authority. Contradictory or incomplete evidence fails explicitly.
Health requirements come from the archived effective policy; an empty required
gate roster is distinct from an unknown roster.

## Reproduce the offline check

First follow the package [installation and recovery instructions](README.md).
Prepare one recovery-request JSON per interpretation cache in an external
directory. The cache receipt's `recovery.request` records the input hashes and
the operator archive paths used for this qualification. On another machine,
select local copies with the same hashes and update the request paths. These
paths are provenance, not executable defaults or a download requirement.

Prepare the clean candidate and reference checkouts with their own frozen
environments. Then run from the exp checkout:

```bash
"$EXP_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare_formal_recovery.py" \
  --candidate "$INFRA_CHECKOUT" \
  --reference "$REFERENCE_CHECKOUT" \
  --requests /your/recovery-requests \
  --output /your/new-cache-comparison
```

The tool refuses an empty request directory or an existing output directory.
Each recovery and capture subprocess runs the selected infra checkout's own
Python, checks its revision and source cleanliness, and writes separate files.
`comparison.json` records outcomes, source provenance, message hashes and helper
digests. A differing message, invalid source, or incorrect membership makes the
command fail. Use the README's `compare.py` command for the 47 frozen cases.

## Interpretation and limits

These are offline input and prompt comparisons: API calls 0, training calls 0.
The cache check reconstructs a cache-only `InterpretationInput` from saved
knowledge, an agreed neutral task description and the reconciled metric. It
normalizes only the temporary output workspace path in captured messages.
It is not a recovered complete historical request envelope or conversation.
The frozen cases retain their individual provenance and reconstruction limits.

The 49-cache audit covers the named paper archives, including TIDMAD band 0–3;
it does not claim an exhaustive audit of every campaign or every band. Fresh
typed summaries and cache writes are tested in infra; the new evidence changes
serialized input identities even when rendered historical text is unchanged.
Use an explicit new workspace. Neither this tool nor the qualification permits
in-place continuation of an old lock, proves equal stochastic LLM responses,
or reproduces deleted predictions and model scores.

The repository's published infra pin remains unchanged until the coordinated
release qualification. This package addition is not a release or installation
pin update.

# Paper proposer routing audit

## Contract and historical behavior

The proposer routing repair makes `propose.comparison`, `propose.reasoning` and
`propose.proposing` select their own provider, model, reasoning effort and retry
limit. Previously `WorkflowLLMConfig.get("propose")` supplied top-level values
from `propose.reasoning`; `MLModelProposalAgent` constructed one bridge with
those values and ignored the additional per-stage kwargs. Source inspection
confirmed this behavior at all four historical infra revisions below.

The four qualified paper configurations already explicitly select the same
provider, model and effort for all three stages: `openai`, `gpt-5.6-sol`,
`medium`. No stage declares `max_retries`; the typed value and historical bridge
argument are `None`. Historical `LLMBridge` source documents this as indefinite
retry, distinct from a finite limit. These are request settings, not evidence
that retries actually occurred or that a provider will reproduce old responses.

**No routing overlay or rewritten archive is needed for these four cases.**
Their existing experiment files already express the historical selection at
each stage. The checker below stores an audit expectation, not a second launch
configuration. Other experiments with unequal stage settings change behavior
under the repair and require their own explicit treatment decision.

## Source and execution evidence

Paths in the following inventory are historical provenance only. The checker
does not open these archive locations or require the original machine.

| Case | Experiment config relative to exp root | Historical infra revision | Historical exp revision |
| --- | --- | --- | --- |
| TESS | `experiments/phyts_tess/main_fixed_workflow/agents.json` | `7689fd58b91d410788e953b51ea69a9dbc528a7d` | Not recorded by the inspected launch artifact |
| LIGO | `experiments/phyts_ligo/main_fixed_workflow/agents.json` | `0ab1573602c708ddd182432ad4d0e43ae4828c53` | `8513deabe042acfbb7743b5981bb790726ae0e82` |
| Project8 dual representation | `experiments/phyts_project8/main_fixed_workflow_dual_representation/agents.json` | `349b6cd6d9766abbf3d87515b22e1005599a694b` | `641de54b721f5c7e123c1ff4e5615d2bae39f644` |
| TIDMAD NoPrior, band 0–3 | `experiments/tidmad/main_fixed_workflow/iclr_official_v1.json` | `345c802d82c71f72e1b73a90d2bf702d09d1865d` | `902711cbd10b35aa8d86e3234e2d3b64847ea1af` |

The audit read each archived `launch.json` and, where an exp revision was
available, its exact Git config blob. LIGO and Project8 configs have SHA-256
`376424b5ba31e08e1117cfcb5da2c786f7b50009c64a474a613d6456c9b2bb88`.
TIDMAD's config has SHA-256
`b37bbf6b51a0b3c40c7f58972f68858f3d4fc46309960a6708639215cf933e4f`,
which also equals the digest recorded by its launch artifact. The preserved
TESS launch-selected config at
`/home/yuema137/siderius-exp-run/experiments/phyts_tess/main_fixed_workflow/agents.json`
has that same latter digest. Its current checkout HEAD is not evidence of the
original exp revision; the TESS revision remains unknown in this audit.

Actual archived chain logs independently record the same three stage settings.
All parsable `LLM config` entries in these files agree:

| Case | Log path | First configuration line | Configuration entries |
| --- | --- | --- | --- |
| TESS | `/home/klz/Data/SIDEREIS_DATA/phyts_tess/units/nop_004/logs/chain.log` | 72 | 17 |
| LIGO | `/home/klz/Data/SIDERIUS-ICLR/runs/ligo-run2-completed-20260922/unit/chain.log` | 75 | 18 |
| Project8 | `/home/klz/Data/SIDERIUS-ICLR/runs/project8-dual-no-prior-run5-20260923/unit/chain.log` | 74 | 13 |
| TIDMAD | `/home/klz/Data/SIDERIUS-ICLR/runs/workflow-v5-20260919/band-0-3/unit/logs/chain.log` | 72 | 10 |

TESS's launch artifact is beside its `logs/` directory. For the other three
cases, `launch.json` is in the indicated `unit/` directory. Logs establish the
configuration supplied to the historical workflow; combined with the pinned
historical node source, they establish its routing behavior. They are not
complete provider request/response transcripts. The TIDMAD log audit covers
band 0–3 only, not every band or later analysis-on campaign.

## Portable offline check

Prepare the candidate infra checkout with its own frozen environment. Set
`INFRA_CHECKOUT` and `EXP_CHECKOUT` to the respective checkout paths, then run:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_paper_proposer_routing.py" \
  --expected-revision "$(git -C "$INFRA_CHECKOUT" rev-parse HEAD)" \
  --output /your/new-routing-receipt.json
```

The parent output directory must exist; the receipt filename must be new.
Omit `--output` to print JSON only. `--exp-checkout /your/exp-copy` optionally
selects a different source copy; by default the checker uses its own exp tree.

For each config the checker calls the real `WorkflowLLMConfig.get("propose")`,
constructs `MLModelProposalAgent` with a recording bridge factory, and examines
the public immutable `routing` value and `routing.for_stage()` interface. It
checks all four fields, including `max_retries: null`, against the historical
reasoning selection. It also verifies the actual constructor received exactly
one matching bridge configuration. The capability index uses a temporary
directory. No provider client is constructed, and generation methods refuse.

Success prints four `MATCH` rows. A mismatch exits nonzero. The receipt includes
config and checker digests, the selected infra revision, routing source digests,
and a dirty-source flag. A dirty checkout can be checked during development;
its result is explicitly source-qualified and must not be represented as a
clean-commit qualification. Run again on the final committed candidate for
release evidence. Existing experiment configs and historical artifacts are
never modified.

## Final candidate evidence

Clean infra candidate `44e822027101785ab4e41e5335f1df8a8adb10ed` has rendering
assembly `29f65b70718cbd5ad358c2ad49ea8e15835fde331e751d41d6a34af1e93e9838`.
The experiment-owned prompt compatibility package version 0.4.0 declares this
assembly after the following offline checks:

- [Four configuration checks](evidence/proposer-routing-config-comparison.json):
  all `MATCH`, `infra_source_dirty: false`, exact source and input digests.
- [47 frozen prompt comparisons](evidence/proposer-routing-prompt-comparison.json):
  all `MATCH`, including the 24 proposer stage/mode cases. System and user
  message digests are equal to the matching historical renderer outputs.
- [Installed package check](evidence/proposer-routing-installation.json):
  14 installed source files equal reviewed package files; all 11 historical
  source inventory entries verify; all four profiles reject an unknown assembly.
- Infra's proposer/config suite: 812 passed. Public node, context and README
  boundary checks: 46 passed. The final mapping type annotation correction
  passed the 14 routing tests again. Changed production files pass basic Pyright
  with zero errors and five existing workflow warnings; Ruff passes.

Independent review checked an unrelated temporary config copy and rejected all
12 stage/field mutations (provider, model, reasoning effort and retry limit). No archived path
is required by the portable checker. This evidence used no API or GPU calls.
The root exp dependency pin and lock are unchanged; selecting this qualified
candidate remains an explicit installation step until release integration.

## Qualification boundary

This checker covers node construction and its public routing interface. It does
not execute proposal stages, structural repairs, retries, fallback calls, or a
workflow. Infra's synthetic pipeline tests must independently verify actual
call dispatch, distinct routes, legacy fallback and repair/retry ownership.
No infra test fixtures are imported by this checker.

Changing proposer node Python changes `rendering_assembly_digest()`, even when
rendered text is unchanged: its inventory includes every Python module in
`nodes/ml_model_proposal_agent`. The exp prompt compatibility package therefore
needs explicit qualification of the final candidate assembly. The bounded
prompt check is the existing 47 frozen comparisons, including 24 proposer
cases (four tasks × three stages × explore/exploit). Route equality and prompt
equality do not establish stochastic response equality, full conversation
replay, scientific-score reproduction, or permission to resume an old lock.
Use a new workspace for the changed framework/package identity.

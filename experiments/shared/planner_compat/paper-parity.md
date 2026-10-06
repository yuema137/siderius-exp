# Offline paper planner strategy verification

## Result and boundary

The #372 historical provider preserves final system/user text for the checked
shared-logic inputs. Twelve LIGO-derived branch cases match with the historical
configuration manual, and the same twelve match with the pre-PR manual. An
independent reviewer recaptured both sets and confirmed that an altered expected
digest fails. No LLM request, scoring, training or dataset download was involved.

The production LIGO startup path was also exercised in fresh, separate temporary
workspaces, stopping at the first planner call. Pre-PR and new-provider captures
produce identical final system and user text. This is an offline startup using
the archived first model and pinned task package, not a claim to have recovered
the original run's complete transient state, advice or API request.

Normal historical and current startup are **not** identical: the current user
prompt's configuration manual includes three properties added before #372:

| Property | Introducing infra commit |
| --- | --- |
| `checkpoint_selection` | `b1e472a5` |
| `target_standardization` | `95c5ad21` |
| `drop_last` | `441061cd` |

The system prompt matches. The historical-manual comparison freezes the old
manual explicitly; it does not hide, repair or automatically remove these
current properties. The operator accepted keeping this pre-existing difference
outside #372 on 2026-10-05. No historical startup adapter is required by this PR;
the scoped strategy-migration verification is complete. This acceptance does not
claim full historical startup equivalence or authorize merging the paired PRs.

## References and method

- Historical infra: `0ab1573602c708ddd182432ad4d0e43ae4828c53`.
- Historical exp task: `8513deabe042acfbb7743b5981bb790726ae0e82`.
- Pre-PR oracle: `a2eb55dfb2853870a8294eb675a8060043d9c68b`, whose entire Git
  tree is identical to PR base `29ab64db567aa15e7e247c2dd21be1fc7df23f12`
  (`ff6dfbe2d8f66187ca86ac0045921905daf58782`).
- New infra: `0f7738bbe6b3217b368c5f3a948a2256a34b9d0f`.
- Selected provider: `legacy-9b78d505cb11-v1`.

Each infra checkout uses its own frozen environment. The startup captures use
the archived `dual_domain_chirp_fuser` plugin, LIGO launch parameters and pinned
task composition. They terminate before any execution attempt. Final prompt
capture runs the real `LLMBridge.plan`; only its provider-boundary method is
replaced by a recorder. Client access and socket connections raise errors.

The portable fixture contains the captured arguments, both manuals, the original
Formal appendix and validation disclosure, and expected final-message hashes.
Later-round cases use a named field projection of the first archived LIGO Trial
record. Other task names label branch projections with LIGO task text and model
inputs; they are not reconstructed historical calls for those tasks. The
scoreability object preserves its serialized identity and refuses execution.

The runner requires the original model plugin as an explicit, SHA-256-checked
input. It isolates plugin/workspace directories, validates the checkout-owned
environment, pins reference revisions, requires expected hashes and refuses to
overwrite result files. It neither imports another checkout's source nor trains
the loaded model. Raw archive transcripts and credentials are not fixtures.

## Additional branch coverage

[paper-branch-audit.json](paper-branch-audit.json) records launch digests,
explicit flags, archived output contracts and common source hashes for all
eleven native paper units. All five original infra revisions share the same
planner template, bridge and conditional loss renderer. They map to the same
historical provider; the early `691617f04b42` provider is not used here.

| Native lineage | Formal training owner | Epoch-validation override | Rounds | Plan override | Output |
| --- | --- | --- | ---: | --- | --- |
| LIGO | Agent | 0.1 | 2 | `is_trial=true` | Continuous scalar |
| TESS | Operator | Absent | 2 | `is_trial=true` | Continuous scalar |
| Project 8 dual | Operator | 0.1 | 2 | `is_trial=true` | Continuous scalar |
| TIDMAD NoPrior, four bands | Operator | Absent | 3 | Absent | Continuous temporal |
| TIDMAD Data Analysis, four bands | Operator | 0.1 | 3 | Absent | Continuous temporal |

Each row contributes one case per round: twelve cases. They cover the relocated
agent-owned Formal appendix, its absence, present/absent validation disclosure,
the historical stage schedule at two/three rounds, locked/unlocked mode hints,
and scalar/temporal continuous-loss advice. The original stage strategy remains
in the historical provider; these tests do not introduce it into native timing
guidance. The previous 28 installed checks separately cover additional registry,
loss, resource and override shapes; counts should not be treated as exhaustive
coverage of all runtime histories.

The older TESS and TIDMAD NoPrior planning source predates the validation
disclosure. Their launches do not set the override; the later helper returns an
empty string for that case. Other old/new planning differences in scope counts
and post-plan Formal recovery do not create a new #372 prompt-rendering branch.
Task-specific text remains caller-supplied and its substitution is unchanged.
CLI and external-orchestrator prompts have separate owners and are not silently
rebound to this native provider.

## Repeating the check

From each exact infra checkout, first run `uv sync --group dev --frozen`.
Install the compatibility package normally into the new infra environment as
described in its installation instructions. Set `EXP_CHECKOUT` to this exp
checkout and `MODEL_PLUGIN` to the archived LIGO model file. Its required digest
is recorded in the fixture; no machine path is an executable default.

Run in the historical infra checkout:

```bash
.venv/bin/python "$EXP_CHECKOUT/experiments/shared/planner_compat/paper_check.py" \
  --model-plugin "$MODEL_PLUGIN" --reference --manual historical \
  --output /tmp/paper-historical-reference.json
```

Run in the pre-PR oracle checkout:

```bash
.venv/bin/python "$EXP_CHECKOUT/experiments/shared/planner_compat/paper_check.py" \
  --model-plugin "$MODEL_PLUGIN" --reference --manual pre_pr \
  --output /tmp/paper-pre-pr-reference.json
```

Run in the new infra checkout, once for each manual:

```bash
.venv/bin/python "$EXP_CHECKOUT/experiments/shared/planner_compat/paper_check.py" \
  --model-plugin "$MODEL_PLUGIN" --manual historical \
  --output /tmp/paper-historical-plugin.json
.venv/bin/python "$EXP_CHECKOUT/experiments/shared/planner_compat/paper_check.py" \
  --model-plugin "$MODEL_PLUGIN" --manual pre_pr \
  --output /tmp/paper-pre-pr-plugin.json
```

Use new output paths if those files exist. Every successful command checks all
twelve expected system/user hashes. [paper-parity-results.json](paper-parity-results.json)
records reference identities, provider identity, fixture digest and startup
comparison digests. Deleted prediction recovery and stochastic result replay
are outside this acceptance, as explicitly directed by the operator.

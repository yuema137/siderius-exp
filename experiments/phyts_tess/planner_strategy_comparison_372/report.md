# Issue #372 controlled TESS planner comparison

Status: planner-call and preflight-input evidence only, recorded 2026-10-04.
This is an internal validation experiment, not a paper artifact reproduction.
The paired development changes are infra PR #593 and exp PR #144.

## Question and treatment

Does composing execution-owned parameter facts into the planner change its
proposals or its explanation of parameter ownership? Compare the original
planner with explicitly selected `native-timing-v1`; the compatibility default
is covered separately by the installed package's offline prompt comparisons.

Exact infra revisions:

- Original: `a2eb55dfb2853870a8294eb675a8060043d9c68b`.
- Native: `0f7738bbe6b3217b368c5f3a948a2256a34b9d0f`.

Each arm used its own frozen virtualenv and production tuner input capture.
The accompanying exp source was `8789ec8`. Both arms used OpenAI
`gpt-5.6-sol`, medium reasoning, standard service tier. The frozen matrix used
three independent calls per arm and condition, alternating arm order: 18 calls
in total. The order and per-call identities are retained in `results.json`.
There were no hidden SDK retries and no content retries in this matrix.

The three conditions were:

| Condition | Trial final evaluation | Epoch-loss validation | Trial epoch cap |
| --- | --- | --- | --- |
| Fixed | Operator override `eval_portion=0.23` | Existing aligned behavior | 3 |
| Free | Planner-controlled evaluation fraction | Existing aligned behavior | 3 |
| Independent | Operator override `eval_portion=0.23` | Operator-declared independent snapshot fraction `0.11` | 3 |

All conditions also exposed Formal training portion `0.4`, Formal evaluation
portion `0.29`, Formal epoch cap 5, Trial/Formal time budgets 1/2 minutes, and
VRAM budgets 8/8 GiB. These are this experiment's declarations, not infra
scientific defaults. This first-round comparison did not execute a Formal round.

The same existing seven-row TESS tuning summary was supplied as prior evidence
in each fresh first-round planner call. It includes five resource-risk skips
and two successful records. This transplanted history is a controlled input:
it is not a resumed run, an archived-response replay, or a freshly measured
hardware history. No held-out test data was accessed or new data downloaded.
The original task, data and workspaces were not modified.

## Observed results

| Observation | Original | Native |
| --- | ---: | ---: |
| Returned responses passing plan schema validation | 9/9 | 9/9 |
| Proposed epochs at or below the cap | 9/9 | 9/9 |
| Preserved `eval_portion=0.23` when locked | 6/6 | 6/6 |
| Proposed `train_portion=0.1` | 9/9 | 2/9 |
| Proposed `train_portion=1.0` | 0/9 | 7/9 |
| Independent-case explanations explicitly distinguish `0.11` epoch validation from `0.23` final evaluation | 0/3 | 2/3 |

All responses proposed exactly 3 epochs. The free cases all proposed
`eval_portion=1.0`. Both arms already obeyed the tested locks and cap; this
sample therefore demonstrates **no reduction in ownership violations**.
Different training fractions demonstrate different proposals, not better
performance. Omitting the validation distinction does not establish that a
model misunderstood it. Explanations were inspected as text, not treated as
proof of execution or scored by another LLM.

The whole PR is the treatment: fixed strategy removal and factual disclosure
were changed together. This matrix does not isolate the effect of either.
Three stochastic calls per condition are exploratory evidence, not a robust
estimate of general reliability or scientific quality.

## Effective configuration witness

Each of the 18 recorded responses was then supplied to its matching version's
public `HyperparamTuningAgent.run` in a fresh workspace. The public preflight
skill boundary was captured before a GPU worker could launch. An independent
subprocess audit guard also prevented accidental child execution after the
response was supplied. No node-private module was imported by the harness.

All 18 runs produced the intended preflight-input artifact and one resolved
Trial configuration. Proposed and resolved epochs, training scope fraction,
per-epoch training fraction and final evaluation fraction agreed numerically
in these cases. One original response encoded the three fraction values as
JSON strings; existing schema coercion converted them to numbers. Raw proposal
values are retained in `results.json`. The capture includes CPU hardware snapshots. It does not establish GPU
admission, runtime feasibility, a training score, or that the trainer consumed
the independent `0.11` validation scope. The GPU integration remains pending.

One preliminary attempt stopped at CPU hardware validation and was interrupted;
it is excluded. Independent review found a harness reporting flaw: both the
intended capture and an unrelated blocked subprocess could report success.
The harness now requires the expected preflight artifact before reporting
success. Every qualified capture already contained that artifact, so the flaw
did not invalidate the 18 recorded captures.

## Cost and retained evidence

All 18 provider requests have known usage and settled ledger entries. Their
conservative debit totals **USD 5.115**, against the operator's USD 20 cap.
This overestimates ordinary cached-input billing: input was charged at the
maximum declared cache-write multiplier, without cache discounts. It is a
budget-accounting upper estimate, not an invoice. Prices were checked against
https://developers.openai.com/api/docs/models/gpt-5.6-sol on 2026-10-04.

Before each request, the local guard durably reserved USD 14.34 based on the
model's full input/output bounds. Unknown usage blocks later requests; an
initialized missing ledger refuses a reset. Seven local fault tests and
independent process-death/concurrency checks passed before launch.

Remaining budget is USD 14.885, only USD 0.545 above the next worst-case
reservation. Consequently, the current reservation policy cannot support a
full workflow after much further actual spending, even though the invoice
would remain below USD 20. The planned four three-iteration GPU runs have
**not started**. Revising their sample count or request bounds requires an
explicitly recorded experimental decision; this report does not change them.

`results.json` retains exact request/response/decision/receipt and preflight
artifact hashes, token usage, proposal fields, resolved fields and reasoning.
Raw prompts and full local artifacts remain in the operator's experiment
workspace, `/tmp/issue372-tess-validation`; this is a machine-local evidence
location, not a portable launch dependency or a guarantee of archival durability.
The frozen manifest digest is recorded in every call receipt and in the result
summary. No credentials, raw arrays or model checkpoints are included here.

Independent adversarial review checked all receipts against the manifest and
ledger, matched response identities, confirmed the counts above, and examined
the effective Trial configurations. No merge or public synchronization is
claimed. Historical scientific migration remains a separate qualification.

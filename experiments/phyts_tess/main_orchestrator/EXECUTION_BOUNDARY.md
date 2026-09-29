# PhyTS TESS orchestration — execution boundary

What an external caller receives, what it never receives, and the mechanism
that enforces each. **This is the review decision the condition rests on**;
the implementation is built on top of it, not the other way round.

Operator decisions recorded here, 2026-09-21:

| decision | value |
|---|---|
| deployment shape | **single host, two processes** |
| native training binding | **yes** — the caller trains through SIDERIUS, as TIDMAD does |

## Why the shape matters, stated plainly

TIDMAD's orchestration hangs on an existing baseline research room: a separate
research account, a protected evaluator service, and a narrowly authorized
scoring command. TESS has no such room, and building one is systems
deployment rather than code.

The single-host arrangement puts the caller and the evaluator in **two
processes on one machine**, separated by filesystem permissions and by the
answer-free agent view.

**Two accounts, and that is not a preference.** The framework's own launcher
refuses anything less (`experiments/shared/native_launcher.py`,
`authorize_native_caller`):

```python
if effective_uid != policy.coordinator_uid or effective_uid == policy.caller_uid:
    raise PermissionError("native launcher requires its separate coordinator account")
```

The coordinator must be a separate account, the caller must be a different
uid, and the caller's identity has to arrive through `sudo` rather than be
asserted. So "separated by filesystem permissions" is enforced rather than
merely intended: a single-user deployment cannot start the native binding at
all.

What this still is **not** is a full research room. TIDMAD additionally runs
a protected evaluator service and a narrowly authorized scoring command.
Here the evaluator is a process, not a service, and the deployment is
**not adversarially isolated**: a determined operator of the host can bypass
it, and no claim to the contrary is made anywhere. If the condition is ever
published as adversarially isolated, that gap has to be closed first.

## What crosses to the caller

A preparation bundle, written by `prepare.py` to a directory **outside both
repositories**. It contains:

| artifact | why the caller needs it |
|---|---|
| `composition.yaml` | the public composition overlay — the task declaration with every path resolved absolute |
| `execution-policy.json` | the bounds it must run inside |
| `agent-models.json` | routing for the LLM roles it may call |
| `deployment.json` | the receipt: revisions, digests, and what is still unresolved |

Plus read access to the **agent view** produced by
[`tasks/phyts_tess/tools/build_views.py`](../../../tasks/phyts_tess/tools/build_views.py):
training rows with their targets, and validation rows carrying identities and
**no target column**.

## What never crosses, and how each is prevented

### 1. The metric arithmetic

`tasks/phyts_tess/runtime/scoring.py` computes R², RMSE and MAE from truth the
caller must not have. The public composition replaces the metric
implementation with the framework's `CandidateEvaluationMetric`, which carries
the task's **declaration** — metric id, direction — and no arithmetic at all.
Its `require_executor()` raises `NoRunMetricError` unless a complete evaluator
is explicitly bound in the process, so a caller that obtains the manifest and
runs it alone **cannot produce a score**; it refuses before training rather
than scoring something wrong.

The two secondary metrics are **dropped from the public composition entirely**.
They are observational, the caller never orders candidates by them, and
carrying them would mean either shipping the same arithmetic or building a
second candidate-evaluation route for values nothing consumes on that side.
The evaluator computes them when it scores.

### 2. Validation truth

`TessScope.truth()` reads the committed identity manifest, and that manifest
carries the validation `frot` values. The public data path therefore reads the
**agent view manifest**, not the committed one, so the scopes it builds have
identities and no targets for the evaluated split.

This is the same property `build_views.py` already enforces and re-verifies by
re-reading the bytes it wrote — it is reused rather than re-implemented,
because a second answer-separation mechanism is a second thing to get wrong.

### 3. The held-out test split

Unchanged from the fixed workflow, and it needs no new mechanism: the split
type admits `train` and `val` only, the committed manifest carries no test
row, scope deserialization refuses a payload naming `test`, and the staging
tool copies two files by name while refusing a destination holding anything
matching `test`. No scope this task can construct reaches that population.

### 4. The scoreability contract

`tasks/phyts_tess/runtime/scoreability.py` validates deliverable **format** —
that predictions are present, finite, and keyed as declared. It contains no
truth and leaks nothing.

An earlier note in [`README.md`](README.md) said it stays private. **That is
corrected here**: keeping it private would force the caller to guess the
deliverable format from prose, and a caller that cannot tell whether its
output is well formed will submit malformed deliverables that the evaluator
refuses — turning a format question into wasted evaluation cycles. The
contract crosses; the **scoring** does not.

## Native training binding

The caller trains through SIDERIUS rather than around it. The machinery is
already task-generic — nothing under `experiments/shared/` names a task — and
covers model export and restore, the training channel, admitted validation
observations and objective review.

What it does **not** yet cover is this task's shape: a fixed-length,
single-channel input, `[B, 1, 1024] float32 → [B, 1] float32`. TIDMAD's is a
different geometry, so transfer is **unverified until a smoke run shows it**.
That is the first thing the implementation must demonstrate, and it is a
claim no amount of reading can settle.

Per-epoch validation goes through the evaluator, which owns truth: the caller
submits, the evaluator returns admitted loss observations. The caller never
sees targets, predictions-versus-truth, or residuals.

## Deliberately not claimed

- **Not adversarially isolated.** See the shape section.
- **Not launch-ready.** `prepare.py` emits a bundle and starts nothing: no
  clock, no LLM call, no training, no scoring.
- **No comparability claim yet.** Whether the orchestration condition may be
  compared with the fixed workflow depends on budgets that are not chosen
  here; `nop_004` ran six hours on one RTX 5090 with an 8 GiB VRAM budget, and
  matching that is a decision, not an inference.

## Do not

- Do not mount `siderius-exp` or a prepared bundle into the caller. Both carry
  the private scoring code.
- Do not reuse the fixed workflow's supervisor. It starts a clock and runs a
  chain, which is exactly what a preparation command must not do.
- Do not let the caller read the evaluator view, or the committed identity
  manifest, under any path.
- Do not weaken the answer separation to make a smoke run pass. If the native
  binding needs truth on the caller side, that is a finding to record, not a
  boundary to move.

# PhyTS TESS — general coding-agent baseline

The same static task run a different way: a general coding agent is given the
light curves, a target to predict, a clock and a machine, with no SIDERIUS
workflow around it.

**This experiment is NOT launchable.** What exists is the part that had to
exist first — the separation that keeps the answers away from the agent. What
does not exist is everything about provisioning and kickoff, which is
operator-owned. Both are listed below, honestly.

[`tasks/phyts_tess`](../../../tasks/phyts_tess/) owns the static scientific
task. This directory does not define another TESS task; it defines one way of
running the same one.

Information treatment:
[`main-cli-no-advice.yaml`](../information_treatments/main-cli-no-advice.yaml)
— no advice, and both workflow modules marked `not_applicable` rather than
`disabled`, because a general coding agent has no such module to switch off.

## What exists: the view split

[`tools/build_views.py`](../../../tasks/phyts_tess/tools/build_views.py)
produces two deliberately non-identical views from one staged data root.

```bash
.venv/bin/python tasks/phyts_tess/tools/build_views.py \
    --data_dir /path/to/run-data \
    --output /path/to/fresh/views
```

| view | contents |
|---|---|
| `agent/` | both light-curve archives · `train.csv` **with** targets · `predict.csv` with identities and **no** target column |
| `evaluator/` | `val_truth.csv` with the validation targets |

**Why this is not optional.** In a SIDERIUS chain the agent is an LLM that
never touches the filesystem — scopes and targets travel to child processes —
so the task package's committed identity manifest carrying validation targets
is harmless and in fact necessary, since the metric reads truth from the
scope. A coding agent has a shell. Any validation target under a path it can
read is a winning strategy: copy them into the predictions and score a
perfect R-squared, with nothing downstream reporting a problem, because the
deliverable is well formed, scoreable and complete.

The tool re-reads what it wrote and **refuses** to publish an agent view
containing an evaluated target, rather than trusting the writer standing next
to it. A training target is not treated as an answer — supervision must
survive, or the task is unlearnable. The split, not the column name, decides.

Both properties are guarded, including the failing counterexample:

```bash
PHYTS_TESS_DATA_DIR=/path/to/run-data \
    .venv/bin/python -m pytest tests/tasks/phyts_tess/test_phyts_tess_views.py -q
```

## What does NOT exist

Each of these is an operator decision or a provisioning fact, not something
to be inferred:

1. **The kickoff.** What the agent is told the task is, how it is told to
   produce predictions, and in what format. TIDMAD's equivalent is a
   hand-written `task.md`.
2. **The evaluation command** the agent may call, and how often. It has to
   score against the evaluator view without exposing it — the scorer runs in
   the trusted executor, never in the agent's workspace.
3. **Provisioning.** Work disk, machine, clock enforcement, retention and
   backup destination. TIDMAD's live under
   `deployments/tidmad_coding_agent_baseline/` with systemd units; nothing
   equivalent has been decided for TESS.
4. **The frozen input bundle.** TIDMAD records archive hashes in Git while
   the bytes stay in an external store. No such store is nominated for TESS.
5. **The budget.** The fixed workflow's six hours is a SIDERIUS-chain budget;
   whether a coding agent gets the same is a comparability decision.

## The comparison this is for

Against [`../main_fixed_workflow/`](../main_fixed_workflow/README.md), on the
same task and the same metric. For that comparison to mean anything, both
sides must be scored by the same authority against the same held-out
population, and neither may see it. The view split is that guarantee on this
side; on the workflow side it is the composition, which never names the test
split.

Note that both sides are evaluated on **validation**. The test split remains
untouched by either, for a separate final evaluation that no agent
participates in.

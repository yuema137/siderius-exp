# Local TIDMAD Data Analysis ON/OFF pair

This bounded, two-iteration experiment compares the same static TIDMAD task
with Data Analysis enabled or disabled. Both arms run Literature Review first.
When enabled, Data Analysis receives bounded Interpretation and Literature
evidence; Proposer receives Literature and Data Analysis as separate typed
evidence streams. The workflow selects this order; neither agent calls the
other. This is a local qualification of analysis behavior, not a full paper
campaign or a claim that two stochastic modeling trajectories are causal
replicates.

## Frozen treatment

| Shared across arms | Value |
|---|---|
| Data/Health scope | Complete high-frequency band, files 15–19 |
| Scientific evidence order | `literature_then_analysis` |
| Literature Review | Enabled, same task-owned config |
| Advice and LLM routing | Same [advice](advice.json) and pinned infra config |
| Tuning | 2 iterations, at most 2 rounds, 1 epoch, 0.02 Trial/Formal portions |
| Training admission | 20/60 minute Trial/Formal, measured; 12 GiB VRAM each |
| Sampling seed | `20260915` |

Only the [ON composition](task_composition_on.yaml) attaches
[Data Analysis](analysis_on.yaml); the [OFF composition](task_composition_off.yaml)
explicitly disables that edge. The underlying task paths and all other
composition fields are identical. ON gives Data Analysis 180 seconds per
iteration, at most ten task-stratified validation items covering all five
files, with a 45-second per-action limit. It permits reference skills,
sandboxed one-off programs and optional experiment-local skill promotion.
When a certified prior model exists, the agent may request historical
inference; its worker sees data, never target. Validation-target analysis
requires a separate authorization path. Whether raw or model-derived evidence
is worth the budget remains a planner decision.

## Local launch boundary

Run the two arms in **separate terminal sessions** against the same committed
experiment checkout and the exact SIDERIUS revision in
[`SIDERIUS_REVISION`](SIDERIUS_REVISION). Use two distinct fresh workspaces
outside both repositories. The launcher requires the same frozen experiment
SHA for both sessions and refuses a dirty checkout or a workspace inside the
raw data directory. It also checks that all
five training and validation HDF5 files and the approved scoring anchor are
present. Do not replace this scope with a lone file.

Prepare the exact checkout environments with `uv sync --group dev --frozen`.
When running the repository's full test suite against a newer framework pin,
set `SIDERIUS_DA_PAIR_CHECKOUT` to a separate checkout of this experiment's
own `SIDERIUS_REVISION`; its launcher tests intentionally fail on a mismatch.
Export `OPENAI_API_KEY` and `DEEPSEEK_API_KEY` from a trusted external secret
source in each launch session; the script checks only their presence and does
not print them. Dry-run requires neither credentials nor data/GPU access:

```bash
bash experiments/tidmad/data_analysis_pair/launch_arm.sh \
  --arm on --siderius-checkout /path/to/pinned/SIDERIUS \
  --workspace /path/to/fresh/on-workspace --data_dir /path/to/tidmad-data \
  --dry-run
```

After PR review/merge, real-data qualification and an operator freeze of the
experiment SHA, launch one command per session by replacing `--dry-run` with
`--expected-exp-sha <same-merged-experiment-SHA>` and using `--arm on` or
`--arm off`. Both commands must run on the local RTX 5090, not the H100
campaign. The one-GPU simultaneous workload needs active VRAM and admission
monitoring; a resource refusal is evidence to inspect, not permission to
silently change one arm's budget.

The required review receipt compares actual skill/program choices, generated
code sandboxing, report grounding, historical-model input and prediction
receipts, Literature→Analysis evidence, and the separate Proposer projections.
No ON/OFF result is claimed until both workspaces finish and those artifacts
are inspected.

# Strategy-only orchestration deployment contract

Condition: `O-StrategyOnly`. Reuse the completed O-NoPrior control; do not
schedule replacement controls. Only the information treatment adds controller
work strategy V3. Record runtime version differences separately; this is not a
claim that the historical control used identical runtime code.

## Preparation and assembly

Select `prepare --strategy-only`. This resolves the NoPrior binding and adds
the exact content-pinned `controller-work-strategy-v3.md` for the outer coding
agent. Data Analysis remains disabled, model advice remains absent, and native
role routing, data scope and execution budgets retain their existing authority.
Never use the historical joint `--prior on` selector for this condition.

Assemble the existing generic toolkit and frozen common input exactly as for
NoPrior. Copy the prepared strategy and `prompt-supplement.json` together into
the protected, agent-readable `run/` directory. Protect both files and their
parent directories against replacement by the research UID. Do not mount the
operator preparation directory or private exp checkout.

The additive `SIDERIUS-RUN.md` must declare:

- `O-StrategyOnly`; dedicated Data Analysis disabled; model advice absent.
- The absolute strategy path, its receipt SHA-256 and outer-controller recipient.
- Open that strategy at startup and after context recovery; preserve its path
  and the run declaration path in continuation summaries.
- Unchanged task, native tool, deadline, evaluation and submission authorities.

The experiment-level advice scope in `TREATMENT_SCOPE.md` permits this one
artifact outside the unchanged frozen input. Do not route it as model advice.

## Delivery at each new invocation

Keep the existing baseline supervisor command and add:

```text
--prompt-supplement /work/agent/run/prompt-supplement.json
```

The supervisor validates the manifest and strategy before creating a clock and
again before every new CLI process. It appends the exact strategy text and
recovery pointers to the existing kickoff prompt. Missing, modified or invalid
files refuse the invocation. Without this explicit option, baseline prompt
bytes are unchanged. No new timer, resource allowance or retry policy is added.

The generic toolkit's existing `AGENTS.md` requires reopening `SIDERIUS-RUN.md`
after recovery. Keep that pointer. New-process injection and recovery pointers
do not guarantee attention or automatic reinjection during the CLI's internal
compaction. Choosing and applying a strategy remains agent behavior.

## Data Analysis exclusion

Use only the NoPrior public candidate composition: its native DA binding must
be `None`. The compact training adapter has no `TaskAnalysisCapability`; native
composition rejects attempting to enable DA on that adapter. Do not supply the
separate Full analysis composition, policy or input-only validation view.

Before launch, check actual research-UID reads against existing paths for old
Full analysis inputs, findings, model advice, run histories and operator
preparation. Remove obsolete material after authorized collection, or deny
access to retained operator records. Missing files alone do not test permissions
on existing private artifacts. Keep private validation targets inaccessible.

This disables the supplied dedicated DA capability and information channel.
It does not prohibit ordinary task-permitted analysis of public training data
or claim to prevent arbitrary reimplementation of analysis in Python.

## Short qualification

Check all four band bindings and native DA refusal without training. Exercise
two fresh CLI invocations: the second starts from a short continuation summary,
opens the run declaration and strategy, and records the disabled DA/model
advice state. Check the transcript's actual file reads. Separately test that a
changed strategy fails before another process starts. Neither smoke starts a
formal clock, trains, scores, or certifies internal CLI compaction behavior.

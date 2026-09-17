# TIDMAD coding-agent baseline

This experiment gives each Codex agent one TIDMAD band, one H100, and an
independent 24-hour clock. The four no-advice units launched together on
2026-09-17. Their launch facts are in
[`main_codex_no_advice_2026-09-17.json`](main_codex_no_advice_2026-09-17.json),
and the four immutable input-archive identities are preserved in
[`frozen_bundle_manifest.json`](frozen_bundle_manifest.json). These are launch
records, not final scores or evidence that every submitted model is scientifically
valid. Results and behaviour traces require separate post-run review.

## One task, different ways to run it

[`tasks/tidmad`](../../../tasks/tidmad/) owns the static scientific task. The
CLI deployment builds its agent-visible task view and evaluator-private view
from that same pinned task tree. The private view is not exposed to the agent;
the two views are deliberately not byte-identical. The CLI-only additions are
the kickoff `task.md`, an evaluation command, and machinery for clocks,
retention and backup under
[`deployments/tidmad_coding_agent_baseline`](../../../deployments/tidmad_coding_agent_baseline/).
The fixed workflow selects the same task through its own experiment
configuration; it does not define another TIDMAD task.

For these four units, human advice and Data Analysis are both absent by the
frozen [`main-cli-no-advice.yaml`](../information_treatments/main-cli-no-advice.yaml)
treatment. Each unit has its own band-scoped training files and full-band
validation evaluation. No result from an earlier diagnostic run is an input.
The work disks, raw HDF5, model weights, CLI traces and secrets are **not** in
Git. Backup buckets are evaluator-owned output stores, not extra agent working
space. The input tarballs remain in the operator's external frozen-artifact
store; the repository records their hashes, not their bytes.

The run was built from the experiment and framework commits recorded in the
frozen manifest. Those historical pins do not move when this repository's
current `SIDERIUS_REVISION` changes. The deployed scorer-wrapper correction and
backup temporary-directory configuration are recorded separately in the run
receipt, because they were installed after the input archives were frozen.

## Future framework-assisted coding-agent condition

Not launched or implemented here. It should keep the same static task and
scoring contract, then add a separately pinned framework skill set: a top-level
map of available agents and one callable skill per public agent interface,
each with explicit inputs, outputs and effects. The kickoff should recommend
using those skills first and permit a direct alternative when the framework
cannot express the needed work. Skill use must be recorded, not presumed; an
agent that never calls a skill is evidence for a *framework-available* condition,
not for an effect of framework use. The agent may write its own workspace but
must not modify the pinned SIDERIUS or siderius-exp source during the run.

Reserve a separate optional Data Analysis binding in that later condition.
The current Data Analysis development is independent and is not a prerequisite
for, or part of, the no-advice CLI run recorded here. Do not turn this paragraph
into a launchable third arm until its skill contract and Data Analysis interface
have been reviewed and qualified.

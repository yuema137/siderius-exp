# MJD tutorial contract

Scope: initialized external Majorana Low-AvsE projects, saved-script execution,
CPU previews and recorded progress. Scientific task source and old experiment
profiles remain unchanged. This treatment is not a paper reproduction or a
new train/validation/final split. Official Test feeds search evaluation.

`settings.MjdExperiment` validates paths and experiment knobs; native framework
schemas remain authoritative for workflow/task execution. `runner.build_command`
owns exposed-knob/native-flag mapping. Train fractions map to trial_portion and
formal_portion; eval fractions map to eval_portion and formal_eval_portion.
All four exposed scope fractions use the native CLI range [0.01, 1.0];
both Trial and Formal training default to 0.01. Both epoch train_portion flags are fixed at 1. Snapshot strategies are explicit.
The new workflow uses native timing defaults, no DA/literature/advice, diagnostic
authority and the task's explicit no-Health declaration. Healthgate mode stays
blocking; no checks are invented or bypassed for the no-Health task.

`project.create_project` refuses existing/source/data-overlapping destinations.
It copies the whole task and current Luna routing, workflow and empty-output
notebook; binds absolute paths; writes a script through shared.saved_script.
No data download/copy, credential read or training belongs to initialization.
`save_variant` validates the merged settings and assigns fresh JSON/script/run
paths; partial I/O failures retain their files and require inspection/new names.
Users edit external copies only. Advice activation is unsupported, schema None.

`data.verify_files` validates the copied and source official dataset manifests
with Pydantic, requires equality, then checks all 22 supervised filenames and sizes.
NPML files are excluded. Launch executes the original task-owned verify_dataset.py
using the exp interpreter and authoritative source manifest, with supervised-only
MD5 checking. It never trusts a modified copied verifier or rewritten checksums.
No checksum cache weakens this launch gate. Preview size checks are not integrity
certification. Small scopes still read full-role metadata; raw waveforms load
lazily through task datasets.

`scope_counts` calls the selected composition/data path's native scope and
materialization methods at illustrative seed 42, epoch fraction 1. Counts reflect
fraction selection followed by exact 25-keV balance; they are not attempt identity
promises. `show_waveform` uses the task's training dataset transform, then reads
the same Train row for the raw panel. Neither figure nor count helpers train,
allocate CUDA or contact providers. A modified task changes copied code identity;
there is no supported split rewrite in this tutorial.

`runner.inspect` checks exact source/package pins, planner identity, selected
composition, data sizes and required key names. Launch additionally checks keys,
GPU and official MD5; no expensive hash scan happens during offline preview.
The saved script owns validation/receipts/native launch. `demo.review` verifies
literal script bindings and reloads settings before presenting all saved paths.
Used workspaces suppress its executable commands. The notebook delegates only to
its saved script; shared.saved_run owns timeout/descendant cleanup, log, receipt,
nonzero refusal and unchanged-success cache behavior. No local lifecycle copy.

MJD's input digest includes saved JSON/script/routing/workflow, every copied task
file except bytecode, selected/resolved paths, both source HEADs and tracked diffs.
Raw data, untracked checkout files, environment/provider state and result bytes
are excluded. Input snapshots are not forensic replay or protection against
concurrent edits; do not edit inputs while a run is active. Shared Pet-compatible
receipt behavior intentionally differs from paper v2; no implicit migration.

`plot_results` requires explicit no-Health and finite native Formal
energy_matched_roc_auc/higher observations, then delegates to shared.progress
with health_policy=none. No-score data refuses a placeholder graph. Failed scored
attempts remain visible; missing observations remain in a chart's CSV. Shared
CSV validity=pass denotes successful scored execution here, not Health PASS.
Plotting uses saved experiment/composition and records only, independent of launch.

Notebook: exact exp kernel and TUTORIAL_HOME binding; no config literals silently
saved on Run All. Save-as is opt-in. Live execution is explicitly disclosed before
RUN_QUICK_DEMO; native preview has a separate switch. The source notebook embeds archived PNG outputs at the data and score cells,
with provenance in `example/provenance.json`; its other outputs are empty and
execution counts are null. Initialization clears all outputs/counts. CPU data
figures and actual training records are labeled separately.

Validation owners: focused tests cover native mappings, official manifest
substitution/refusal, actual fixture loader/normalization, source isolation,
quoted scripts/save-as, cache handoff, no-Health plotting and offline notebook
execution. Real CPU preview/native dry-run evidence is separate from fixtures.
The recorded three-iteration API/GPU qualification completed on the source
revision recorded in `example/provenance.json`; subsequent gallery edits are
presentation only. Cached Run All was verified with no new API requests and an unchanged
completion receipt. This establishes the
recorded sequence, not universal generated-model or hardware qualification.

# Cancer CPDB tutorial contract

The task-owned CPDB composition is a teaching variant: it selects only CPDB and
`evaluation_split: val`. Its tutorial task description narrows the population;
the forward contract is identical to the original task declaration. The selected
dataset profile declares one CPDB partition, and tutorial proposal blocks describe
CPDB-only evidence and full-graph label sampling. Neither reuses an operational
instruction to compare all eight networks. The task's real data loading, loss,
metrics and original splits are unchanged. Candidate checks use the task-owned
[synthetic graph fixture](../../../tasks/cancer_gene_identification/plugins/model-probe.md)
through the framework's optional input capability. Archived configurations and
dated provenance retain their original source pins. No framework policy or
scientific loader is copied.

`settings.CancerExperiment` owns external paths, three-iteration defaults,
positive time/VRAM allowances and native fraction range [0.01,1].
`project.create_project/save_variant` copies the task and all-Luna configuration,
clears notebook outputs and writes exclusive JSON/script pairs. Source/data/output
roots must be disjoint. Shared saved_script validates literal path/module bindings.

`runner` renders the external workflow and maps training label fractions to
`--train_portion` / `--formal_train_portion`. Training scope portions remain 1.
The task's training_dataset gives EpochSamplingParams.train_portion precedence
over the scope fraction. Validation fractions map to `--eval_portion` /
`--formal_eval_portion`. The workflow explicitly selects operator Formal scope,
structured `regressor` output, masked BCE via composition, and minimum batch 1;
the task parameter rule and inference hook require exactly one complete graph.
No second fraction multiplication or graph sampling is implied. All four phase-specific label selections
respect the original task masks; Test labels remain unused.

`data` validates copied source metadata against the repository authority and
checks file size, graph shape, original disjoint masks and active binary labels.
Launch verifies the complete official SHA-256; ordinary review is explicitly
size/structure only. Task composition resolution checks CPDB/val, no Health,
batch1, native task id, custom objective and mean_auprc. Previews materialize
through that task, never a parallel graph loader. Seed42 count/class previews
are illustrative; they cannot establish later attempts' class support.

`demo` reuses saved_run for execution/cache/failure cleanup and shared progress
for no-Health score rendering. Input identity binds copied task files, experiment,
script, routing, workflow, source checkout identities and raw resolved path/size/
mtime. Fresh SHA verification owns raw integrity; this is not a hostile mutation
or concurrent-file race guarantee. Plotting old records needs no dataset or API.
Cache reuse still verifies current local input identity before delegating to the
shared completion check. No new lifecycle or registry is introduced.

Hardware-only inspection uses tutorials.shared.hardware. Fresh launch additionally
checks credentials and the shared GPU configured-cap readiness before native
execution. Passing is a snapshot, not reservation/model-fit proof. Host RAM/disk
observations and CPU materialization evidence are not universal resource bounds.

Validation is focused: true native parser/normalizer, actual loader fraction
ownership/topology parity, source identity and bad-input refusals, saved-script
handoff/cache/notebook output clearing, original task contract and offline copied
notebook with real CPDB. The [example receipt](example/provenance.json) records
the separately authorized completed live qualification and its exact source pair.

## Offline qualification boundary

The author checkpoint passed 19 focused tutorial checks and 11 existing Cancer
task-package checks. Existing CPDB bytes matched the pinned SHA-256; the actual
loader preserved 13,627 nodes and 518,005 packed records with 2,013 Train, 224
Validation and 746 reserved Test nodes. A copied notebook completed all six
code cells with live execution disabled. Committed-source saved-script preview,
three rendered native argv parser/normalizer checks and independent source review
also passed. These offline checks are separate from the live evidence below.

## Recorded live qualification

Executed exp revision `9e5b4c166dc0a58271c251e93e6f3f453c8310bd` with pinned infra
`52373be9a52bead36fd1f15d706385967e0a129d` completed three iterations, each with
one successful Trial and Formal record. The all-Luna run used original full
CPDB Train/Validation masks. Native automatic implementation retries repaired
generated forward-interface mismatches without manual source/model intervention.
All 42 provider requests settled; recorded cost was $0.067196. Repeating Run All
reused the result without new requests and preserved the completion receipt.

Archived notebook outputs contain only the genuine graph and score images. The
initializer still clears outputs and execution counts. The example CSV changes
only machine-local source paths to project-relative paths; its scores/statuses
and PNG/SVG bytes are unchanged. Native records, not gallery assets, remain the
plotting authority for each new user project. See the receipt for timings,
source hashes and the distinction between diagnostic execution and Health.

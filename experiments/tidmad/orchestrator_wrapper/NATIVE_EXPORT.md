# Native candidate packaging

`native_candidate.package_native_candidate` bridges an explicit native
`ExperimentRecord` to the existing CLI evaluator's candidate directory. It
requires a certified trained-model reference, an approved model plugin, the
typed evaluator contract, explicit CPU examples, and a new output directory.

The research worker must supply filesystem/resource/deadline isolation. The
function imports and executes the certified generated code, so it must never
run in the private evaluator's security context.

The adapter verifies record/model/config identity, uses the shared certified
restorer and scripting exporter, and reloads the pair through the unchanged
`load_candidate_model`. It checks supplied examples against the frozen 40,000
sample int64-to-float32 regression contract. It retains the source, original
certified descriptor/config bytes, training metadata and provenance. It does
not retain examples, input HDF5, private targets, credentials or scores.

The returned digest is the existing evaluator's candidate-tree digest. Submit
the resulting directory through the existing evaluation interface; this helper
does not score, archive as a valid candidate, select a winner or grant data
access. Proposed training settings and observed training history are recorded
separately so a time-budget stop is not rewritten as the proposed epoch count.

The component tests exercise certified restoration, scripting, saved weights,
directory validation and actual frozen-evaluator HDF5 inference on synthetic
data. This is not a real scientific score or an end-to-end orchestrator run.
Training-precheck integration, isolated operation dispatch and real candidate
replay still require qualification.

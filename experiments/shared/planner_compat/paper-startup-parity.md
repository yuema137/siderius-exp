# Actual paper task planner startup parity

## Contract and selection

The explicit v4 profiles extend role-v3 with experiment-owned configuration
manual rendering. Infra offers an optional string renderer for this section;
its default remains `json.dumps(manual, indent=2)`. The provider receives a copy,
so it cannot mutate execution schemas. An unknown manual refuses before the
provider call instead of discarding unrecognized controls.

Two historical schema eras exist; one universal old manual would be incorrect:

| Historical lineage | Explicit selector | Manual reference |
| --- | --- | --- |
| TESS, LIGO, TIDMAD NoPrior | `legacy-9b78d505cb11-paper-v4` | Before three training fields |
| Project8 dual, TIDMAD analysis-on | `legacy-9b78d505cb11-paper-late-v4` | Includes all three training fields |

The three fields are `checkpoint_selection`, `target_standardization` and
`drop_last`. Project8 and analysis-on TIDMAD already had them at their recorded
infra revisions. V4 changes prompt representation only; it does not restore
old execution bugs or weaken current schema validation. Existing provider
versions and installation defaults remain unchanged. V4 identities hash the
source, inherited v3 identity, frozen manual evidence and selected manual era.
Use a fresh workspace for the new identity.

## Production startup verification

`capture_startup.py` runs the real tuner startup and stops at its first final
planner message. The caller explicitly supplies a new output directory,
composition and expected fingerprint, data root, archived seed model and
description with expected hashes, and tuner parameters. The model is registered
through the normal loader, reproducing the upstream implementor's registration.
Model descriptions are staged into the new workspace's authorized plugin tree.
Network access is forbidden; a constructor placeholder is not an API credential.
The captured planner never returns a plan, so no training is started.

Four startup pairs were captured using each experiment's original infra revision
and its own frozen environment, then compared with current production startup:

| Task | Original infra | Actual first model | Result |
| --- | --- | --- | --- |
| TESS | `7689fd58b91d410788e953b51ea69a9dbc528a7d` | `cadence_aligned_spectral_resnet` | System/user bytes match |
| LIGO | `0ab1573602c708ddd182432ad4d0e43ae4828c53` | `dual_domain_chirp_fuser` | System/user bytes match |
| Project8 dual | `349b6cd6d9766abbf3d87515b22e1005599a694b` | `dual_axis_crossattn_regressor` | System/user bytes match |
| TIDMAD NoPrior, band 0–3 | `345c802d82c71f72e1b73a90d2bf702d09d1865d` | `wholeband_gated_dilated_regressor` | System/user bytes match |

The model descriptions and `expert_advice_followed` strings come from the
corresponding archives; the latter is written by the record producer from the
tuner input, not generated anew. Actual task compositions reproduce the archived
fingerprints. TESS's original exp revision remains unknown; task assets from
`8513deabe042acfbb7743b5981bb790726ae0e82` reproduce its archived fingerprint.
This qualifies those assets, not an inferred original repository revision.

The differing intermediate input fields are the explicit strategy/identity and
timing context, the two manual eras, and LIGO's relocated Formal appendix.
Their final rendering matches. Other captured planner input fields match.

`fixtures/paper_task_startups.json` freezes the four actual captured argument
sets and original final-message hashes. `startup_check` rehydrates the typed
arguments, registers an explicitly supplied SHA-checked model, and obtains the
manual from the current production skill. It does not inject the old manual to
make the comparison pass. Scoreability identity fields are preserved, while
actual scoring refuses. A mismatched model or message digest fails.

## TIDMAD analysis input recovery

The four analysis-on compositions were generated from the frozen exp revision
`552535dc43227baef69a79b81e038c9e09e275b9` by `composition_overlay`: relocate the
frozen task's file/config/declaration references to the recorded deployment root
and bind the recorded analysis-policy path, then serialize with `yaml.safe_dump`.
Policies come from that revision's `full-prior-v6/<band>/analysis-policy.yaml`.
All eight reconstructed file hashes match the respective launch receipts.

Exact historical bytes are retained under `paper_inputs/tidmad-analysis/` and
listed in `paper-replay-369.json`. Their old absolute paths are provenance, not
portable launch defaults. For relocated execution, use the recorded exp revision's
`experiments.tidmad.information_treatments.prepare_full --condition da-only`
with a new external output directory. Verify policy identity and task semantics;
relocated YAML bytes naturally differ from the archived path-bearing bytes.

## Coverage and exclusions

The four actual startup pairs supplement the twelve shared branch cases and
thirty role/ordering producer comparisons; these counts describe different
populations. TIDMAD's other bands and analysis-on conditions retain branch and
source qualification, not a claim of eleven full startup captures. Recovered
analysis configuration is not a replay of the analysis agent's conversation.

This PR qualifies planner input assembly for the recorded cases. It does not
claim every historical iteration was reconstructed, nor any LLM response or
score reproduced. Implementor training-contract additions, interpreter ordering
evidence, and full upstream/downstream message replay are explicitly deferred to
a separate PR by operator decision. Deleted prediction files are not required.
No API requests, GPU training or dataset downloads were performed.

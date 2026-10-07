# Tutorial qualification after infra PR #605

## Scope and versions

The exp dependency advances from `349b6cd6d9766abbf3d87515b22e1005599a694b`
to `e800fc1f08b0e067fc21076a200f3f70d04b38b8`, the merged infra
[PR #605](https://github.com/Galileo-Sandbox/SIDERIUS/pull/605).
The operator authorized that public infra release; its public master was
verified at the target before generating the exp lock. This report does not
authorize merging or publicly synchronizing exp.

Executable exp candidate: `ad843c94a9dc97f9cc6fa27a7694887fdcc088ad`.
Both checkouts used their own Python 3.12.13 environments. `uv lock` changed
only the infra reference and added the existing exp-owned
`siderius-planner-compat==0.4.0` package as a normal, non-editable dependency.
The version file, dependency, generated lock, installed VCS metadata and clean
infra checkout all passed the existing pin checks.

The [machine-readable receipt](2026-10-07_infra605_tutorial_qualification.json)
records four preview identities and all 47 comparison results. It stores
canonical JSON message hashes rather than full prompts or private data.
The hash serialization is `json.dumps(messages, sort_keys=True,
ensure_ascii=False).encode()` followed by SHA-256.

## Implementation and behavior

Fresh external tutorial projects explicitly select `legacy-9b78d505cb11-v1`.
Its frozen planner source matches the old tutorial pin's `prompts.py` SHA-256
`9b78d505cb11786319aca45e763f48d73d235e0f7e9de6fb3a62ffc774d237bd`.
This retains the previous planner strategy selection; it is not a claim that
new demos reproduce a historical paper conversation. Paper replay uses its
separately versioned profiles.

The shared helper preserves explicit strategy choices and all routing fields.
Preview resolves the selected provider in exp and infra and compares complete
typed identities, including content and assembly digests. An absent provider
or mismatch reports installation/configuration repair steps before launch.
No provider constructor, network request or automatic installation is involved.
Scientific task declarations, historical configurations, scoring and archived
notebook outputs are unchanged. Existing user projects are never rewritten.

## Targeted local checks

Run from the exp checkout after the documented frozen installation:

```bash
.venv/bin/python -m pytest -q \
  tests/tutorials \
  tests/experiments/test_fixed_workflow_config.py \
  tests/experiments/test_information_treatment.py \
  tests/experiments/test_workflow_credentials.py
```

Result: **91 passed in 8.84 seconds**. Changed Python files passed Ruff and
format checks; `git diff --check` passed. The checks cover four initializer
bindings, preservation of explicit selections, refusal to overwrite, absent
providers, full-identity mismatch and secret-free child error handling.

The original TIDMAD seal/credential tests depended on an ambient
`/tmp/siderius-tutorial-infra` checkout. Their fixture now uses `tmp_path`.
The seal test resolves the real composition in its own interpreter; the
credential test isolates installation/composition checks while retaining its
original refusal assertions. The actual separate infra interpreter is exercised
by the saved-script checks below.

## Four real saved-script previews

All projects were freshly initialized beneath an external directory containing
spaces. Each generated `scripts/run-TASK.sh` was executed with `bash` from an
unrelated working directory, without `--launch` and with `OPENAI_API_KEY`,
`GEMINI_API_KEY`, `DEEPSEEK_API_KEY` and `PYTHONPATH` removed.

| Task | Preview | Data preparation for this check |
| --- | --- | --- |
| TESS | PASS | No data required for preview |
| TIDMAD | PASS | No data required for preview |
| Project8 dual representation | PASS | 20 training / 20 validation rows, selected from existing local prepared observations |
| LIGO | PASS | 20 training / 20 validation rows, selected from existing local prepared observations |

Project8/LIGO used the existing `DatasetRecipe`/`prepare` API and the pinned
local source manifests. Their two-row epoch-loss subsets were declared by the
existing 10% rule. No raw dataset was downloaded. Preview checked composition
and configuration, reported missing key names, recorded the exact infra and
planner identities, and left run workspaces absent.

For example, after following the installation and project initialization
instructions in the [tutorial README](../../tutorials/paper/README.md), execute:

```bash
env -u OPENAI_API_KEY -u GEMINI_API_KEY -u DEEPSEEK_API_KEY -u PYTHONPATH \
  bash "$PROJECT/scripts/run-tess.sh"
```

The expected result is a JSON receipt and a missing-key warning, without
training. The corresponding saved scripts are `run-tidmad.sh`,
`run-project8.sh` and `run-ligo.sh`; the last two require their prepared task
declarations first.

An additional real negative check temporarily removed only the planner package
from the isolated infra environment. The TESS saved script refused with
`Infra cannot load the selected planner` and the explicit `uv pip install`
repair command. The same package was then restored. Unit coverage separately
checks a changed content digest even when the provider name remains unchanged.

## Historical prompt boundaries

The existing `experiments/shared/prompt_compat/compare.py` harness compared the
exact target infra against the frozen reference checkouts, using each
checkout's own interpreter. Candidate infra normally installed the existing
planner and prompt compatibility packages; their source was not edited.

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare.py" \
  --candidate "$INFRA_CHECKOUT" \
  --references "$REFERENCE_MAP" \
  --output "$NEW_COMPARISON_DIRECTORY"
```

`REFERENCE_MAP` is the existing harness's JSON mapping of `tess`, `tidmad`,
`project8`, `ligo` and `analysis` to their frozen infra checkouts. Each fixture
supplies its required reference revision; mismatched revisions refuse capture.
The receipt records the actual revisions, input hashes and comparison scope.

Result: **47 MATCH, zero differences/errors**: 11 each for TESS, TIDMAD,
Project8 and LIGO, plus three analysis cases. These are the existing declared
rendering/producer boundaries, including their documented reconstructed inputs.
They do not certify complete historical conversations, stochastic responses,
training results, or runtime timing across every data/hardware scale.

## Review and remaining work

Implementing-agent review checked source ownership, unchanged scientific files,
explicit routing preservation, both-environment resolution, generated commands,
error instructions and English README readability. No independent-agent review
was performed in this slice. Local targeted verification was selected by the
operator; this exp checkout has no GitHub Actions workflow. No full-suite or
remote-green claim is made.

API calls, training and GPU work: **not run**. Notebook Run All execution is
also not newly qualified by these script previews. Existing displayed results
retain their original provenance. Pet, MJD, SuperNEMO and Cancer completion,
including the remaining infra #567 robustness work, remains a separate step.

# Proposer time-budget historical presentation, v2

## Scope and owners

SIDERIUS now renders configured Trial/Formal time budgets in every proposer
request and describes its static estimate as advisory. The experiment package
owns explicit historical presentation. Its v2 profiles suppress only the new
`proposal.time_budget_context(inp: ProposalInput) -> str` text boundary while
continuing to load the unchanged frozen proposal templates, including their
historical static-gate wording. Execution, validation, retry counts and runtime
admission remain native. No scientific configuration or default task is changed.

The source registry is `pyproject.toml`; the provider and declared source closure
are in `src/siderius_prompt_compat/__init__.py`. V2 accepts only assemblies in
`src/siderius_prompt_compat/qualification-v2.json`. V1 retains its separate
`qualification.json` and refuses the new framework assembly. An unspecified
`prompt_renderer` selects native rendering.

## Explicit selection

V2 requires the new framework checkout qualified in
[`qualification-v2.json`](src/siderius_prompt_compat/qualification-v2.json),
initially `830d819f3233cad23ac613c1ba1c50f82b8efa88`. A merge with the identical
rendering assembly is accepted by the same digest. The root exp
`SIDERIUS_REVISION` remains at its older pin, which cannot select v2; this
compatibility change does not promote that installation pin.

Install this checkout's standalone package into that qualified framework
checkout's own frozen environment. Reuse the commands from
[installation](usage.md#1-install-into-the-infra-environment), with
`INFRA_CHECKOUT` bound to the new qualified checkout rather than the older root
exp pin. The root exp dependency lock does not consume this standalone package.

Copy the intended task package and experiment declarations into an external
project, preserving relative paths. Apply only the `task_composition_overlay`
from [paper-proposer-budget-v2.json](profiles/paper-proposer-budget-v2.json) to the
copied task manifest. This file is an explicit selection reference, not an
automatic launcher overlay. Keep the separately selected planner/runtime
compatibility settings and original budgets.

| Paper branch | Previous profile | New profile |
| --- | --- | --- |
| TESS NoPrior, LIGO NoPrior | `paper-early-v1` | `paper-early-v2` |
| Project8 dual NoPrior | `paper-late-v1` | `paper-late-v2` |
| TIDMAD NoPrior, four bands | `paper-tidmad-noprior-v1` | `paper-tidmad-noprior-v2` |
| Separate TIDMAD analysis-on at `c0467447` | `paper-analysis-c0467447-v1` | `paper-analysis-c0467447-v2` |

For example, the copied LIGO manifest selects `prompt_renderer: paper-early-v2`.
The four source task manifest paths are recorded in the overlay; archived
workflow declarations remain unchanged. The analysis-on branch retains its
separate documented recovery-policy selection.

Use a new output workspace. The package fingerprints all packaged Python,
Markdown and JSON files, including qualification files. Therefore adding v2
changes the installed package identity even when selecting v1; preserving a v1
selector does not preserve an old package digest. Resume an existing workspace
only with its original package and framework bindings. Never edit its lock to
accept this upgrade. Unknown assemblies fail before rendering, and an
undeclared rendering boundary is refused rather than falling through.

## Offline qualification contract

The existing `compare.py` corpus contains 47 frozen boundary cases, including
24 proposer system-template cases. Run it with `--profile-version 2` for the
new candidate and the historical checkout mapping described in
[usage](usage.md#3-inspect-the-offline-comparisons). It compares UTF-8 message
hashes without whitespace normalization and does not reconstruct intermediate
proposer user requests.

`compare_proposer_requests.py` separately compares the complete requests emitted
by the pre-fix framework at `c7996a352d064229725ab1ebe886b9006bdbf36d` with its v1
profile and the candidate framework with its v2 profile:

```bash
"$EXP_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare_proposer_requests.py" \
  --reference "$BASE_INFRA_CHECKOUT" \
  --candidate "$INFRA_CHECKOUT" \
  --output /your/new-request-comparison-directory
```

Each framework checkout must first receive its own frozen environment and the
normally installed package. The capture process rejects dirty framework source,
an unexpected revision or a borrowed environment. It blocks network access,
injects a scripted bridge and binds an empty generated library to a temporary
workspace. Native protocol conversion, node assembly and retry validation run.

The immutable fixture `request-fixtures/proposer-budget-v2.json` declares a
single synthetic, classification-shaped evidence/reply corpus, used with the
four paper task-to-profile mappings. Its twelve cases cover explore/exploit,
legacy reasoning/commit, absent budgets, text stages, clamping and the four
correction/retry branches. These are supplementary branch witnesses, not four
reconstructed scientific conversations. Expected call labels are asserted before
comparing full system/user bytes. Missing historical intermediate replies remain
missing; neither command calls a provider or trains a model.

Installation checks use `check_installation.py --profile-version 2`. They verify
the installed package, frozen template source inventory and unknown-assembly
refusal through actual entry points. Package tests additionally ensure v1 and
v2 assembly admission stays separate.

## Evidence status

The [qualification report](qualifications/proposer-budget-v2/report.md) records
the exact reviewed assembly, source/package identities and executable comparisons:
47/47 preserved boundaries on each side and 48/48 synthetic sequences.
The pre-fix c7996a assembly required a separate baseline qualification because
the existing v1 list stopped before optional model-probe transport was added.
Its addition admits only the old assembly; it does not make v1 accept the new
budget-context boundary. No complete historical conversation or paper-score
replay is claimed.

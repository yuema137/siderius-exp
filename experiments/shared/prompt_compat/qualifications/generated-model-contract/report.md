# Generated-model contract qualification

## Qualified pair and scope

Infra `13e3b980177ab97e5da2e3a98a543588acd7ebb7` checks generated model defaults
before implementation and explains that contract in native proposer requests.
It also includes the earlier retry documentation changes, which changed the
rendering assembly identity. Prompt package `0.10.16` admits this exact assembly
under the existing explicit v2 profiles; frozen renderers and scientific inputs
are unchanged. The current v2 selection overlay requires this package version.
Root dependency pins and locks, v1 selection requirements and archived evidence
remain unchanged.

The infrastructure default is intentionally corrected. Archived proposal and
implementor inputs remain readable and transportable, but actual implementation
checks eligibility before model or custom-loss calls. Historical rendering does
not authorize execution of incompatible generated defaults or bypass validation.
Registered model reuse retains its own configuration contract.

## Offline evidence

The [receipt](receipt.json) records the final committed candidate and existing
capture tools. All checks used the selected infra checkout's own frozen environment
with the four standalone compatibility packages installed, without source-path
injection. No real API, training or GPU work was performed.

| Check | Result |
| --- | --- |
| Recovered four-task and analysis-on rendering corpus | 47 exact system/user hash matches against retained historical references |
| Complete scripted proposer requests | 48 sequences, 156 requests match clean reference `c7996a352d064229725ab1ebe886b9006bdbf36d` |
| Installed-source and frozen inventory checks | Pass, including four unknown-assembly refusals |
| Explicit historical selection and paper model routing | Pass |
| Planner historical message self-check | 28 pairs match; registry boundary checks pass |
| Prompt package and scheduler-manual tests | 66 pass; updated overlay recheck: 7 pass |

The complete-request comparator compares full system/user strings before recording
hashes. The receipt retains compact per-case digests of those ordered message-hash
lists rather than duplicating both matching transcripts. The frozen corpus compares
against unchanged `reference_messages` from the Luna-defaults receipt.

The 48 scripted cases exercise the existing no-rule request shapes. The paper
scheduler-only rule is stripped by the explicit historical renderer. This is not
a claim of full legacy-request equality for arbitrary additional parameter rules:
the native legacy commit now receives applicable rule guidance. The separate
scheduler test pins literal historical rule prose instead of deriving its expected
text from the changing native renderer.

These results establish the bounded prompt and information-composition comparisons
above. They do not establish complete historical conversations, future LLM response
equality, historical invalid execution or equality of retrained scores/artifacts.

## Reproduction and workspace selection

Use a fresh workspace with the explicit
[v2 selection overlay](../../profiles/paper-scheduler-disabled-v2.json).
Install its declared standalone packages into the selected infra environment;
do not modify old workspace locks or assume the repository root installation pin
selects this new pair.

Follow the existing [offline capture procedure](../constraint-disclosure/report.md#reproduce-the-offline-checks)
with the candidate revision above and fresh output locations. For each unchanged
`fixtures/*.json` from the Luna-defaults receipt, run `capture.py` with the matching
v2 profile: TESS/LIGO use early, Project8 late, TIDMAD no-prior, and analysis the
analysis profile. Compare the receipt's message hashes without normalization.
Run `compare_proposer_requests.py` against the clean reference above, each using
its own environment. Run `check_installation.py --profile-version 2`,
`check_constraint_disclosure.py`, and `check_paper_proposer_routing.py` with the
candidate revision. Run prompt-package tests plus
`planner_compat/tests/test_scheduler_manual_v11.py` with explicit
`SIDERIUS_CHECKOUT`. Finally bind `paper-early-v2` and call
`siderius_planner_compat.self_check.check()` for planner parity.

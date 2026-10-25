# Validator pre-disclosure prompt baseline qualification

## Scope and pair

This is prompt-rendering evidence for exp #278, preceding infra #848. Reference
infra is `4ec6c6968da61dc13a0d6d9acfa13fa56b53305b`; candidate is
`1f15ba6d470c64ec55ad8c0029cf7c1398db0cef`. Both use their own frozen environments.
Exp source starts at `b48c37477b38c6c6a8f9dfef5467a6e5e8c47635`. Standalone
prompt package0.10.18 admits only the pre-disclosure rendering assembly
`803e9ce34470b275329ca7bb9408945e98268d3303faabb607f0655d9d67bb0f`.
A later disclosure adapter must use a subsequent version, not overwrite0.10.18.
Root pins, overlays, archived fixtures and previous receipts remain unchanged.
The new #848 assembly is not admitted by this change.

## Executed evidence

- All47 existing native rendering boundary pairs match accepted source, and all47
  historical v2 pairs match the original registered-reuse receipt hashes. Existing
  fixture reconstruction, synthetic-input and system-only limits remain intact.
- All16 reconstructed complete validator requests match in native and historical
  modes (four tasks times clean/pytest/gradient/absent-contract). Comparisons use
  raw complete system/user strings, including the final constraint appendix.
  Mathematical descriptions are recovered fixture inputs; plugin source, advice
  and errors are explicit synthetic inputs. This is not historical wire replay.
- Both installed-package checks confirm reviewed package/source equality, all16
  frozen source-inventory entries and all four unknown-assembly refusals. The
  historical profile identities are retained in the installation receipts.
-61 prompt package tests pass. The scheduler-presentation tests exercise actual
  v2 profile selection and preserve frozen parameter rules for explicit scheduler
  off declarations.594 result-interpretation tests pass, including public cold-start
  calculation, existing producer reachability and optional analysis coverage.
- No API, training or GPU effects. Full-request hashes and normalized contracts
  are retained; matching transcript duplication is avoided.

## Source disposition and scheduler branch

The accepted-to-baseline rendering closure includes generated-name validation,
`ParameterRules` training-path membership and explicit-null preservation,
validator observed-output geometry, generated probe tests and cold-start helper
extraction. These are real execution/input-admission repairs, not mere file hashes.
The corpus covers admitted fixture inputs; it does not restore invalid old names,
invalid training paths or erroneous output-geometry acceptance. The final validator
system/user builders are unchanged before #848. The cold-start extraction retains
its original caller and optional analysis semantics, supported by the594 tests.
The subsequent1bd08066 native phase extraction is outside this rendering closure.

`_profile` selects the frozen proposer parameter-rule renderer when the assembly
is in `scheduler_disabled_assemblies`; late profiles then select the preserved
pre-scheduler native-training appendix. The accepted assembly already uses this
branch. Adding the new assembly to that same set preserves its selection, proven
by47 historical message pairs and the actual v2 scheduler-presentation tests.
This is presentation qualification, not a scheduler/runtime execution claim.

## Known unsupported whole-pair boundaries

Whole paper-pair readiness remains pending exp #276 and #277. With unchanged
planner0.12.2/runtime0.1.6 installed, the five ancillary
`planner_compat/tests/test_scheduler_manual_v11.py` cases fail before their
assertions: `legacy-345c802d-verifier-v1` refuses verifier assembly
`c3ce8d77c71616b046c2dbce1c33be5ba18c81bf481f73abc0fa35cabea05e5f`.
Initial missing-package attempts were setup failures; the installed-profile refusal
is the compatibility finding. No runtime qualification is added here. Frozen
message equality cannot establish complete conversation, future response,
training, timing-decision or artifact equivalence.

## Reproduction

Create the two exact infra checkouts above and run `uv sync --group dev --frozen`
in each. Install this standalone `experiments/shared/prompt_compat` package into
each interpreter normally. Do not borrow site-packages or use PYTHONPATH.
For each preserved `fixtures/*.json`, run the existing `capture.py` with that
checkout's `.venv/bin/python`, `--request`, a fresh `--output`, and the exact
`--expected-revision`. Native capture omits `--profile`; historical capture uses
`compare.PROFILES` task mappings with suffix-v2. Compare all47 system/user hashes
and then compare historical hashes to the unchanged registered-reuse receipt.
No new corpus runner is introduced.

Run `capture_requests.py --exp EXP --expected-exp-revision EXP_REV --expected-revision REV --output FRESH.json`
from this directory with each selected infra interpreter, once natively and once
with `--historical`. Compare complete `rows` for equality before summarizing hashes;
metadata revisions intentionally differ. This retained script contains all fixture
construction and records config/source hashes, normalized contracts and its own
SHA256. Run `check_installation.py --profile-version 2` with both interpreters.
Run prompt-package tests with `SIDERIUS_CHECKOUT` explicitly selecting the candidate,
and the candidate result-interpretation test directory. The separate runtime
refusal can be reproduced with the ancillary planner tests and unchanged installed
planner/runtime packages; it is expected to remain a blocker outside this PR.

The retained full-request comparator is `compare_requests.py`. Supply both captures,
expected infra revisions and a fresh output. It checks the exact16-case set,
normalized inputs and complete system/user text before recording hashes. Missing
cases, changed system/user text, changed contracts and wrong revisions were each
rejected by a mutation witness. Capture receipts now retain hashes of the profile
mapping, compositions, configs and original implementor fixtures, alongside the
helper hash and explicit exp worktree status. The current captures were produced
against701bb64 with only qualification-helper development changes recorded as
dirty; scientific inputs and installed package source were unchanged. This is
explicit candidate-tool provenance, not a clean-exp-head claim.

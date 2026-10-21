# Registered-model reuse qualification

## Qualified pair

Infra `4ec6c6968da61dc13a0d6d9acfa13fa56b53305b` permits documented same-name
registered model reuse while retaining generation-name collision protection.
Prompt package `0.10.17` admits that exact rendering assembly through existing
explicit v2 profiles. The current v2 overlay requires this version. Frozen
renderers, scientific inputs, archives, v1 selections, root pins and locks are
unchanged.

The collision check operates on the resolved, validated proposal before it
becomes a successful result. The pipeline retains its original duplicate-name
feedback text and retry limits. Previously rejected legitimate reuse now succeeds
intentionally; this qualification does not reproduce that erroneous control flow.
Legacy error wording changes without adding retries. Prompt templates themselves
are unchanged; broad name-guidance wording is outside this execution repair.

## Evidence and limits

The [receipt](receipt.json) records the clean candidate revision, installed profile
identities and capture tool identities. The frozen corpus compares all 47 existing
system/user message pairs to the unchanged historical hashes in the
[Luna-defaults receipt](../luna-defaults/receipt.json). The complete scripted
proposer comparator checks full strings against clean reference
`c7996a352d064229725ab1ebe886b9006bdbf36d`: 48 sequences / 156 requests match,
including duplicate-name correction feedback. Compact message-list digests avoid
publishing duplicated matching transcripts.

Installation/frozen-inventory checks pass, including refusal of four unknown
assemblies. The 66 prompt-package and scheduler-manual tests pass. Native infra
validation separately passes 816 proposer tests, covering registered reuse,
rejected generation/alias/phantom collisions and parameter-rule resolution in
both routes. No real API, training or GPU execution is part of qualification.

This establishes the recorded messages and tested request shapes, not arbitrary
additional parameter rules, complete historical conversations, identical future
LLM replies, rejected historical trajectories or retrained artifact equality.
The earlier qualification's explicit no-rule/scheduler-only scope still applies.
Historical rendering never bypasses the corrected live execution checks.

## Reproduction

Use a fresh workspace and the [current v2 overlay](../../profiles/paper-scheduler-disabled-v2.json).
Install its four standalone compatibility packages into the selected infra
checkout's own frozen environment. Do not rewrite existing locks or assume the
repository root pin selects this pair.

Follow the [existing capture procedure](../constraint-disclosure/report.md#reproduce-the-offline-checks)
using the candidate above, matching v2 profiles, unchanged fixtures and fresh
output paths. Compare the 47 receipts without normalization. Run
`compare_proposer_requests.py` with the candidate and reference, each using its
own environment; run `check_installation.py --profile-version 2`. Run the prompt
package tests and `planner_compat/tests/test_scheduler_manual_v11.py` with the
candidate Python and explicit `SIDERIUS_CHECKOUT`. The new receipt retains hashes
for each frozen pair and each scripted sequence; source tools remain unchanged.

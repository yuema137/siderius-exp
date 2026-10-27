# #923 human-advice scheduler-disabled qualification candidate

## Candidate pair

The candidate infra revision is `0c36aebc5d4359a872c61fc5f3cc099772dd2a43`; its rendering assembly digest is `61da42221d186bfff9efbb8c7343f7e20657c6c3cd39a6bfe6cfb0fa74895e57`. The exp base is the current master `416483b98f1dcc0860409b22c7fd894ef222cecf`, which already contains #287/#288 and its separately qualified `0.10.21` / `cfc7c822…` pair.

This candidate advances only `siderius-prompt-compat` to `0.10.22`, records the exact infra revision and assembly in qualification v2, adds that assembly to the existing scheduler-disabled classification, and updates the scheduler-disabled v2 profile's package requirement. It does not alter a renderer, archived template, v1 profile, infra pin/lock, task config, or prior receipt.

## Historical rendering boundary

The existing v2 renderer reads the archived proposal templates from its package. Its source inventory binds both files to infra revision `0ab1573602c708ddd182432ad4d0e43ae4828c53`; the installation check verifies the packaged template hashes against those historical source hashes. The new live human-advice templates therefore do not replace archived text in this profile. The 47 boundary comparisons below are the behavioral evidence for that distinction.

## Offline evidence

With package `0.10.21`, the exact `61da4222…` assembly was refused as unqualified. After installing the candidate package into the exact infra checkout's own frozen Python 3.12 environment, the existing tools reported **47/47 MATCH** frozen rendering boundaries and **4/4 MATCH** task groups covering **48/48 synthetic proposer sequences and 156/156 complete requests**. The installation check validated 20 installed source files and 16 frozen-source entries, returned all four v2 profiles for the exact candidate assembly, and exercised four unknown-assembly refusals.

The exact result payloads are retained in `boundary-comparison.json`, `proposer-comparison.json`, and `installation.json`. For this evidence export, machine-specific filesystem prefixes were replaced with stable task-relative archive/source identifiers; all message, source, and record digests and comparison statuses were retained. Original command logs and unredacted outputs remain local to the qualification worktree and are not part of this export. No provider, API, workflow execution, training, or GPU calls occurred.

This is an unpublished offline qualification candidate pending independent review. It supports only this exact infra/package pair and the stated offline rendering scope; it does not establish recovered full conversations, scientific execution, or stochastic artifact equivalence.

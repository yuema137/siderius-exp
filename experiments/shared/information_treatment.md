# Information-treatment contract

`information_treatment.py` validates the information that an experiment makes
available to an execution adapter. It does not define a scientific task or a
workflow.

The declaration has four authorities:

- `task_package`: one repository-relative static task root;
- `advice.mode`: explicit `enabled` or `disabled`;
- `advice.artifact` and `advice.sha256`: one immutable artifact when enabled,
  both null when disabled;
- `modules`: adapter-specific states that preserve `enabled`, `disabled`, and
  `not_applicable` as different meanings.

Resolution refuses absolute paths, paths that escape the repository, absent
task roots, missing or changed advice bytes, inconsistent advice fields, and
missing required adapter/module states. The resolver never interprets the
advice JSON keys. SIDERIUS remains the authority for its accepted advice
format and node routing.

The canonical receipt replaces repository paths with the bundle-local name
`advice.json`. It retains the manifest digest, advice digest or explicit
absence, adapter name, task-package declaration, and resolved module states.

# Information-treatment contract

`information_treatment.py` validates the information that an experiment makes
available to an execution adapter. It does not define a scientific task or a
workflow.

The declaration has five authorities:

- `treatment_id`: one stable arm identity recorded by every adapter;
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

Delivery depends on the adapter, not on a second content file. The SIDERIUS
adapter supplies the certified artifact to the framework, which validates and
routes its named sections to supported recipients. The coding-agent adapter
places the same whole artifact at `advice.json` for the product to read once.
The receipt records which adapter was used, so these delivery shapes are not
reported as identical workflow modules.

The canonical receipt replaces repository paths with the bundle-local name
`advice.json`. It retains the treatment ID, manifest digest, advice digest or
explicit absence, adapter name, task-package declaration, and resolved module
states.

# siderius-exp — entry point for coding agents

Read [`README.md`](README.md) before modifying this repository. In particular,
preserve the task/workflow/experiment/campaign ownership split and the
repository-identity rules documented there.

Before reporting where work lives, verify the current checkout with:

```bash
git rev-parse --show-toplevel
git rev-parse --git-common-dir
git branch --show-current
git remote get-url origin
```

A linked worktree under `/tmp` still belongs to the repository named by
`--git-common-dir`; its path is not its ownership. Real task and experiment
assets belong in `siderius-exp`, while generic framework mechanisms belong in
SIDERIUS. Raw datasets, workspaces, generated models, caches, and secrets stay
outside both repositories.

Use the exact SIDERIUS revision in `SIDERIUS_REVISION` and the checkout's own
`.venv/bin/python`. Do not borrow another checkout's virtual environment or use
`PYTHONPATH` to mix revisions.

For API-backed launches, follow the credential-preparation and secret-handling
boundary in [`README.md`](README.md#api-backed-launch-preparation), including
pre-effect failure for missing required keys and the distinction between key
presence and usable provider access. Preserve explicitly reviewed bindings;
clear only inherited conflicting overlays.

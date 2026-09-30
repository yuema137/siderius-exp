# siderius-exp Project Rules

## Documentation audience and review

This rule applies at every directory depth, including source, tests, examples,
deployments and archived documentation. Classify Markdown by filename,
case-insensitively:

- `README.md` files, Markdown files whose names contain `tutorial`, and
  tutorial Jupyter notebooks (`.ipynb`) are
  **human-facing**. Assume a technically literate reader who is new to this
  project. Lead with purpose and prerequisites, then give ordered steps,
  concrete commands, expected outputs and effects, and where to change inputs.
  Explain project-specific terms when they first matter; preserve exact CLI
  flags, filenames, schema fields and established technical terminology.
- All other Markdown files are **agent-facing technical references**. State
  scope, owners, interfaces, schemas, invariants, defaults, failure behavior,
  side effects, validation evidence and unresolved limitations as applicable.
  Use the same jargon and identifiers as the landed code. Be detailed and
  complete enough that an agent can implement or verify the contract without
  reconstructing missing decisions. Agent-facing does not mean opaque prose.

Every new or modified human-facing page must receive a readability and logic
review using the non-dialect parts of the
[DongbeiGPT skillset](https://github.com/yuema137/DongbeiGPT):
`clear-tech-explainer` for causal structure, `concrete-example` when a worked
trace helps, and `plain-chinese` for Chinese prose. Apply the clarity principles
to English pages without translating them or adding regional voice. Check
whether a new reader can identify what to do, in what order, which file owns
each choice, and how to recognize success. Simplification must preserve
technical conditions and distinctions.

For both audiences, compare behavior claims and commands against the exact
source revision and relevant tests: paths, flags, defaults, units, shapes,
parameter interactions, outputs and failure cases. Distinguish source review
from commands actually executed. A plan or old session is evidence of intent,
not proof of current behavior. Mark historical claims with their scope and
revision. Link to the owning contract instead of duplicating rules in README
files; keep each rule authoritative in one place.

Apply this review whenever a page is created or changed; this does not require
an unrelated repository-wide rewrite. Explicitly requested human reading
mirrors remain reading aids for the authoritative source, not separate rule
owners.

Public installation/download examples and current repository entry links use
`yuema137/SIDERIUS` and `yuema137/siderius-exp`. Development PRs remain in
Galileo-Sandbox. Preserve historical issue/PR evidence links at their actual
origin; changing documentation links does not authorize publishing or syncing
a release.

## Repository and scientific ownership

Before reporting where work lives, verify the current checkout:

```bash
git rev-parse --show-toplevel
git rev-parse --git-common-dir
git branch --show-current
git remote get-url origin
```

A linked worktree under `/tmp` belongs to the repository identified by
`--git-common-dir`; its path is not its ownership. Real task and experiment
assets belong in siderius-exp; generic framework mechanisms belong in SIDERIUS.

- `tasks/` owns scientific meaning, data identity, splits, plugins, model I/O,
  metrics and validity rules.
- The workflow owns execution and Trial/Formal progression. `experiments/`
  binds a task and workflow to concrete parameters, advice, budgets and result
  identity.
- `campaigns/` owns authorization and coordination across units.
  `deployments/` owns machine and scheduler setup.
- Raw datasets, workspaces, generated models, caches and secrets remain outside
  both repositories.

Preserve frozen scientific identities. Changed treatments need new identities;
historical records are evidence, not launch authorization.

## Environment and launch credentials

Run `uv sync --group dev --frozen` in the exact checkout and use its own
`.venv/bin/python`. Use the exact SIDERIUS revision in `SIDERIUS_REVISION`,
consistent with `pyproject.toml` and `uv.lock`. Historical launchers with a
separate pin retain their own revision. Do not borrow another checkout's
virtualenv or editable install, or mix source revisions through `PYTHONPATH`.

Before each API-backed launch, inject the enabled providers' required keys from
a trusted mode-600 external credential file or managed secret into the launching
process. Perform a name-only presence check before effects. Never print, log,
commit or upload values. Key presence is not proof of working provider access.
A checkout `.env` compatibility loader is not a substitute for an explicit
launch-process binding. Preserve explicitly reviewed bindings; clear only
inherited conflicting overlays. Follow the selected launcher's actual checks.

## Development and publication

Continue development and review in Galileo-Sandbox. Synchronize to yuema137
only for a stable release selected by the operator.


## Paper tutorial ownership

For notebook/task/experiment/launch responsibilities, follow the owning
[tutorial support contract](tutorials/paper/implementation.md#tutorial-responsibility-boundary).
Keep training/execution owned by the saved scripts. The Run All quick-demo
cell may explicitly invoke its saved script (operator-requested onboarding
route); notebook cells must not reimplement training or construct provider calls.
Disclose API/GPU effects before the cell and reuse completed runs without
silently relaunching them.

Tutorial users edit only their initialized external project: copied notebooks,
tasks, experiment JSON, LLM routing and generated scripts. Never prescribe
changes to tracked repository templates as a tutorial step. Distinguish that
project root from each fresh run's output workspace. Advice activation must be
explicitly supported by the selected treatment; an example file is not active.

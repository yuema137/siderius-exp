# Historical planner compatibility package

This package preserves the planner strategies removed from SIDERIUS framework
source. Installing it declares an installation default, so an existing caller
that omits a strategy can retain the historical planner prompt behavior.

Offline checks verify that this package preserves the historical planner text
for the covered inputs. Twelve cases cover the current historical prompts,
including the agent-owned Formal training appendix; six cover the older prompts
with an empty loss registry. The [paper verification report](paper-parity.md)
adds LIGO startup and shared-branch comparisons for the four paper tasks. The
[controlled TESS comparison](../../phyts_tess/planner_strategy_comparison_372/report.md)
is complete; it does not claim improved scientific performance.

This package alone does not reproduce a paper result or migrate an existing
workspace. Historical model/history import and non-empty older loss registries
remain unqualified. Follow the workspace rules below rather than resuming an old
run under a guessed strategy.

The historical loss-search and recovery wording is also archived here. Ten
additional offline cases check that moving this helper preserves final prompts
for free loss choices and task-locked builtin/custom objectives. Infra no longer
owns that historical strategy text.

## Install into the environment that will run infra

Use the infra checkout for the paired issue #372 change. A released infra
revision without `agent.planner_strategy` cannot load this package. First
create that checkout's own environment using its installation instructions.
Then install this directory into that environment:

```bash
# Replace both paths with your checkouts; no credentials are needed here.
INFRA_CHECKOUT=/absolute/path/to/SIDERIUS
EXP_CHECKOUT=/absolute/path/to/siderius-exp
uv pip install --python "$INFRA_CHECKOUT/.venv/bin/python" --no-deps \
  "$EXP_CHECKOUT/experiments/shared/planner_compat"
```

Use a normal installation for a run whose identity must remain fixed. Do not
edit the package during execution. Both repositories' public download locations
are [yuema137/SIDERIUS](https://github.com/yuema137/SIDERIUS) and
[yuema137/siderius-exp](https://github.com/yuema137/siderius-exp); the paired
change must be merged and synchronized before those paths include this API.

Inspect the selected identity without calling an LLM:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -c \
  'from agent.planner_strategy import resolve_planner_strategy; print(resolve_planner_strategy(None).identity.model_dump_json(indent=2))'
```

The declared default is `legacy-9b78d505cb11-v1`. A missing package or multiple
installed defaults produces an explicit error. Infra never guesses which
historical experiment you intended.

## Select a strategy for a new experiment

In your workspace's LLM configuration, add the selector to the existing `tune`
object and keep its planner/reflector model settings:

```json
{
  "tune": {
    "planner_strategy": "legacy-9b78d505cb11-v1",
    "planner": {"provider": "openai", "model_id": "YOUR_MODEL_ID"},
    "reflector": {"provider": "openai", "model_id": "YOUR_MODEL_ID"}
  }
}
```

Run your existing experiment script with this LLM configuration. The standalone
infra tuner also accepts `--planner_strategy legacy-9b78d505cb11-v1`.
An explicit choice overrides the installation default. `native-timing-v1`
selects the new timing-aware planner and changes the treatment; it is not the
historical fallback.

The additional `legacy-691617f04b42-v1` source variant is preserved for the older
Majorana/SuperNEMO records. Six synthetic cases match its original assembled
prompts, but the historical runs themselves are not yet qualified. Its API adapter currently
supports an absent or verified-empty custom-loss inventory only; non-empty or
unavailable inventory information refuses explicitly. It also refuses new
agent-owned Formal training and independent epoch-validation scopes, which
were absent from its original planning path. No loss information is silently
dropped to make the old call signature work. Do not substitute it into a
historical run and report successful replay.

## Keep old results intact

Do not edit an old `run_invariants_lock.json` to make a new run start. A lock
without a strategy identity cannot prove which installed plugin it used. The
new framework refuses that resume rather than filling in a guess.

Keep the original workspace and receipts. A verified migration must create a
new workspace, bind the historical provider explicitly, and retain a separate
record linking to the old evidence. The migration procedure is not automated
by this package yet. If provenance cannot be verified, use the old infra
revision for that run. SuperNEMO's missing workspace is an acknowledged exception;
it will be rerun separately and is not part of the paper models.

Scientific experiments are checked individually before migration. Internal
framework tests keep their original code revision and records; this work does
not adapt those old tests to new plugins. The [migration contract](migration.md)
lists the evidence required before a scientific migration can be called verified.

`source_manifest.json` records the original prompt source revisions and hashes.
The archived modules remain byte-identical to those sources. Preserving source,
matching final prompts, replaying archived responses, and obtaining the same
score from a fresh stochastic run are different checks; only report the checks
actually completed.

## Check the installed package without an API call

From the same infra environment used above:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -m siderius_planner_compat.self_check
```

Success reports 12 current, six early and ten composed-loss matching prompt pairs,
two early empty-registry
boundary cases, and refusal of uncertain registry information before any provider
call. The recorded reference digests came from the original infra checkout,
not from the new renderer. All clients are blocked from network access. These
checks use synthetic inputs; the early comparisons cover an empty registry only
and do not establish scientific replay.

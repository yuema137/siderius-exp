# Choose LLM settings for the job

Start with a small process demo. Confirm that configuration, training, scoring
and saved results work before paying for a larger research search. A good score
is not the acceptance criterion for this first run.

| Level | Purpose | Configuration |
|---|---|---|
| Offline checks | Inspect files, credentials by name, resolved settings and launch commands | Preview only; no LLM call and no proof of model access |
| Functional demo | Exercise the complete process on a small dataset | The [GPT-6 Luna test profile](openai_smoke_luna.json), copied into each new project's `llm/agents.json` |
| Production / research run | Investigate your task after the process works | Start with the paper's LLM routing below; choose run size and API budgets separately |
| Custom routing | Use your preferred supported providers and models | Edit the individual routes in your external project's `llm/agents.json`, then preview and test them |
| Paper replay | Recover a recorded experiment's declared treatment | Follow the [paper artifact reference](../../experiments/paper-artifacts.md) and its historical configurations; never use these as smoke-test defaults |

## Move from a demo to research

**Luna is the inexpensive testing configuration. For production research, we
recommend the paper's LLM configuration as a starting point.** You can use
your own supported providers and models instead. Neither choice guarantees
the paper's scores on your task.

Inspect the paper task's routing file before editing your external project:

- [TESS agent routes](../../experiments/phyts_tess/main_fixed_workflow/agents.json)
- [LIGO agent routes](../../experiments/phyts_ligo/main_fixed_workflow/agents.json)
- [Project8 agent routes](../../experiments/phyts_project8/main_fixed_workflow_dual_representation/agents.json)
- [TIDMAD experiment and treatment choices](../../experiments/tidmad/main_fixed_workflow/README.md)

The linked TESS, LIGO, and Project8 files specify `gpt-5.6-sol` with `medium`
reasoning across their workflow routes. TIDMAD has multiple treatments; choose
the intended experiment rather than assuming one configuration covers them all.
These are recorded model choices; verify current model access with your provider.

In your project's `llm/agents.json`, set `provider`, `model_id`, and
`reasoning_effort` for each route you want to change, including the three
proposal stages and the planner/reflector. Review optional analysis and literature
routes too. Keep retries and run budgets explicit; changing models can increase
API costs. Run the saved script's preview, check the resolved routes and required
key names, then do a small real run before increasing the workload.

**Model choice and historical replay are separate.** For a new research run,
keep the project's intended planner and runtime policies; do not copy historical
compatibility selectors just to use the paper's models. Reproducing a recorded
treatment additionally requires its source/configuration pair and explicit
historical settings, as described in the artifact reference above.

Before paid execution, follow the [hardware check guide](hardware/README.md) for
your saved experiment. It covers GPU readiness and each tutorial's data/RAM/storage
considerations; choosing a cheaper LLM does not reduce GPU requirements.

## What a fresh tutorial selects

All nine [tutorial tasks](../README.md) use the same independent test template,
including the supplementary MJD, SuperNEMO, Cancer and DAVIS entrypoints.
Every configured workflow route uses OpenAI `gpt-6-luna` with `medium` reasoning:
interpretation, Data Analysis, all three proposer stages, implementation,
validation, tuning's planner and reflector, and both literature-review routes.
An explicitly configured optional route stays disabled until the workflow enables
it. Configuring its model does not activate it.

The planner selects infra's built-in `native-timing-v1`. No paper prompt plugin is
needed. Your initializer saves the JSON in your external project, alongside the
task and experiment files; it refuses to replace an existing project. Inspect
that saved JSON before launching. Existing projects keep their current routing.
To adopt this template, create a fresh project and transfer your intended edits.

## Keep a demo small

Model selection and run size are separate controls. Change iterations, dataset
fractions, attempts and training budgets in the saved experiment using your
notebook's examples. Run the script's preview first. Starting the actual script
or a notebook's live-demo cell makes paid API calls and performs training.

Every route sets `max_retries: 1`: one initial attempt for transient provider
status errors such as 429 or 503, with no extra status-error retry. Tuning's
reflector and literature search keep their own limits. Timeouts, invalid-output
repair and failed workflow rounds are separate controls. This JSON sets no dollar
ceiling or output-token limit and does not bound the total number of calls.
Do not treat choosing Luna as permission for unbounded retries.

An external agent driving orchestration has its own model setting. Set that
runner to GPT-6 Luna too if you want an entirely Luna-based test; `llm/agents.json`
controls only workflow calls. Optional setup-review tooling likewise uses its
own reviewer configuration.

Offline routing checks validate configuration; they do not prove provider access.
Separate real Luna-medium runs are recorded for [MJD](../supplementary/mjd/example/README.md),
[SuperNEMO](../supplementary/supernemo/example/README.md),
[Cancer](../supplementary/cancer/example/README.md) and
[DAVIS](../supplementary/davis/example/README.md). Their receipts identify the
source pair, data, hardware, costs and actual outcomes, including failures.
That evidence does not qualify every task, GPU or generated model.

The four paper-task galleries and Pet retain their earlier model/source identities;
they are not new Luna qualifications. None of these examples promises your score.
See the [technical contract](llm-profile.md) for verification ownership.

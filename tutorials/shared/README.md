# Choose LLM settings for the job

Start with a small process demo. Confirm that configuration, training, scoring
and saved results work before paying for a larger research search. A good score
is not the acceptance criterion for this first run.

| Level | Purpose | Configuration |
|---|---|---|
| Offline checks | Inspect files, credentials by name, resolved settings and launch commands | Preview only; no LLM call and no proof of model access |
| Functional demo | Exercise the complete process on a small dataset | The [GPT-6 Luna test profile](openai_smoke_luna.json), copied into each new project's `llm/agents.json` |
| Research run | Investigate your task after the process works | Deliberately edit provider/model choices in your external project's `llm/agents.json`; choose effort and budgets separately |
| Paper replay | Recover a recorded experiment's declared treatment | Follow the [paper artifact reference](../../experiments/paper-artifacts.md) and its historical configurations; never use these as smoke-test defaults |

## What a fresh tutorial selects

TESS, TIDMAD, Project8, LIGO and Pet use the same independent test template.
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

The template has offline routing checks; **a successful live Luna run has not yet
been established by those checks**. Archived notebook pictures and scores remain
from their original recorded runs and model choices. They demonstrate the process,
not the results you will obtain from this profile. See the
[technical contract](llm-profile.md) for verification and ownership details.

# Tutorial LLM profile contract

## Ownership and activation

`openai_smoke_luna.json` is the standalone recommendation for new tutorial projects.
It is not derived from `experiments/`, does not change infra defaults, and does
not install an implicit historical strategy. `llm_setup.write_test_llm_config`
validates it with the installed `WorkflowLLMConfig` then uses exclusive creation.
All five initializers refuse existing project roots before copying files.

The source records eleven routes explicitly: four single-call slots (`interpret`,
`data_analysis`, `implement`, `validate`), three proposer slots, two tuner slots
and two literature-review slots. Every route uses OpenAI `gpt-6-luna`, reasoning
`medium`. Tuning explicitly selects `native-timing-v1`. No unknown output-token
or budget fields are inserted into the JSON.

## Limits and boundaries

`max_retries=1` is requested where the current workflow projects it. Tuner retry
configuration comes from its planner and applies to the shared bridge. The
literature owner does not forward leaf retry settings, so those fields are
absent; no uniform retry-cap guarantee is made. Invalid-output repair and workflow
round/attempt controls are distinct from transient provider retries. The profile
is neither a campaign spending guard nor a training/workflow budget.

Optional workflow stages remain controlled by experiment settings. External
orchestration and optional setup-review models are separate configuration owners.
The shared planner preflight still compares the actual selected implementation
across the exp and infra environments; native selection needs no exp historical
plugin installation. Existing external files and all historical experiment
routing remain unchanged.

## Evidence and documentation

Offline tests use the actual installed workflow schema and its node projection,
exercise all five new external project initializers, and reject overwrite attempts.
These tests do not call providers, prove account/model access, train, or establish
score quality. Existing gallery images, notebook outputs and provenance retain
their original identity; introductory Markdown labels them as earlier runs.
The top-level tutorial guide owns navigation; README.md here owns configuration
level recommendations; task guides own their launch and parameter instructions.

# Tutorial LLM profile contract

## Ownership and activation

`openai_smoke_luna.json` is the standalone recommendation for new tutorial projects.
It is not derived from `experiments/`, does not change infra defaults, and does
not install an implicit historical strategy. `llm_setup.write_test_llm_config`
validates it with the installed `WorkflowLLMConfig` then uses exclusive creation.
All tutorial initializers refuse existing project roots before copying files.
Eight initializer modules serve nine tasks: Project8 and LIGO share one module.

The source records eleven routes explicitly: four single-call slots (`interpret`,
`data_analysis`, `implement`, `validate`), three proposer slots, two tuner slots
and two literature-review slots. Every route uses OpenAI `gpt-6-luna`, reasoning
`medium`. Tuning explicitly selects `native-timing-v1`. No unknown output-token
or budget fields are inserted into the JSON.

## Limits and boundaries

Every route explicitly sets `max_retries=1`, meaning one initial attempt and no
additional retry for transient provider status errors. The tuner reflector and
literature search receive their own typed retry policies through the workflow;
they do not silently inherit a different route's explicit limit. Timeout retries,
invalid-output repair and workflow round/attempt controls are distinct. The profile
is neither a campaign spending guard nor a training/workflow budget.

Optional workflow stages remain controlled by experiment settings. External
orchestration and optional setup-review models are separate configuration owners.
The shared planner preflight still compares the actual selected implementation
across the exp and infra environments; native selection needs no exp historical
plugin installation. Existing external files and all historical experiment
routing remain unchanged.

## Evidence and documentation

`tests/tutorials/test_planner_setup.py` uses the actual installed workflow schema
and node projection and parameterizes the original five task cases: TESS, TIDMAD,
Project8, LIGO and Pet. It verifies routing and overwrite refusal; it is not a
nine-task live test. MJD, SuperNEMO, Cancer and DAVIS also have their owning
initializer/runtime tests. Offline tests do not contact providers, establish
account/model access, train or establish score quality.

Separate Luna-medium live witnesses are recorded in the supplementary MJD,
SuperNEMO, Cancer and DAVIS `example/provenance.json` receipts and explained by
their example READMEs. These qualify their recorded source/data/hardware sequence,
not every task or hardware combination. Earlier paper-task and Pet galleries
retain their original model/source identity and must not be relabeled as Luna.
All recorded images, outputs and provenance remain unchanged by this guide.
The top-level tutorial guide owns navigation; README.md here owns configuration
level recommendations; task guides own their launch and parameter instructions.

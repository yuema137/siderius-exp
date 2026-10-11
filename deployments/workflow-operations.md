# Fixed-workflow deployment contract

## Scope and owners

Use an existing task/experiment launcher when its declared treatment matches
the requested experiment. A profile for another task or data split is not an
interchangeable launcher. An external experiment may instead supply its reviewed
arguments directly to the selected framework's `scripts/launch/run_chain.sh`.

| Responsibility | Owner |
| --- | --- |
| Task, data split, metrics, model interface and validity | Task package |
| Model routing, advice, budgets and experiment identity | Experiment configuration |
| Iteration loop, child argv, native resume and graceful STOP | Framework `scripts/launch/run_chain.sh` |
| Provider invocation, routing and native usage records | Framework `agent.LLMBridge` |
| GPU policy validation, identity and execution | Framework `GpuExecutionPolicy` and native execution owners |
| Host credentials, isolation, service lifecycle and any separately authorized campaign limits | Selected deployment |
| Private-label evaluation | Selected task's isolated scorer, when required |

Do not source `_chain_common.sh` and replace `submit_iteration` to work around a
missing public option. Confirm the gap against the selected framework revision,
file an issue in its development repository, and repair the public entrypoint.
Do not add a second provider client or accounting system merely to start a run.

The deployment must record exact framework and experiment revisions. Build each
selected checkout's own frozen environment; use its existing source/pin checks.
This contract does not change `SIDERIUS_REVISION`, experiment-specific pins or
paper compatibility profiles.

## Native invocation

A saved script passes the existing experiment's arguments to the native chain:

```bash
bash "$SIDERIUS_CHECKOUT/scripts/launch/run_chain.sh" \
  --mode lilab \
  --workspace "$WORKSPACE" \
  --run_name "$RUN_NAME" \
  --task_composition "$TASK_COMPOSITION" \
  --data_dir "$DATA_DIR" \
  --llm_config "$LLM_CONFIG" \
  --num_iterations "$NUM_ITERATIONS" \
  "${EXPERIMENT_ARGS[@]}"
```

All variables and the `EXPERIMENT_ARGS` Bash array are explicit deployment inputs.
The array contains the reviewed scientific settings; it must not contain
conflicting copies of the named arguments. Use absolute paths for external
inputs because the native launcher executes from its framework checkout.
Run the same command with `--dry-run` to inspect child commands before effects.
Dry-run does not prove data, credentials or GPU availability.

The optional `--gpu_execution_policy_json FILE` is available on the chain at
framework revision `19aaf53143ced3e76439e0cfd3e37506916af8e7` and descendants
retaining that interface. The file is parsed by the native Python owner; the
shell only transports its path. An older experiment pin is not silently upgraded
by this guide. Do not invent hardware-specific fallback values when an option
or required policy is unavailable.

## Credential and service boundaries

Derive provider requirements from the enabled workflow configuration using the
[credential contract](../experiments/shared/workflow_credentials.md). Keep real
keys outside source, run artifacts and logs. Inject them only into the reviewed
process boundary. Passing a real key to a workflow process does not by itself
hide it from generated child code.

A separately reviewed deployment may retain a host-side credential relay or
private scorer. Reusing the native chain does not establish that these services
are unnecessary. Preserve their access boundaries during migration. Conversely,
a privileged training/admission service is not automatically an API relay.

The framework sandbox command builder can supply isolation to an external
supervisor. Its full runner also owns a timeout and process lifecycle; replacing
an existing supervisor with it requires checking those semantics. Do not add an
unrequested whole-campaign timeout when the declared campaign is uncapped.

## Failure evidence and accounting

An external relay adds a failure boundary and must be qualified as such. It must
retain sanitized failure stage, time, exception class, HTTP status and available
provider/client request identifiers. Preserve received responses before local
accounting validation can reject them. Receipts stay in protected operator
storage; never publish credentials, arbitrary headers or private experiment data.

Keep the original failure distinguishable from a later logging or delivery
failure. Unknown usage remains explicitly uncertain, not zero or fabricated
spend. A lost successful response must not silently trigger duplicate paid
requests; preserve known usage and reconcile before resending. A fresh accounting
segment references immutable prior ledgers and carries their uncertainty forward.

Before relying on an external relay, exercise HTTP/transport errors, malformed
responses, missing usage, receipt-write failure and downstream disconnect with
synthetic responses. Successful experiments alone do not validate these cases.
These are deployment requirements, not a claim that this repository ships such
a relay. Native exception propagation and native usage records remain their
framework owners' responsibilities.

## Resume after a deployment change

1. Request a graceful stop through the native `$WORKSPACE/STOP` file. It stops
   the chain after the current iteration; do not kill a paid request to replace
   its launcher. This procedure is for the foreground `lilab` chain. Slurm jobs
   are submitted ahead of execution and require scheduler-specific coordination.
2. Confirm the previous chain and owned service processes have exited. Inspect
   `chain_stopped.json`, completed manifests and the native read-only inspector:

   ```bash
   "$SIDERIUS_CHECKOUT/.venv/bin/python" \
     "$SIDERIUS_CHECKOUT/scripts/launch/inspect_run_state.py" \
     --layout chain --workspace "$WORKSPACE" --next-iter
   ```

   Require a successful exit and the expected next iteration. A partial iteration
   is not a clean boundary merely because the inspector identifies its number.
3. Verify unchanged task/config/policy identities and compatible source changes.
   Native invariant checks must still pass. Do not alter historical manifests,
   prompts, model files or locks to force a match.
4. At a clean compatible boundary, retain the same workspace. Archive the
   graceful-stop request and report as operator evidence before deliberately
   removing the active `STOP`; never blindly clear `.chain_halted`. Keep completed
   evidence read-only to generated code where the deployment supports it.
5. Reuse the native command with `--auto_resume`. Remove stale manual
   `--start_iter` and `--no_auto_resume` overrides. Preview the command, verify
   isolation and source binding, then start the separately recorded deployment
   segment. Confirm the expected iteration starts and prior iterations are not
   executed again.

If the source change is incompatible or the prior iteration is incomplete,
preserve the old workspace and choose an explicit reviewed recovery procedure.
Do not copy partial artifacts or force a fresh start over existing history.
Paper-specific historical behavior stays in experiment-owned profiles and pins.

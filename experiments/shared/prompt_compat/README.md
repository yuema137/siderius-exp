# Historical information-flow checks

This directory is being developed to compare paper-era messages with explicit
historical profiles. It is not yet a complete full-workflow compatibility package.
The existing planner-only checks remain in [planner_compat](../planner_compat/README.md).

## Explicit recovery policy

The profile [analysis-c0467447-recovery-v1.json](profiles/analysis-c0467447-recovery-v1.json)
preserves the recovery allowances in infra revision
`c046744712fabfbd09c5c5a51a84fb30073d59e3`, used by the archived native
TIDMAD analysis-on run:

- After generated-program validation and one representation repair fail,
  stop that preparation attempt: `generated_program_retries: 0`.
- Analysis-plan preparation retains its existing shared fresh-attempt
  allowance: `plan_retries: 1`.

Do not apply this profile to every historical experiment. It is qualified for
that source revision, and it does not restore historical prompt text by itself.

With the accompanying infra changes, copy the profile object into the
`recovery_policy` field of your external analysis-policy YAML, or supply it
in a standalone `DataAnalysisInput`. Use a new workspace. The policy enters
run identity; old archived policy files and workspaces must remain unchanged.
Omitting the field retains current behavior: one additional attempt at each
stage. Counts mean additional attempts, excluding the initial attempt and
its representation-only repair. Validation, access checks, provider-error
handling, and the original request deadline remain enforced.

## Offline failure-branch comparison

`replay_generated_failure.py` consumes a hash-verified archived receipt and
its neighboring `input.json`. It routes the two saved replies through the
actual preparation and validation code, and stops at any additional request
for which no archived reply exists. It does not execute generated programs.

Run with the selected infra checkout's own frozen environment:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/replay_generated_failure.py" \
  --archive "$ARCHIVED_ANALYSIS_DIRECTORY" \
  --receipt-sha256 "$VERIFIED_RECEIPT_SHA256" \
  --recovery-policy "$EXP_CHECKOUT/experiments/shared/prompt_compat/profiles/analysis-c0467447-recovery-v1.json" \
  --output "$NEW_OUTPUT_DIRECTORY"
```

For an original checkout that predates the policy field, omit
`--recovery-policy`. Also omit it when checking the current default. Output
must be a new directory. Inspect `result.json` for the revision, input and
policy hashes, request sequence, message hashes, and observed termination.
Messages are saved separately in `messages.json` for local inspection.

The archived band 4–9, iteration 9 witness produces two requests followed by
failure under the original revision. The current default requests an
additional generation. Explicitly selecting this profile restores the two
request sequence and failure boundary while still rejecting both invalid
drafts. System-message differences remain to be handled by rendering profiles;
matching this sequence is not a claim of complete prompt parity.

`capture.py` separately captures declared rendering boundaries from explicit
reconstructed inputs. Its receipts distinguish renderer comparison from an
archived conversation. Neither tool calls an API, trains, downloads a dataset,
or proves equality of stochastic outputs or paper scores.

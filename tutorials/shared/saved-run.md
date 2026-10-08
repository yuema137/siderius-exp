# Saved-script delegation contract

`shared.saved_run.run_saved_script` owns the notebook-side lifecycle used by
`pet.demo.run_demo`: completed-result reuse, exclusive console-log creation,
launching `bash <script> --launch` in a new session, waiting, interruption cleanup
and completion persistence. Its explicit inputs are `script`, `workspace`,
`digest`, zero-argument `ready` callback and `timeout_seconds`. It has no task or
timeout default. Task adapters own validated settings, path restrictions, digest
input closure, credential policy and public defaults. Pet keeps its 3600-second
notebook timeout and validates settings and launcher before calculating the digest.

This is the existing Pet lifecycle, not the paper tutorials' v2 identity policy.
The helper does not validate configuration, inspect data, calculate provenance,
revalidate inputs after launch or supply task dispatch. A supplied digest is a
caller-owned identity, not evidence of replay or raw-dataset content identity.

## Ordering and persisted interface

- Receipt path is `workspace.with_suffix(".notebook-run.json")`; log path is
  `workspace.with_suffix(".console.log")`.
- Existing receipt is decoded as JSON. Check digest equality, workspace directory
  existence, then zero exit code, in that order. Return the original decoded
  result unchanged. No readiness call or launch occurs on reuse or refusal.
- Without a receipt, refuse an existing workspace or log. Call `ready()` before
  creating parent directories or the log. Callback failures leave no new log.
- Open the log exclusively and start the saved shell with combined stdout/stderr.
  Wait in intervals capped at 30 seconds, subject to the caller's timeout.
- On timeout or another `BaseException`, capture recursive descendants before
  terminating the process group and descendants. Wait up to five seconds for
  descendants, kill survivors, then wait up to five seconds for the parent and
  escalate its group if necessary. Re-raise the original exception; retain the
  log without writing a completion receipt. This preserves existing supervision,
  including its race/error limitations; it is not an API/GPU accounting guard.
- A returned process exit writes an exclusive JSON receipt with the existing keys
  `input_sha256`, `exit_code`, `elapsed_seconds`, `workspace`, `log`. A nonzero exit
  is recorded before raising; a later call refuses that result. No automatic retry
  or cleanup occurs. Malformed/incomplete receipts retain the existing JSON/key
  failure behavior.

## Generated launcher binding

`shared.saved_script.write_launcher` and `validate_launcher` take explicit
`checkout` and `runner_module` parameters. The writer preserves the existing Pet
shell bytes when called with Pet's module and checkout, including the setup guard,
interpreter, exclusive write and executable mode. Its callers supply trusted
module identifiers and absolute checkout paths. The validator requires exactly
one literal absolute `EXPERIMENT` and `EXP_CHECKOUT` binding matching the selected
paths, then the generated runner exec line. It is a handoff check, not a shell
security parser. Pet retains its public two-path wrappers.

The runner mismatch diagnostic now says “selected tutorial runner” rather than
“Pet tutorial runner”; its `ValueError` type and check order are unchanged.
No notebook, archived output, scientific declaration or runtime prompt changes.

Validation: `test_saved_run` exercises the Pet wrapper's actual delegation order,
success/nonzero receipt reuse, refusal without effects, interrupt escalation and
an alternate runner binding. Existing Pet tests retain the real detached-worker
timeout witness and saved-config/script mismatch coverage; the offline notebook
uses synthetic JPEGs and native-schema score fixtures, never scientific evidence.

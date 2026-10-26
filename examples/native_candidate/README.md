# Open a real task in code and the GUI

Inspect a copied TESS task, explicitly accept its checked current snapshot, then
edit one ordinary `workflow.py` through your coding agent or the console. Prepare
that same saved source before deciding whether to launch a candidate.

This first example runs **Propose → Implement → Validate**. It has no training
or scientific score. You need Linux, working bubblewrap/user namespaces, prepared
TESS data and an already available reviewed framework checkout matching the
[TESS profile](tess/profile.json). This is a development example; public release
installation is separate. Existing tutorial environment pins stay unchanged.

## 1. Prepare data and copy the project

Start with the [TESS data steps](tess/README.md). Select the reviewed example
commit in your exp checkout, then replace these absolute paths with your own:

```bash
export INFRA_CHECKOUT="/absolute/path/to/reviewed-SIDERIUS"
export EXP_CHECKOUT="/absolute/path/to/siderius-exp-with-this-example"
export PROJECT="/absolute/path/to/new-tess-candidate-project"
export TESS_DATA="/absolute/path/to/prepared-tess-data"
(cd "$INFRA_CHECKOUT" && uv sync --group dev --frozen)
export INFRA_PYTHON="$INFRA_CHECKOUT/.venv/bin/python"
mkdir "$PROJECT"
set -o pipefail
git -C "$EXP_CHECKOUT" archive HEAD examples/native_candidate tasks/phyts_tess |
  tar -x -C "$PROJECT"
cd "$PROJECT"
```

The project and data stay outside both repositories. Run the copied recipe with
the framework's own Python; this route needs no exp environment or `PYTHONPATH`.

## 2. Inspect, then accept the task

```bash
"$INFRA_PYTHON" examples/native_candidate/materialize.py inspect \
  --project "$PROJECT" --data "$TESS_DATA" --framework "$INFRA_CHECKOUT" \
  --profile examples/native_candidate/tess/profile.json \
  --output "$PROJECT/inspections/task-001.json"
```

Expect `Inspected, NOT accepted` and `r2 (higher is better)`. This saves model
routing, inspection scratch files and a report; it calls no provider. Read the
report's task description, model I/O, metrics, split references and limitations.
It checks composition, not dataset correctness. Failed checks need fresh report
paths after you fix their inputs.

Create a private provider file **outside the project and repositories**. Empty
JSON supports offline preparation and leaves candidate Launch blocked:

```bash
export PROVIDER_CREDENTIALS="/absolute/private/tess-provider-credentials.json"
"$INFRA_PYTHON" - "$PROVIDER_CREDENTIALS" <<'PY'
import os, sys
with os.fdopen(os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
    stream.write('{}\n')
PY
"$INFRA_PYTHON" examples/native_candidate/materialize.py accept \
  --inspection "$PROJECT/inspections/task-001.json" \
  --credential-file "$PROVIDER_CREDENTIALS" --port 8740 --accept-task
```

Use `--accept-task` only after reading the task facts. It rechecks them before
writing `workflow.py`, `console.json`, `prepare-request.json`, `console-token`
and separate run/recovery directories. Existing outputs refuse; provider values
are never copied into the project.

## 3. Edit the same file in code and the browser

```bash
"$INFRA_PYTHON" -m tools.candidate_console check --config "$PROJECT/console.json"
"$INFRA_PYTHON" -m tools.candidate_console serve --config "$PROJECT/console.json"
```

Keep the server running. Open `http://127.0.0.1:8740/#workflow`, connect using
`console-token` and select TESS. For remote access follow the
[console SSH-tunnel steps](https://github.com/Galileo-Sandbox/SIDERIUS/blob/master/src/tools/candidate_console/README.md#set-up-and-open-the-console).

Your coding agent and the graph both use `workflow.py`. After a code edit,
**Refresh from disk**. For a browser edit, change a supported field or advanced
source, select the saved task's configured choice, **Review changes**, read the
Python diff and task findings, acknowledge them and **Save reviewed source**.
Saving does not execute anything.

## 4. Prepare, then decide whether to launch

In **New run**, choose TESS and a fresh run name, **Review preparation**, then
**Prepare saved source**. Expect **prepared** and `runs/<run UUID>/inputs/`;
`workspace/` remains absent. **Open prepared run** to inspect the capture.

The original saved source also has a direct native CLI request:

```bash
"$INFRA_PYTHON" -m tools.candidate_prepare \
  --reusable-request "$PROJECT/prepare-request.json"
```

That request refuses after source edits or reuse. After editing, use **New run**
or create a fresh typed request through the
[reusable preparation API](https://github.com/Galileo-Sandbox/SIDERIUS/blob/master/src/tools/candidate_prepare/candidate-prepare-contract.md).
Preserve old inputs and results.

**Review capture** reports the missing `OPENAI_API_KEY` from the empty private
file. For intentional paid execution, update that file using the
[private credential recipe](example-contract.md#provider-file), then review again.
**Launch captured run** uses the
[existing native operation](https://github.com/Galileo-Sandbox/SIDERIUS/blob/master/src/tools/candidate_operations/README.md)
and may spend API credits and execute generated code. Its 600-second timeout is
not a billing cap; no GPU devices are exposed. Set your own spending controls.
Inspect native validation and reported tokens in Slow control; completion alone
does not certify a model. The example's qualification never presses Launch.

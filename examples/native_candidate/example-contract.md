# Native candidate example contract

Scope: external asset materialization and checked-current-snapshot acceptance,
then native three-stage reusable preparation/execution. First task is TESS.
Training, scoring, iterative control examples and Pet/DAVIS additions remain
separately scoped work. No old tutorial generator or root pin is modified.

## Environment and provenance

The exp root remains pinned to framework769bba4539cc9bef0189427d7da278da1012daac.
Its tutorial previews enforce source, pyproject, lock and installed distribution
identity. This example never imports exp tutorials/experiments or executes their
runners under a different environment. Users export committed example/task bytes
into their own project and invoke that copied recipe with the selected framework
checkout's own `uv sync --group dev --frozen` environment.

Profile framework_revision currently selects
cdf60abc112f489c2eaf0dfa442acd2a11e46129 (includes reviewed B GUI acceptance).
asset_revision=693b85427f81226a51356d79a26b4f5556dbb0cd identifies the upstream
exported scientific assets, not authenticated unchanged current user bytes.
package_id/revision are explicit readable labels. Native composition supplies
semantic_fingerprint/task_data_path_id. No new fingerprint, accepted-task record,
immutable release registry or task-version lifecycle is introduced.

The framework checkout/interpreter/import origin must match the profile and be
clean. Public yuema repositories are not assumed to contain the development SHA;
initial qualification uses an available reviewed checkout. Public synchronization
or release is a separate authorized action.

## Inspection and acceptance

`inspect` validates the native profile, copies framework Luna routing only when
absent, and invokes existing observe_composition with an explicit task mount,
separate data reference and a60-second offline/device-free task sandbox. It saves
an Inspection wrapper around the original CompositionObservation. This is an
unaccepted observation, not launch permission. Dataset contents are not read by
this composition check. Empty data-directory fixtures in tests establish only
composition/preparation transport; they are not qualified scientific data.

`accept --accept-task` requires a successful selected report, explicit user action,
canonical private credentials, valid typed console/resources and absent outputs.
It derives all source/JSON bytes before publication, re-observes native task facts
and refuses drift. The only task pin is the existing TaskBinding in the canonical
ReusableWorkflowDocument and the same configured TaskChoice.task_revision.

Outputs: workflow.py, console.json, prepare-request.json, console-token(mode600),
state/, runs/, preparations/, candidates/, editor-recovery/(mode700). Successful
acceptance neither creates a candidate workspace nor submits an operation.
Output preflight refuses occupied names. Writes are exclusive; I/O failure may
retain partial files. No new transaction manager or recursive cleanup exists.
Keep partial evidence and materialize a fresh project.

## Same-source native consumption

WorkflowAuthoring.read produces the GUI SourceView of workflow.py. B review/Save
uses existing task selection, ordered findings and explicit acknowledgements.
GUI Save writes the same source that the native request names. Reusable native
preparation captures workflow.py.snapshot and enforces the original task pin.
After a source edit, the old prepare-request.json intentionally refuses: use
GUI New run or create a new typed request with current source identity/new UUID.
No silent mutation/replacement of earlier capture is allowed.

GUI New run and direct `tools.candidate_prepare --reusable-request` share the
existing preparation owners. Actual candidate submission remains
ReusableCandidate.review/launch → submit_operation. This recipe defines no
runtime submission helper, provider constructor, environment manager or launcher.
Expected run layout is runs/<UUID>/inputs/ plus later workspace/ if explicitly
launched. Outcome/usage/validity retain their existing independent native owners.

## Provider file

ConsoleConfig.credential_file names an explicit caller-owned mode600 JSON file.
An empty object is valid for offline work, but Review capture reports the missing
OPENAI_API_KEY. Shell key presence does not substitute for this configured file.
The recipe checks shape/permissions and never copies/logs its values. To enable
intentional paid execution, update the existing private file interactively:

```bash
"$INFRA_PYTHON" - "$PROVIDER_CREDENTIALS" <<'PY'
import getpass, json, os, sys
key = getpass.getpass('OpenAI API key: ')
with os.fdopen(os.open(sys.argv[1], os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW), 'w') as stream:
    json.dump({'OPENAI_API_KEY': key}, stream)
PY
```

Review source/task/routes/resources/credential readiness again before explicit
Launch. Network is enabled for that later candidate; environment forwarding is
OPENAI_API_KEY only, no devices,600-second candidate timeout. No API effects or
launch authority follow from successful composition, materialization or prepare.

## Bounded qualification

Exp tests use exp's own frozen environment only as the pytest/stdlib orchestrator;
SIDERIUS_CHECKOUT must name the profile's exact framework. Every native subprocess
uses that framework's own frozen interpreter. Copies live at unrelated paths with
spaces. No exp source is imported through another interpreter or PYTHONPATH.

Tests cover explicit acceptance, bad-port/private-file refusal before publication,
no overwrite, native task drift, original source request staleness, actual native
preparation/source snapshot equality and absent candidate/training effects.
The real Chromium driver loads code-edited source, changes/reviews/acknowledges/
saves it through B, then requests actual offline preparation of those saved bytes.
It checks the captured source, final connected session, missing provider key and
no candidate Launch request. No API/GPU/training/scientific success claim.

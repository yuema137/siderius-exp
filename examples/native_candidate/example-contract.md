# Native candidate example contract

Scope: external asset materialization and checked-current-snapshot acceptance,
then native three-stage reusable preparation/execution for TESS, Pet and DAVIS.
Training, scoring and iterative control examples remain
separately scoped work. No old tutorial generator or root pin is modified.

## Environment and provenance

The exp root remains pinned to framework769bba4539cc9bef0189427d7da278da1012daac.
Its tutorial previews enforce source, pyproject, lock and installed distribution
identity. This example never imports exp tutorials/experiments or executes their
runners under a different environment. Users export committed example/task bytes
into their own project and invoke that copied recipe with the selected framework
checkout's own `uv sync --group dev --frozen` environment.

Profile framework_revision currently selects
4272979663eb42c1f51ee4b840f304d7a36c30ee (merged PR883, including B GUI acceptance,
native reusable proposal families and checked task-reference updates). This explicitly
replaces the TESS/Pet framework pin; all three profiles require new
source/GUI/preparation qualification.
Profile asset_revision identifies upstream exported scientific assets (TESS693b854,
Pet0ef535b, DAVISac5572a), not authenticated unchanged current user bytes.
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


## Task profile distinctions

| Profile | Native task id | Input → output float32 dimensions after batch | Primary | Allowed output | Objective | Selected scope |
| --- | --- | --- | --- | --- | --- | --- |
| TESS | phyts_tess_rotation | [1,1024] → [1], unbounded | r2/higher | regressor | task does not select one | original train/validation stars |
| Pet | oxford_iiit_pet | [3,144,144] → [37] logits | accuracy/higher | classifier | categorical CE | gate2_train370 / gate2_validation74; no final |
| DAVIS | davis_future_prediction | [3,8,128,224] → [3,4,128,224] | mse/lower | regressor | custom davis_exact_l1 | gate2_train60 / gate2_validation15; no final |

Profiles are native typed declaration data consumed by the one unchanged recipe.
Pet data root contains individual JPEGs; TESS root contains its prepared NPZ files;
DAVIS root contains DAVIS/JPEGImages/480p. All share external private credential-file checks and explicit current-snapshot
acceptance. Tests preserve the existing five refusal/preparation cases for all three
profiles, assert independent expected native task/I/O/metric/output-type facts and
resolve Pet/DAVIS native objectives and exact original manifest-selected scopes
without image/frame loading. DAVIS checks sequence-level train/validation disjointness,
the actual selected custom-loss descriptor and MSE lower versus PSNR higher/MAE lower. The browser witness derives project/task/run labels from console config;
it must be executed separately for each qualified profile. No true-data or training
qualification follows from these empty-data-directory fixtures.


## TESS one-proposal fanout lesson

`tess/fanout/profile.json` selects the existing native-proposal-fanout/v1 grammar:
proposal → build_left/check_left and build_right/check_right. Both validation
requests use proposed-implementation-to-validation with exact proposal and
implementation result arguments. Managed aliases slot_left/slot_right resolve
through native layout to distinct storage.build_<side>.json files, each shared
only by its implementation/validator pair. One seed proposal.json is reused.
The exact native index has B+6=8 entries for B=2; unchanged native parent verification
owns source-derived names, paths, bytes and branch lineage. A node-count heuristic
cannot authorize the graph without the explicit execution profile.

The profile uses the same TESS scientific task binding/export provenance and
framework427 as the base lesson, plus distinct workflow example/run IDs. The common
recipe/browser driver are unchanged. Common PROFILE_FILE selects declaration data,
not a second engine. GUI source review/Save and native prepare preserve all five
instances and exact edges. Branch runtime remains the existing serial executor;
no shared-science diversity, aggregation/ranking/AND join, parallel execution or
training_settings support is implied. This preparatory lesson does not satisfy
TESS-D's aggregation/comparison requirement or A/B/C training/scoring packs.

Focused tests reuse the existing TESS fixture with an optional selected profile
path (default unchanged), assert the exact prepared seed/index/stores and validator
lineage, and exercise real native refusal of cross-branch aliases, incomplete
validation, missing explicit profile and stale edited graph source. No expanded
fixture framework or production materializer change. One original fixed TESS
native-prepare case protects the unchanged default selector. Actual browser source
parity and offline preparation are separate required witnesses; no provider/API,
GPU, data decoding or candidate launch occurs in qualification.

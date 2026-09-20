# Current qualification checkpoint

## Selected scope

The current operator decision is baseline plus SIDERIUS tools. Use the existing
baseline harness, permissions, scoring and archive. The expanded deployment at
exp `85a2191` / infra `8b416f88` is retained in Git history and withdrawn from this
release candidate. Its local component tests are historical evidence only.

## Evidence already obtained

- Actual synthetic coding-agent sessions read the toolkit and invoked native
  implementer/validator; two implementations overlapped and a later session
  revised a candidate using prior feedback.
- Independent processes/branches preserved candidate state. The composition
  JSON recovery and fresh-process seed registration bugs have concrete fixes.
- A subsequent real native tuner call reached planning, then refused CPU-only
  zero-VRAM resources. This is not a successful GPU training run.
- Existing public-package assembly and prior preparation checks preserve frozen
  bytes. Preparation remains distinct from deployment.

## H100 component evidence (2026-09-20)

The reserved band 0–3 host has qualified infra `3c317507` with exp `ad29fbd`:

- All four archived public task packages compose without private scorer source;
  each package's 96 original file hashes remain unchanged. Packages were loaded
  in independent processes, matching deployment.
- The installed research account constructs the native training command with
  the public composition, scope artifacts and protected validation launcher.
- Real public training-batch preflight passes in about 0.20 seconds without
  materializing local validation inputs.
- An installed protected training invocation runs two real epochs, 250 training
  and validation ML segments each, in about 32.95 seconds. Training uses UID 1002
  and private numeric validation uses UID 65534. Per-epoch validation computation
  is about 1.8–1.9 seconds, with a further 5.4–5.5 seconds of model/loss process
  startup; these tiny-model measurements are not large-model estimates.
- Native model reconstruction/export passes local trained-FCNet tests against
  the original candidate loader. An earlier real trained candidate separately
  passed the unchanged complete band 0–3 scorer, including all four files and
  six Health gates. Those were separate invocations, not one complete tuner run.
- Short parallel training and deadline cleanup have component evidence; the
  latest training smoke left no GPU process or temporary privileged entry.

### Complete public-runtime tuner call

On the same reserved host, infra `4bddacaf` / exp `8f5fa5f` subsequently completed
one actual tuner round through the public source distribution and its own frozen
environment. A deterministic diagnostic bridge supplied planning and reflection;
this is execution evidence, not a live coding-agent strategy test.

The two-epoch tiny model traversed protected native training, private per-epoch
loss, export, the unchanged complete band 0–3 scorer, trained-model artifact
certification, record creation and successful tuner termination. The original
complete receipt exists; the recorded artifact's size and SHA-256 were checked
against its actual file. Scoring covered all four files and all 200 PSD segments
per file. Temporary privileged entries were removed and the GPU process list
was empty after completion.

The entire service took 732.2 seconds. Protected training took 56.2 seconds;
each epoch's 2,000-row validation took 14.2–14.5 seconds plus 5.4–5.5 seconds for
model/loss worker startup. These remain tiny-model measurements. The diagnostic
run reported incomplete calibration identity and quarantined that measurement;
it is not evidence of reusable resource calibration.

The public runtime's 45 published files passed source-hash and immutable-source
checks under the research UID. Both research and numeric-worker namespaces
loaded their required modules and training entry while private validation and
operator source paths remained absent.

No formal orchestration clock was started. Live custom-loss review and the final
deployed coding-agent binding still need qualification. Local semantic-review
success does not prove deployed credential provisioning or service reachability.
The subsequently synchronized candidate requires its own review and CI; the
above installed revisions identify the completed hardware test precisely.

### Large-state transport measurement

The synchronized infra `a0775706` / exp `5a18b5e` public environment also passed
a synthetic FCNet transport test on that H100: 327,724,096 parameters, input
length 40,000, latent width 4,096 and batch size two. Two distinct weight states
were snapshotted and restored into separate confined numeric workers. Five
forward results per state matched direct native execution.

Each 1,310,898,589-byte snapshot took about 1.56 seconds to create. Worker startup
and state restoration took 5.19–5.21 seconds. The first isolated forward took
about 99 milliseconds; subsequent calls took 7–10 milliseconds versus about
0.56 milliseconds directly. Total service runtime was 19.77 seconds. This test
used synthetic inputs only, with no training, private validation or scoring;
it measures model transport, not full epoch validation or loss-worker overhead.

### Large-model native training and private loss

The same infra `a0775706` / exp `5a18b5e` pair subsequently passed two native
FCNet regression epochs with 327,724,096 parameters, batch size two and 2,000
private validation rows per epoch. The registered single-file plugin delegates
to the existing FCNet regression implementation; it does not replace the
network. Source discovery uses the research account's environment through the
command-specific sudo source-locator whitelist. The training result included
the retained model-candidate sidecar; this invocation did not score a candidate.

The native call took 83.83 seconds (87.04 seconds for the enclosing service).
Model startup took 5.15/5.21 seconds, loss startup 2.60/2.65 seconds and validation
15.13/15.01 seconds. Both epochs completed, and the temporary privileged entry
was removed. These are bounded 2,000-row measurements, not whole-band scoring
or 100-epoch throughput estimates.

The preceding failed attempts are retained as diagnosis: a read-only `/tmp`
mount broke captured-plugin materialization; after correcting that deployment
setting, the diagnostic plugin's inherited classification default conflicted
with its regression declaration. The passing plugin explicitly selects the
native regression head through the existing single-config constructor contract.
No framework or fixed-workflow implementation changed to obtain this pass.

A further two-epoch run passed under the actual baseline systemd isolation
properties, including its 16 MiB temporary filesystem, strict filesystem
protection and `baseline-results` primary group. The native namespace used
the existing baseline scratch directory, and the root coordinator received
write access to its own protected run-state directory. Native time was 83.83
seconds; per-epoch validation was 15.40/15.06 seconds. Both enclosing services
terminated successfully, no GPU compute process remained, and temporary
privileged entries were absent. The preceding service-level attempt correctly
rejected the login-default GID; deployment now binds the actual service GID.

## Remaining launch evidence

A real task candidate has traversed native calls, short H100 training, export and
existing baseline scoring. Preserve relevant multi-iteration/parallel/recovery/
deadline behavior, review the selected two-repository revisions, pass required
CI, merge, publish paired tags, then verify four clean rooms and start.

See [execution boundary](EXECUTION_BOUNDARY.md) for the selected runtime bindings
and [smoke](SMOKE.md) for acceptance.
The bounded tuner call passed; no formal orchestration start is claimed here.

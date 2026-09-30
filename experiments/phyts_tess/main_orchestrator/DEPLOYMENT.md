# What the host must provide before the native binding can run

Everything in this directory is code and stops at the same line: the native
binding needs **host privilege work that no committed file can perform**.
This page says exactly what, so the remaining gap is a list rather than a
discovery.

TIDMAD does not create these either — its preparation document states that
it "does not create new accounts, permissions, services or clocks", because
it reuses a room that already exists. **TESS has no such room.**

## Required, and why each is not optional

### 1. Two accounts

The framework refuses a single-user deployment outright
(`experiments/shared/native_launcher.py::authorize_native_caller`):

```python
if effective_uid != policy.coordinator_uid or effective_uid == policy.caller_uid:
    raise PermissionError("native launcher requires its separate coordinator account")
```

So the host needs a **caller** account, which the orchestrating agent runs
as, and a separate **coordinator** account that owns the launcher policy and
the evaluator view. The caller's identity must arrive through `sudo` —
`SUDO_UID` and `SUDO_GID` are read and checked against the policy — rather
than be asserted by the caller.

`verify_launcher_policy.py` refuses a policy whose two uids match, so this
is caught while drafting rather than under sudo with a clock running.

### 2. A root-owned wrapper and a sudoers rule

The caller invokes a wrapper, not the launcher. The wrapper is root-owned,
fixes the entry script, the checkout interpreter and the policy path, and
appends only the caller's native command. `deployments/shared/native_training_entry.py`
requires `python -I -B`: isolated, so the caller's `PYTHONPATH` and cwd
cannot reach the child, and no bytecode is written beside operator code.

The sudoers rule grants the caller exactly that wrapper and nothing else.

### 3. `bubblewrap`

Every namespace in the runtime policy names a `bubblewrap` binary. Probe,
training and worker phases each run confined, so the host needs `bwrap`
installed and usable by the coordinator.

### 4. A policy file in an operator-owned directory chain

`read_launcher_policy` walks every parent of the policy path and refuses if
any is not operator-owned or is writable by others. The policy is therefore
not merely a config file: its directory chain is part of the check.

**The file must be owned by the coordinator, not by root.** The launcher
reads it with `owner_uid=os.geteuid()`, and the wrapper runs *as the
coordinator*, so `st_uid != owner_uid` refuses a root-owned policy. Parents
may be root **or** the coordinator, which is why `/etc/tess-native` being
root-owned is correct while the file inside it being root-owned is not.
Installing it the obvious way — `install -o root -g root` — produces a
policy that passes every content check and fails at the first invocation
with *"launcher policy must be an operator-owned regular file"*.

```bash
sudo install -o tess-coordinator -g root -m 0644 policy.json /etc/tess-native/policy.json
```

**Draft it from the deployment, never by hand.** The first hand-written
policy verified and would have refused every real launch: it named the
caller's entry script where capture requires the framework's
`execute_tools/train_engine_sandbox.py` (the exact `argv[1]` the tuner
emits), declared three empty namespaces (bubblewrap mounts no host root
implicitly), and pointed `cwd` at a directory the protected relaunch cannot
import `experiments.shared.native_training_entry` from. None of that is
visible to a reader.

```bash
python -m experiments.phyts_tess.main_orchestrator.draft_launcher_policy \
    --deployment-root <root> --data-dir <rundata> \
    --caller-uid 996 --caller-gid 996 --coordinator-uid 995 \
    --caller-work /home/tess-caller/work --out policy.draft.json
python -m experiments.phyts_tess.main_orchestrator.stage_policy policy.draft.json \
    --out policy.staged.json --hours 6
sudo install -o tess-coordinator -g root -m 0644 policy.staged.json /etc/tess-native/policy.json
python -m experiments.phyts_tess.main_orchestrator.verify_launcher_policy \
    --installed /etc/tess-native/policy.json
sudo -u tess-coordinator <framework-python> \
    experiments/phyts_tess/main_orchestrator/machine/probe_namespace.py /etc/tess-native/policy.json
```

Once §5 has made the evaluator view coordinator-only, the drafter, the
stager and the verifier can no longer read the truth manifest as the
operator: run all three as the coordinator (`sudo -u tess-coordinator …`)
and write the drafts under `/var/lib/tess-native/`, which it owns.

The drafter asks the deployment's own interpreter for the training script's
location and the three pinned digests, hashes both manifests, and builds
the mount list from what the child must see: the system library trees, the
NVIDIA device nodes, the framework, the deployment's interpreter tree, the
published runtime, the caller bundle, the agent view and the data — plus
the caller's workspace, bound writable in the training namespace only. The
evaluator's identity manifest is pinned by digest as `truth_manifest`: the
coordinator computes per-epoch validation loss against it, in its own
process, and it is never mounted into a namespace. The verifier checks all
of this on the draft; `--installed` adds ownership and the parent chain;
`probe_namespace.py` enters the declared namespace as the coordinator and
imports what training needs, with CUDA visible.

`--caller-work` is the one host path the training child writes to, as the
coordinator. It must therefore be writable by the coordinator and readable
by the caller: `install_evaluator.sh` creates it owned by the caller with
group `tess-coordinator` and mode `2775`. Whether the caller's own tuner can
then rewrite files the coordinator created there is one of the things only
the smoke run settles.

### 5. The two views, separated

`prepare.py` writes `caller/` and `evaluator/` as siblings in one bundle,
which is right while the operator holds both. Before the caller runs, they
must be moved apart and given ownership that matches §1 — the caller must
not be able to read `evaluator/`, which holds `runtime/scoring.py` and the
identity manifest.

### 6. The scoring boundary: `tess-score`

The published metric refuses to execute without a complete evaluator bound in
the caller's process, and that evaluator scores nothing itself — it hands the
candidate to a coordinator-owned command. So the host needs a **second**
wrapper and sudoers rule, installed beside the training one:

```bash
sudo bash experiments/phyts_tess/main_orchestrator/machine/install_evaluator.sh \
    --checkout <same exp checkout> --python <same interpreter> --confirm
```

That creates `/usr/local/sbin/tess-score` (root-owned, runs as the
coordinator), `/etc/sudoers.d/tess-score`, and three directories: the
coordinator-private work root, the caller-readable receipt root, and the
caller-owned candidate root the coordinator reads from. It then needs an
**evaluator policy**, owned by the coordinator for the same reason the
launcher policy is:

```json
{
  "version": "phyts-tess-evaluator-policy-v1",
  "caller_uid": 996,
  "coordinator_uid": 995,
  "evaluator_view": "/path/to/bundle/evaluator",
  "validation_data": "/path/to/rundata",
  "candidate_root": "/var/lib/tess-candidates",
  "work_root": "/var/lib/tess-native/evaluator",
  "evaluation_root": "/var/lib/tess-evaluations",
  "health_policy": null,
  "device": "cpu",
  "inference_batch_size": 64
}
```

```bash
python -m experiments.phyts_tess.main_orchestrator.verify_evaluator_policy draft.json
sudo install -o tess-coordinator -g root -m 0644 draft.json /etc/tess-native/evaluator.json
python -m experiments.phyts_tess.main_orchestrator.verify_evaluator_policy \
    --installed /etc/tess-native/evaluator.json
```

`evaluator_view` is the bundle's `evaluator/` tree from §5, so this is where
§5's ownership matters: the coordinator must read it and the caller must not.
`validation_data` is the staged archive directory holding
`tess_rotation_val.npz` — flux only, no targets, so it may be the same
directory the caller trains from.

The caller's side is configured by a `TessEvaluationSettings` JSON
(`command`, `candidate_root`, `evaluation_root`, `run_id`, the frozen
`metric_declaration` and its sha256, `evaluator_uid`) that the run
declaration supplies; the command is
`["sudo", "-n", "-u", "tess-coordinator", "/usr/local/sbin/tess-score"]`.

## What is still not decided

The orchestration condition's **wall-clock and hardware budget**. `nop_004`
ran six hours on one RTX 5090 with an 8 GiB VRAM budget, and the execution
policy this directory emits already carries the same per-round bounds. The
wall clock is different: the fixed workflow's six hours bounded a chain with
a fixed iteration structure, and an orchestrator has none. Matching the
number is a comparability decision, not an inference, and it is the
operator's.

## What running it would first establish

The one thing reading cannot settle: whether the shared native machinery,
which was built around TIDMAD's geometry, transfers to a fixed-length
single-channel task — `[B, 1, 1024] float32 → [B, 1] float32`. That is the
first launch blocker `prepare.py` records, and it stays recorded until a
smoke run answers it.

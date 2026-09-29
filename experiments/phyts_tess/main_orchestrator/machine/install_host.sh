#!/bin/bash
# Create the host privilege separation the native binding requires.
#
# This is the part no committed Python can perform: two accounts, a
# root-owned wrapper, a sudoers rule and the directories each side owns.
# The framework refuses a single-user deployment outright, so none of it is
# optional — see EXECUTION_BOUNDARY.md and DEPLOYMENT.md.
#
# It prints its plan and does nothing without --confirm. It creates no
# service, no clock, and no network access, and it never touches the data
# root or an existing run.
set -euo pipefail

CALLER_USER=tess-caller
COORD_USER=tess-coordinator
STATE_ROOT=/var/lib/tess-native
POLICY_ROOT=/etc/tess-native
WRAPPER=/usr/local/sbin/tess-native-training
SUDOERS=/etc/sudoers.d/tess-native
ENTRY_NAME=native_training_entry.py

usage() {
    cat <<'USAGE'
usage: install_host.sh --checkout <exp-checkout> --python <interpreter> [--confirm]

  --checkout   siderius-exp checkout the launcher runs from. Its
               deployments/shared/native_training_entry.py becomes the
               wrapper's fixed entry point, and the entry script puts that
               checkout on sys.path.
  --python     interpreter the wrapper runs the launcher with. It must have
               the framework installed: the launcher imports pydantic and
               the framework before it does anything. The system python
               almost certainly does not, so this is usually a deployment
               venv rather than /usr/bin/python3.
  --confirm    actually make the changes. Without it this only prints them.

BOTH PATHS MUST BE REACHABLE BY THE CALLER ACCOUNT. They are baked into a
root-owned wrapper that the caller invokes, so a path under an operator's
home directory - typically mode 0750 - produces "Permission denied" at the
caller's first invocation and nowhere earlier. This script refuses to
install such a wrapper.

Run as root to apply. Re-running is safe: every step is skipped when already
correct.
USAGE
}

CHECKOUT=""
PYTHON=""
CONFIRM=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --checkout) CHECKOUT="${2:-}"; shift 2 ;;
        --python)   PYTHON="${2:-}"; shift 2 ;;
        --confirm)  CONFIRM=1; shift ;;
        -h|--help)  usage; exit 0 ;;
        *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$CHECKOUT" ]] || { echo "--checkout is required" >&2; exit 2; }
[[ -n "$PYTHON" ]] || { echo "--python is required" >&2; exit 2; }
CHECKOUT="$(cd "$CHECKOUT" && pwd)"
ENTRY_SOURCE="$CHECKOUT/deployments/shared/$ENTRY_NAME"
[[ -f "$ENTRY_SOURCE" ]] || {
    echo "not an exp checkout: $ENTRY_SOURCE is missing" >&2; exit 2; }
[[ -x "$PYTHON" ]] || { echo "not an executable interpreter: $PYTHON" >&2; exit 2; }

# Only applying needs privilege. Previewing the plan must not, or the
# operator cannot read what they are about to authorize without first
# authorizing it.
if [[ "$CONFIRM" -eq 1 && "$(id -u)" -ne 0 ]]; then
    echo "--confirm must run as root; re-run with sudo" >&2
    exit 2
fi

# bubblewrap confines every probe, training and worker phase. Report rather
# than install: what a host installs is the operator's decision.
BWRAP="$(command -v bwrap || true)"
[[ -n "$BWRAP" ]] || {
    echo "bubblewrap (bwrap) is not installed; the namespaces cannot start" >&2
    echo "  install it, then re-run: apt-get install -y bubblewrap" >&2
    exit 1
}

cat <<PLAN
plan
  caller account      $CALLER_USER        (the orchestrating agent runs as this)
  coordinator account $COORD_USER   (owns the policy and the evaluator view)
  state directory     $STATE_ROOT       owner $COORD_USER, mode 0750
  policy directory    $POLICY_ROOT          owner root, mode 0755
  wrapper             $WRAPPER
  sudoers rule        $SUDOERS
  entry point         $ENTRY_SOURCE
  launcher python     $PYTHON
  bubblewrap          $BWRAP
PLAN

# The sudoers rule is `caller ALL=(coordinator)`, so the wrapper EXECUTES AS
# THE COORDINATOR: it is the coordinator that reads the interpreter and the
# entry script, not the caller. Getting this account wrong would check a
# reachability nobody needs and miss the one that fails.
#
# Skipped when it cannot be performed rather than guessed at: without the
# privilege to become that account, every path would read as unreachable and
# the refusal would be about this script's own rights.
if id -u "$COORD_USER" >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    unreachable=()
    for fixed in "$PYTHON" "$ENTRY_SOURCE"; do
        sudo -n -u "$COORD_USER" test -r "$fixed" 2>/dev/null \
            || unreachable+=("$fixed")
    done
    if [[ ${#unreachable[@]} -gt 0 ]]; then
        echo
        echo "REFUSING: $COORD_USER cannot read:" >&2
        printf '  %s\n' "${unreachable[@]}" >&2
        echo >&2
        echo "The wrapper runs as $COORD_USER, so fixing these paths into it" >&2
        echo "would fail at the first invocation with Permission denied. A" >&2
        echo "home directory is usually 0750 — reachable by its owner and by" >&2
        echo "nobody else. Move them somewhere traversable and re-run." >&2
        exit 1
    fi
    echo
    echo "  reachability: $COORD_USER can read both fixed paths"
fi

if [[ "$CONFIRM" -ne 1 ]]; then
    echo
    echo "nothing changed. re-run with --confirm to apply."
    exit 0
fi

id -u "$CALLER_USER" >/dev/null 2>&1 \
    || useradd --system --create-home --home-dir "/home/$CALLER_USER" \
        --shell /bin/bash "$CALLER_USER"
id -u "$COORD_USER" >/dev/null 2>&1 \
    || useradd --system --home /nonexistent --shell /usr/sbin/nologin "$COORD_USER"

# The coordinator owns the job state. The caller must not be able to read it:
# it holds captured inputs and the evaluator's working files.
install -d -o "$COORD_USER" -g "$COORD_USER" -m 0750 "$STATE_ROOT"
install -d -o "$COORD_USER" -g "$COORD_USER" -m 0750 "$STATE_ROOT/work"

# read_launcher_policy walks every parent and refuses one that is not
# operator-owned or is writable by others, so the chain matters as much as
# the file.
install -d -o root -g root -m 0755 "$POLICY_ROOT"

# The wrapper fixes the interpreter, the entry script and the policy path.
# -I drops the caller's PYTHONPATH and cwd; -B writes no bytecode beside
# operator code. The caller appends only its native command.
cat > "$WRAPPER" <<WRAPPER_EOF
#!/bin/bash
# Installed by install_host.sh. Do not edit by hand: the caller is granted
# exactly this path, and its fixed arguments are the privilege boundary.
set -euo pipefail
exec "$PYTHON" -I -B "$CHECKOUT/deployments/shared/$ENTRY_NAME" \\
    "$POLICY_ROOT/policy.json" "\$@"
WRAPPER_EOF
chown root:root "$WRAPPER"
chmod 0755 "$WRAPPER"

# Exactly the wrapper, nothing else, and as the coordinator rather than root.
cat > "$SUDOERS.tmp" <<SUDOERS_EOF
$CALLER_USER ALL=($COORD_USER) NOPASSWD: $WRAPPER
SUDOERS_EOF
chmod 0440 "$SUDOERS.tmp"
chown root:root "$SUDOERS.tmp"
visudo -cf "$SUDOERS.tmp" >/dev/null
mv "$SUDOERS.tmp" "$SUDOERS"

cat <<DONE

done.
  caller uid      $(id -u "$CALLER_USER")
  caller gid      $(id -g "$CALLER_USER")
  coordinator uid $(id -u "$COORD_USER")

next, as the operator:
  1. write the policy using those uids, and install it OWNED BY $COORD_USER
     (the launcher reads it as that account; a root-owned file is refused):
       sudo install -o $COORD_USER -g root -m 0644 draft.json \\
           $POLICY_ROOT/policy.json
  2. verify it where it lives:
       python -m experiments.phyts_tess.main_orchestrator.verify_launcher_policy \\
           --installed $POLICY_ROOT/policy.json
  3. move the bundle's evaluator/ view somewhere $CALLER_USER cannot read
DONE

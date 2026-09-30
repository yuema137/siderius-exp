#!/bin/bash
# Install the `tess-score` privilege boundary beside the native-training one.
#
# install_host.sh created the two accounts and the training wrapper. This
# adds what scoring needs: a second root-owned wrapper the caller may run as
# the coordinator, the directories each side owns, and nothing else. It
# prints its plan and does nothing without --confirm. It never touches the
# data root, an existing run, or the training wrapper.
set -euo pipefail

CALLER_USER=tess-caller
COORD_USER=tess-coordinator
POLICY_ROOT=/etc/tess-native
POLICY_FILE="$POLICY_ROOT/evaluator.json"
WORK_ROOT=/var/lib/tess-native/evaluator
EVALUATION_ROOT=/var/lib/tess-evaluations
CANDIDATE_ROOT=/var/lib/tess-candidates
CALLER_WORK=/home/tess-caller/work
WRAPPER=/usr/local/sbin/tess-score
SUDOERS=/etc/sudoers.d/tess-score
ENTRY_REL=deployments/phyts_tess_orchestration/tess_score_entry.py

usage() {
    cat <<'USAGE'
usage: install_evaluator.sh --checkout <exp-checkout> --python <interpreter> [--confirm]

  --checkout   the SAME siderius-exp checkout install_host.sh was given.
  --python     the SAME interpreter install_host.sh was given.
  --confirm    actually make the changes. Without it this only prints them.

Both accounts must already exist (install_host.sh). Both paths must be
readable by the COORDINATOR: the wrapper runs as that account.
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
ENTRY_SOURCE="$CHECKOUT/$ENTRY_REL"
[[ -f "$ENTRY_SOURCE" ]] || {
    echo "not an exp checkout with the scorer entry: $ENTRY_SOURCE is missing" >&2; exit 2; }
[[ -x "$PYTHON" ]] || { echo "not an executable interpreter: $PYTHON" >&2; exit 2; }
for account in "$CALLER_USER" "$COORD_USER"; do
    id -u "$account" >/dev/null 2>&1 || {
        echo "account $account does not exist; run install_host.sh first" >&2; exit 2; }
done

if [[ "$CONFIRM" -eq 1 && "$(id -u)" -ne 0 ]]; then
    echo "--confirm must run as root; re-run with sudo" >&2
    exit 2
fi

cat <<PLAN
plan
  wrapper             $WRAPPER            (runs as $COORD_USER)
  sudoers rule        $SUDOERS
  entry point         $ENTRY_SOURCE
  scorer python       $PYTHON
  evaluator policy    $POLICY_FILE          owner $COORD_USER (you install it)
  work root           $WORK_ROOT   owner $COORD_USER, mode 0750
  evaluation root     $EVALUATION_ROOT       owner $COORD_USER, mode 0755 (caller reads receipts)
  candidate root      $CANDIDATE_ROOT        owner $CALLER_USER,      mode 0755 (coordinator reads candidates)
  caller work         $CALLER_WORK        owner $CALLER_USER, group $COORD_USER, mode 2775 (training writes here as the coordinator)
PLAN

# Same reachability rule as install_host.sh, same account, same reason.
if sudo -n true 2>/dev/null; then
    unreachable=()
    for fixed in "$PYTHON" "$ENTRY_SOURCE"; do
        sudo -n -u "$COORD_USER" test -r "$fixed" 2>/dev/null \
            || unreachable+=("$fixed")
    done
    if [[ ${#unreachable[@]} -gt 0 ]]; then
        echo
        echo "REFUSING: $COORD_USER cannot read:" >&2
        printf '  %s\n' "${unreachable[@]}" >&2
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

install -d -o "$COORD_USER" -g "$COORD_USER" -m 0750 "$WORK_ROOT"
install -d -o "$COORD_USER" -g root -m 0755 "$EVALUATION_ROOT"
install -d -o "$CALLER_USER" -g "$CALLER_USER" -m 0755 "$CANDIDATE_ROOT"
# The training child runs as the coordinator inside its namespace and writes
# checkpoints and results into the caller's sandbox; setgid keeps every file it
# creates readable by the caller through the shared group.
install -d -o "$CALLER_USER" -g "$COORD_USER" -m 2775 "$CALLER_WORK"

cat > "$WRAPPER" <<WRAPPER_EOF
#!/bin/bash
# Installed by install_evaluator.sh. Do not edit by hand: the caller is
# granted exactly this path, and its fixed arguments are the privilege boundary.
set -euo pipefail
exec "$PYTHON" -I -B "$ENTRY_SOURCE" "$POLICY_FILE" "\$@"
WRAPPER_EOF
chown root:root "$WRAPPER"
chmod 0755 "$WRAPPER"

cat > "$SUDOERS.tmp" <<SUDOERS_EOF
$CALLER_USER ALL=($COORD_USER) NOPASSWD: $WRAPPER
SUDOERS_EOF
chmod 0440 "$SUDOERS.tmp"
chown root:root "$SUDOERS.tmp"
visudo -cf "$SUDOERS.tmp" >/dev/null
mv "$SUDOERS.tmp" "$SUDOERS"

cat <<DONE

done.

next, as the operator:
  1. write the evaluator policy (see DEPLOYMENT.md) with
       caller_uid $(id -u "$CALLER_USER"), coordinator_uid $(id -u "$COORD_USER"),
       work_root $WORK_ROOT, evaluation_root $EVALUATION_ROOT,
       candidate_root $CANDIDATE_ROOT; and draft the launcher policy with
       --caller-work $CALLER_WORK
     and install it OWNED BY $COORD_USER:
       sudo install -o $COORD_USER -g root -m 0644 evaluator.json $POLICY_FILE
  2. verify it where it lives:
       python -m experiments.phyts_tess.main_orchestrator.verify_evaluator_policy \\
           --installed $POLICY_FILE
  3. make the evaluator view readable by $COORD_USER and by nobody else:
       sudo chown -R $COORD_USER:root <bundle>/evaluator && sudo chmod -R o-rwx <bundle>/evaluator
DONE

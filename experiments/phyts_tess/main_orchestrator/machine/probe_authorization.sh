#!/bin/bash
# Prove the privilege path works, without training anything.
#
# The caller's first real invocation crosses five stages before a single
# batch is read. Each can be misconfigured independently, and a failure in
# any of them looks the same from outside: the run did not start. This
# exercises all five with a command that is deliberately NOT a training
# invocation.
#
#   1. sudo grants the caller exactly the wrapper          (sudoers rule)
#   2. the wrapper fixes interpreter, entry and policy     (installed file)
#   3. read_launcher_policy walks the owner chain          (directory modes)
#   4. authorize_native_caller checks SUDO_UID/SUDO_GID    (the two accounts)
#   5. capture refuses a command that is not the entrypoint
#
# So SUCCESS HERE IS A NAMED REFUSAL. Reaching stage 5's message proves the
# four before it worked; any other message says which one did not.
#
# It starts no clock, calls no model, trains nothing and scores nothing.
set -uo pipefail

CALLER_USER=${CALLER_USER:-tess-caller}
WRAPPER=${WRAPPER:-/usr/local/sbin/tess-native-training}
COORD_USER=${COORD_USER:-tess-coordinator}

EXPECTED="invocation must use the deployment's native entrypoint"

echo "probing the authorization path as $CALLER_USER"
echo "  wrapper: $WRAPPER"
echo

output="$(sudo -u "$CALLER_USER" sudo -n -u "$COORD_USER" "$WRAPPER" \
    /nonexistent/not-a-training-command 2>&1)"
status=$?

echo "--- launcher output ---"
echo "$output"
echo "-----------------------"
echo

if grep -qF "$EXPECTED" <<<"$output"; then
    echo "PASS: reached input capture, which means stages 1-4 all worked."
    echo "      The refusal is the expected one: the probe command is not the"
    echo "      deployment's entrypoint, which is exactly what it should not be."
    exit 0
fi

echo "FAIL: the expected refusal was not reached. What the message says:"
case "$output" in
    *"a password is required"*|*"not allowed to execute"*)
        echo "  stage 1 — the sudoers rule does not grant $CALLER_USER this wrapper" ;;
    *"No such file or directory"*)
        echo "  stage 2 — the wrapper or its fixed entry script is missing" ;;
    *"Permission denied"*)
        echo "  stage 2 — a path baked into the wrapper is unreadable by"
        echo "            $COORD_USER, which is the account the wrapper RUNS AS"
        echo "            (the sudoers rule is caller ALL=(coordinator)). A home"
        echo "            directory is typically 0750: readable by its owner and"
        echo "            by nobody else. Re-run install_host.sh with --checkout"
        echo "            and --python under a traversable path." ;;
    *"launcher policy"*)
        echo "  stage 3 — the policy file or one of its parent directories is"
        echo "            not operator-owned, or is writable by others" ;;
    *"separate coordinator account"*|*"sudo-issued caller identity"*|*"not assigned to this run"*)
        echo "  stage 4 — the policy's uids do not match the accounts in use" ;;
    *)
        echo "  unrecognized; read the launcher output above" ;;
esac
exit 1

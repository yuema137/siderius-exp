#!/bin/bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: install_vm.sh must run as root" >&2
    exit 2
fi
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 codex|claude BUNDLE_ROOT" >&2
    exit 2
fi

PRODUCT="$1"
BUNDLE_ROOT="$(cd "$2" && pwd -P)"
PYTHON_BIN="${BASELINE_PYTHON_BIN:-python3.12}"
WHEEL_NAME_FILE="${BUNDLE_ROOT}/evaluator/siderius-wheel-name.txt"
EVALUATOR_REQUIREMENTS="${BUNDLE_ROOT}/evaluator/requirements.txt"
if [ "$PRODUCT" != codex ] && [ "$PRODUCT" != claude ]; then
    echo "ERROR: product must be codex or claude" >&2
    exit 2
fi
if [ ! -f "$WHEEL_NAME_FILE" ] || [ ! -f "$EVALUATOR_REQUIREMENTS" ]; then
    echo "ERROR: pinned evaluator environment is incomplete" >&2
    exit 2
fi
WHEEL_NAME="$(tr -d '\r\n' <"$WHEEL_NAME_FILE")"
if [ -z "$WHEEL_NAME" ] || [ "$(basename "$WHEEL_NAME")" != "$WHEEL_NAME" ]; then
    echo "ERROR: invalid pinned evaluator wheel name" >&2
    exit 2
fi
SIDERIUS_WHEEL="${BUNDLE_ROOT}/evaluator/${WHEEL_NAME}"
if [ ! -f "$SIDERIUS_WHEEL" ]; then
    echo "ERROR: pinned evaluator wheel is missing: $WHEEL_NAME" >&2
    exit 2
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: required Python interpreter is unavailable: $PYTHON_BIN" >&2
    exit 2
fi
if [ "$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.12" ]; then
    echo "ERROR: baseline deployment requires Python 3.12" >&2
    exit 2
fi
if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: provision an AWS CLI before install; the harness will not install an unpinned latest version" >&2
    exit 2
fi
if systemctl is-active --quiet tidmad-coding-agent.service; then
    echo "ERROR: refuse to replace a bundle while the evaluated agent is active" >&2
    exit 2
fi
(
    cd "${BUNDLE_ROOT}/evaluator"
    sha256sum --check SHA256
)

getent group baseline-results >/dev/null || groupadd --system baseline-results
getent group baseline-agent >/dev/null || groupadd --system baseline-agent
getent group baseline-evaluator >/dev/null || groupadd --system baseline-evaluator
getent group baseline-inference >/dev/null || groupadd --system baseline-inference
id baseline-agent >/dev/null 2>&1 \
    || useradd --create-home --shell /bin/bash --gid baseline-agent baseline-agent
usermod -a -G baseline-results baseline-agent
id baseline-evaluator >/dev/null 2>&1 \
    || useradd --system --home /nonexistent --shell /usr/sbin/nologin \
        --gid baseline-evaluator baseline-evaluator
usermod -a -G baseline-results baseline-evaluator
id baseline-inference >/dev/null 2>&1 \
    || useradd --system --home /nonexistent --shell /usr/sbin/nologin \
        --gid baseline-inference baseline-inference
for device_group in video render; do
    if getent group "$device_group" >/dev/null; then
        usermod -a -G "$device_group" baseline-inference
    fi
done
id baseline-backup >/dev/null 2>&1 \
    || useradd --system --home /nonexistent --shell /usr/sbin/nologin baseline-backup
usermod -a -G baseline-results baseline-backup

rm -rf -- /work/harness /work/input /opt/tidmad-evaluator /opt/tidmad-inference
install -d -o root -g root -m 0755 /work /work/harness /work/input
cp -a "$BUNDLE_ROOT/input/." /work/input/
cp -a "$BUNDLE_ROOT/harness/." /work/harness/
find /work/input -type d -exec chmod 0555 {} +
find /work/input -type f -exec chmod 0444 {} +
chown -R root:root /work/input /work/harness

for child in agent state submission logs; do
    install -d -o baseline-agent -g baseline-results -m 2770 "/work/$child"
done
install -d -o root -g root -m 0755 /data
install -d -o baseline-evaluator -g baseline-results -m 2750 \
    /var/lib/tidmad-baseline /var/lib/tidmad-baseline/candidates
install -d -o root -g baseline-inference -m 0750 \
    /var/lib/tidmad-baseline/inference-sessions
install -d -o baseline-backup -g baseline-backup -m 0700 \
    /var/lib/tidmad-baseline/backup-receipts
install -d -o root -g root -m 0755 /etc/tidmad-baseline

"$PYTHON_BIN" -m venv /work/harness/venv
HARNESS_SITE="$(/work/harness/venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
cp -a /work/harness/baseline_harness "$HARNESS_SITE/"

install -d -o baseline-evaluator -g baseline-results -m 0750 /opt/tidmad-evaluator
install -d -o baseline-evaluator -g baseline-evaluator -m 0750 \
    /opt/tidmad-evaluator/assets
cp -a "${BUNDLE_ROOT}/evaluator/." /opt/tidmad-evaluator/assets/
"$PYTHON_BIN" -m venv /opt/tidmad-evaluator/venv
/opt/tidmad-evaluator/venv/bin/pip install --disable-pip-version-check \
    --requirement /opt/tidmad-evaluator/assets/requirements.txt
/opt/tidmad-evaluator/venv/bin/pip install --disable-pip-version-check \
    --force-reinstall --no-deps "/opt/tidmad-evaluator/assets/${WHEEL_NAME}"
EVALUATOR_SITE="$(/opt/tidmad-evaluator/venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
cp -a /work/harness/baseline_harness "$EVALUATOR_SITE/"
chown -R baseline-evaluator:baseline-evaluator /opt/tidmad-evaluator
chmod -R o-rwx /opt/tidmad-evaluator

install -d -o root -g root -m 0755 /opt/tidmad-inference
"$PYTHON_BIN" -m venv /opt/tidmad-inference/venv
/opt/tidmad-inference/venv/bin/pip install --disable-pip-version-check \
    --requirement /opt/tidmad-evaluator/assets/requirements.txt
/opt/tidmad-inference/venv/bin/pip install --disable-pip-version-check \
    --force-reinstall --no-deps "/opt/tidmad-evaluator/assets/${WHEEL_NAME}"
INFERENCE_SITE="$(/opt/tidmad-inference/venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
cp -a /work/harness/baseline_harness "$INFERENCE_SITE/"
chown -R root:root /opt/tidmad-inference
find /opt/tidmad-inference -type d -exec chmod 0555 {} +
find /opt/tidmad-inference -type f -exec chmod 0444 {} +
find /opt/tidmad-inference/venv/bin -type f -exec chmod 0555 {} +

install -d -o root -g root -m 0755 /usr/local/libexec
cat >/usr/local/libexec/tidmad-score-candidate <<'EOF'
#!/bin/sh
exec /opt/tidmad-evaluator/venv/bin/python -I -m baseline_harness.score candidate "$@"
EOF
chmod 0755 /usr/local/libexec/tidmad-score-candidate

cat >/etc/sudoers.d/tidmad-baseline-score <<'EOF'
Defaults!/usr/local/libexec/tidmad-score-candidate env_keep += "BASELINE_RUN_ID BASELINE_INVOCATION_ID"
baseline-agent ALL=(root) NOPASSWD: /usr/local/libexec/tidmad-score-candidate *
EOF
chmod 0440 /etc/sudoers.d/tidmad-baseline-score

cat >/usr/local/bin/tidmad-score <<'EOF'
#!/bin/sh
exec sudo -n /usr/local/libexec/tidmad-score-candidate "$@"
EOF
chmod 0755 /usr/local/bin/tidmad-score

install -m 0644 /work/harness/systemd/tidmad-coding-agent.service /etc/systemd/system/
install -m 0644 /work/harness/systemd/tidmad-baseline-backup.service /etc/systemd/system/
install -m 0644 /work/harness/systemd/tidmad-baseline-backup.timer /etc/systemd/system/
install -m 0644 /work/harness/systemd/tidmad-baseline-finalize.service /etc/systemd/system/
cat >/etc/tidmad-baseline/agent.env <<EOF
BASELINE_PRODUCT=$PRODUCT
EOF
chown root:baseline-agent /etc/tidmad-baseline/agent.env
chmod 0640 /etc/tidmad-baseline/agent.env
systemctl daemon-reload

{
    printf 'python=%s\n' "$(/work/harness/venv/bin/python --version 2>&1)"
    printf 'aws=%s\n' "$(aws --version 2>&1)"
} >/etc/tidmad-baseline/install-receipt.txt
chmod 0444 /etc/tidmad-baseline/install-receipt.txt

echo "Installed $PRODUCT baseline harness. Credentials and the formal schedule are not set."

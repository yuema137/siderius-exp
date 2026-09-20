"""Actual namespace visibility and inherited-channel checks (Linux/bubblewrap)."""

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.shared.validation_confinement import (
    NamespaceMount,
    ValidationNamespace,
)


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap not installed")
@pytest.mark.parametrize("share_network", [False, True])
def test_namespace_mounts_and_inherited_channel(tmp_path, share_network):
    public = tmp_path / "public"
    public.mkdir()
    (public / "input.txt").write_text("public fixture")
    private = public / "hidden"
    private.mkdir()
    (private / "answer.txt").write_text("synthetic private fixture")
    output = tmp_path / "output"
    output.mkdir()
    omitted = tmp_path / "not_mounted.txt"
    omitted.write_text("must not be visible")
    roots = [
        Path(x)
        for x in ("/usr", "/lib", "/lib64", "/etc/ld.so.cache")
        if Path(x).exists()
    ]
    roots.extend((Path(sys.base_prefix).parent, Path(sys.prefix), public))
    policy = ValidationNamespace(
        bubblewrap=Path(shutil.which("bwrap")),
        cwd=public,
        mounts=tuple(NamespaceMount(source=p, target=p) for p in roots)
        + (NamespaceMount(source=output, target=output, mode="write"),),
        hidden_directories=(private,),
        share_network=share_network,
    )
    code = """import json,os,socket,sys
from pathlib import Path
public,private,output,omitted = map(Path,sys.argv[2:])
assert (public/'input.txt').read_text() == 'public fixture'
assert not list(private.iterdir())
assert not omitted.exists()
try:
    (public/'input.txt').write_text('bad')
except OSError:
    pass
else:
    raise AssertionError('public mount writable')
(output/'result.txt').write_text('written')
s=socket.socket(fileno=int(sys.argv[1]))
assert s.recv(64)==b'from-coordinator'
s.sendall(json.dumps({'network':os.readlink('/proc/self/ns/net'),
                      'pid':os.readlink('/proc/self/ns/pid'),
                      'cache':os.environ['TORCHINDUCTOR_CACHE_DIR']}).encode())
"""
    parent, child = socket.socketpair()
    try:
        parent.settimeout(10)
        with subprocess.Popen(
            [
                *policy.prefix(),
                sys.executable,
                "-c",
                code,
                str(child.fileno()),
                str(public),
                str(private),
                str(output),
                str(omitted),
            ],
            pass_fds=(child.fileno(),),
            env={"PATH": os.defpath},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as process:
            child.close()
            parent.sendall(b"from-coordinator")
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 0, (stdout, stderr)
            result = json.loads(parent.recv(4096))
        assert (result["network"] == os.readlink("/proc/self/ns/net")) == share_network
        assert result["pid"] != os.readlink("/proc/self/ns/pid")
        assert result["cache"] == "/tmp/torchinductor"
        assert (output / "result.txt").read_text() == "written"
        assert (private / "answer.txt").read_text() == "synthetic private fixture"
        assert (public / "input.txt").read_text() == "public fixture"
    finally:
        parent.close()
        child.close()


@pytest.mark.skipif(os.geteuid() != 0, reason="requires actual root host credentials")
def test_host_identity_can_write_own_directory_but_not_root_secret(tmp_path):
    uid, gid = 65534, 65534
    output = tmp_path / "owned"
    output.mkdir(mode=0o700)
    os.chown(output, uid, gid)
    secret = tmp_path / "secret"
    secret.write_text("synthetic private target")
    secret.chmod(0o600)
    roots = [
        Path(p)
        for p in ("/usr", "/lib", "/lib64", "/etc/ld.so.cache")
        if Path(p).exists()
    ]
    roots += [Path(sys.base_prefix).parent, Path(sys.prefix), secret]
    policy = ValidationNamespace(
        bubblewrap=Path(shutil.which("bwrap")),
        cwd=output,
        uid=uid,
        gid=gid,
        mounts=tuple(NamespaceMount(source=p, target=p) for p in roots)
        + (NamespaceMount(source=output, target=output, mode="write"),),
    )
    code = """import os,sys
from pathlib import Path
assert os.getuid()==65534
assert os.getgroups()==[]
Path('/tmp/runtime-cache').write_text('namespace-local writable cache')
status=Path('/proc/self/status').read_text()
for key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb'):
    assert int(next(line.split()[1] for line in status.splitlines() if line.startswith(key+':')),16)==0
assert next(line.split()[1] for line in status.splitlines() if line.startswith('NoNewPrivs:'))=='1'
try:
    Path(sys.argv[1]).read_text()
except PermissionError:
    pass
else:
    raise AssertionError('host-root secret readable')
Path('result').write_text('owned by actual host uid')
"""
    result = subprocess.run(
        [*policy.prefix(), sys.executable, "-c", code, str(secret)],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert (output / "result").stat().st_uid == uid
    assert (output / "result").stat().st_gid == gid

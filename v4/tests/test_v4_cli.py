"""v4 SPEC 9.4, 9.5, 10: exit codes, usage, the manifest command, bytes paths (finding 03),
unreadable files (16), the manifest writer (17), the memory floor (X002). Mutation report
mutation-v3/SUMMARY.md, __main__ survivors 22, 25-37, 48, 62."""
import hashlib
import os
import subprocess
import sys

import helpers
import pytest

SRC = os.environ.get("REALITY4_SRC") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")


def cli(*args, env=None, preexec=None, cwd=None):
    e = {"PATH": "/usr/bin:/bin", "PYTHONPATH": SRC, "LC_ALL": "C.UTF-8", "PYTHONUTF8": "1"}
    if os.name == "nt":   # Windows Python cannot start without SYSTEMROOT
        e.update(SYSTEMROOT=os.environ["SYSTEMROOT"], PATH=os.environ.get("PATH", ""))
    e.update(env or {})
    r = subprocess.run([sys.executable, "-m", "reality4", *args], capture_output=True, env=e,
                       preexec_fn=preexec, cwd=cwd, timeout=120)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def write(p, b):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b)
    return hashlib.sha256(b).hexdigest()


def test_accepted_exits_0_refused_1(tmp_path):
    h = write(str(tmp_path / "t.tsv"), b"a\tb\n1\t2\n")
    write(str(tmp_path / "ok.rl"), f"file f = sha256:{h}\nclaim rows(tsv(f))\n".encode())
    write(str(tmp_path / "no.rl"), f"file f = sha256:{h}\nclaim rows(tsv(f), 1)\n".encode())
    rc, out, _ = cli("check", str(tmp_path / "ok.rl"), "--files", str(tmp_path / "t.tsv"))
    assert rc == 0 and out.endswith("accepted\n"), out
    rc, out, _ = cli("check", str(tmp_path / "no.rl"), "--files", str(tmp_path / "t.tsv"))
    assert rc == 1 and "refused" in out
    rc, out, _ = cli("check", str(tmp_path / "ok.rl"), str(tmp_path / "no.rl"), "--files", str(tmp_path / "t.tsv"))
    assert rc == 1 and f"== {tmp_path / 'ok.rl'}" in out


@pytest.mark.parametrize("args", [[], ["frobnicate"], ["manifest"], ["manifest", "a", "--out"], ["manifest", "a", "b", "c"], ["manifest", "--out", "x"]])
def test_usage_exits_2_on_stderr(args):
    rc, out, err = cli(*args)
    assert rc == 2 and out == "" and "python -m reality4 check" in err


def test_manifest_command(tmp_path):
    d = tmp_path / "d"
    write(str(d / "b.txt"), b"bb")
    write(str(d / "a" / "x.tsv"), b"a\n")
    rc, out, _ = cli("manifest", str(d))
    expect = ("reality-manifest 1\n" + f"{hashlib.sha256(b'a\n').hexdigest()}\t2\ta/x.tsv\n"
              + f"{hashlib.sha256(b'bb').hexdigest()}\t2\tb.txt\n").encode()
    assert rc == 0 and out.encode() == expect
    rc, out, _ = cli("manifest", str(d), "--out", str(tmp_path / "m"))
    assert rc == 0 and open(tmp_path / "m", "rb").read() == expect
    assert out == f"sha256:{hashlib.sha256(expect).hexdigest()}  {tmp_path / 'm'}\n"


def test_manifest_missing_folder_exits_2(tmp_path):
    rc, out, err = cli("manifest", str(tmp_path / "nope"))
    assert rc == 2 and out == "" and "not a folder" in err


def test_manifest_refuses_non_utf8_names(tmp_path):
    d = str(tmp_path / "d")
    os.makedirs(d)
    # POSIX: a name with the byte 0xff; Windows (UTF-16 names): an unpaired surrogate, which has no UTF-8 form either
    bad = os.path.join(os.fsencode(d), b"x\xff") if os.name == "posix" else os.path.join(d, "x\ud800")
    with open(bad, "wb") as f:
        f.write(b"1")
    rc, out, err = cli("manifest", d)
    assert rc == 2 and out == "" and "not UTF-8" in err


@pytest.mark.skipif(os.name == "nt", reason="Windows file names cannot contain a tab (characters 1-31 are forbidden)")
def test_manifest_refuses_tab_names(tmp_path):
    d = os.fsencode(str(tmp_path / "d"))
    os.makedirs(d)
    with open(os.path.join(d, b"a\tb"), "wb") as f:
        f.write(b"1")
    rc, out, err = cli("manifest", str(tmp_path / "d"))
    assert rc == 2 and "manifest path" in err


@pytest.mark.parametrize("env", [{"LC_ALL": "C.UTF-8", "PYTHONUTF8": "1"}, {"LC_ALL": "C", "PYTHONUTF8": "0"}])
def test_non_ascii_names_independent_of_locale(tmp_path, env):   # findings 03, 17
    d = tmp_path / "ds"
    h = write(str(d / "notes-été.txt"), b"hello")
    rc, man, _ = cli("manifest", str(d), env=env)
    assert rc == 0 and "notes-été.txt" in man
    mh = write(str(tmp_path / "m" / "x.manifest"), man.encode())
    write(str(tmp_path / "p.rl"), f"file m = sha256:{mh}\nfile f = sha256:{h}\nclaim size(f)\n".encode())
    rc, out, _ = cli("check", str(tmp_path / "p.rl"), "--files", str(tmp_path / "m"), "--root", str(d), env=env)
    assert rc == 0 and "ByteCount" in out and "= 5" in out, out


def test_unreadable_supplied_file_is_skipped(tmp_path):   # finding 16
    h = write(str(tmp_path / "f" / "t.tsv"), b"a\n1\n")
    write(str(tmp_path / "f" / "locked.tsv"), b"b\n2\n")
    undo = helpers.unreadable(str(tmp_path / "f" / "locked.tsv"))
    try:
        write(str(tmp_path / "p.rl"), f"file f = sha256:{h}\nclaim rows(tsv(f))\n".encode())
        rc, out, _ = cli("check", str(tmp_path / "p.rl"), "--files", str(tmp_path / "f"))
        assert rc == 0 and "= 1 (Exact)" in out, out
    finally:
        undo()


def _limit(mb):
    def f():
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (mb * 1024 * 1024, mb * 1024 * 1024))
    return f


@pytest.mark.skipif(os.name != "posix", reason="setrlimit(RLIMIT_AS) exists only on POSIX; the Windows limit (a job object) is test_below_memory_floor_in_a_windows_job")
def test_below_memory_floor_checks_nothing(tmp_path):
    h = write(str(tmp_path / "t.tsv"), b"a\n1\n")
    write(str(tmp_path / "p.rl"), f"file f = sha256:{h}\nclaim rows(tsv(f))\n".encode())
    rc, out, _ = cli("check", str(tmp_path / "p.rl"), "--files", str(tmp_path / "t.tsv"), preexec=_limit(1024))
    assert rc == 3 and out.startswith("no verdict: this machine's memory limit") and "formed" not in out


@pytest.mark.skipif(os.name != "nt", reason="job objects are Windows' memory limit; POSIX rlimits are test_below_memory_floor_checks_nothing")
@pytest.mark.parametrize("flag", [0x100, 0x200])   # JOB_OBJECT_LIMIT_PROCESS_MEMORY, JOB_OBJECT_LIMIT_JOB_MEMORY
def test_below_memory_floor_in_a_windows_job(tmp_path, flag):
    h = write(str(tmp_path / "t.tsv"), b"a\n1\n")
    write(str(tmp_path / "p.rl"), f"file f = sha256:{h}\nclaim rows(tsv(f))\n".encode())
    args = ["check", str(tmp_path / "p.rl"), "--files", str(tmp_path / "t.tsv")]
    e = dict(os.environ, PYTHONPATH=SRC)
    r = subprocess.run([sys.executable, "-c", helpers.JOB_LIMIT_SRC, str(flag), str(1 << 30), *args], capture_output=True, env=e, timeout=120)
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 3 and "(1073741824 bytes) is below" in out and "formed" not in out, (out, r.stderr)
    r = subprocess.run([sys.executable, "-c", helpers.JOB_LIMIT_SRC, str(flag), str(3 << 30), *args], capture_output=True, env=e, timeout=120)
    assert r.returncode == 0 and "= 1 (Exact)" in r.stdout.decode(), (r.stdout, r.stderr)   # a job limit above the floor checks


@pytest.mark.skipif(os.name != "nt", reason="GlobalMemoryStatusEx is the Windows reading of physical memory")
def test_windows_physical_memory_is_read():
    from reality4 import machine
    lim = machine.memory_limit()
    assert isinstance(lim, int) and lim > 0 and lim == machine._physical()


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="chmod 0 denies reads only to a non-root POSIX user")
def test_manifest_of_a_folder_it_cannot_read_whole_exits_2(tmp_path):
    """(A10, Argon review 10, its repro with chmod for icacls) An unreadable root gave exit 0 and an empty manifest, an
    unreadable sub-folder a partial one (check then formed '1 subject' of a 2-subject dataset), an unreadable file a
    PermissionError traceback (exit 1). Each is exit 2 now, nothing written."""
    d = tmp_path / "d"
    write(str(d / "README"), b"x\n")
    write(str(d / "sub-02" / "a.tsv"), b"a\n")
    for p in (d, d / "sub-02", d / "README"):
        os.chmod(p, 0)
        try:
            rc, out, err = cli("manifest", str(d), "--out", str(tmp_path / "m"))
        finally:
            os.chmod(p, 0o644 if p.name == "README" else 0o755)
        assert rc == 2 and out == "" and "cannot read" in err and "Traceback" not in err and not (tmp_path / "m").exists(), (p, rc, out, err)

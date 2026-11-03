import hashlib
import os
import sys

sys.path.insert(0, os.environ.get("REALITY4_SRC") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from reality4 import readers  # noqa: E402
from reality4.kernel import check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def manifest(root, out_dir):
    """Write root's Reality manifest into out_dir; return its sha256."""
    data = readers.make_manifest(root)
    h = hashlib.sha256(data).hexdigest()
    with open(os.path.join(out_dir, h + ".manifest"), "wb") as f:
        f.write(data)
    return h


def run(prog, files=(), roots=()):
    ok, out = check(prog.encode("ascii") if isinstance(prog, str) else prog, readers.Store(list(files), list(roots)))
    text = "\n".join(out)
    print(text)
    return ok, text


def sha(path):
    return readers.sha256_file(path)[0]


def tsv(tmp, name, text):
    p = os.path.join(str(tmp), name)
    with open(p, "wb") as f:
        f.write(text.encode("utf-8") if isinstance(text, str) else text)
    return p, sha(p)


def unreadable(path):
    """Make path unreadable to this user (POSIX: mode 0; Windows: an ACL entry denying read to
    Everyone, data only, so the ACL itself stays readable) and return the function that undoes it. Skips the calling test if the file can still
    be read afterwards (root, or a privilege that overrides the ACL): then the case cannot be built."""
    import subprocess
    if os.name == "nt":
        subprocess.run(["icacls", path, "/deny", "*S-1-1-0:(RD)"], check=True, capture_output=True)
        undo = lambda: subprocess.run(["icacls", path, "/remove:d", "*S-1-1-0"], check=True, capture_output=True)  # noqa: E731
    else:
        os.chmod(path, 0)
        undo = lambda: os.chmod(path, 0o644)  # noqa: E731
    try:
        open(path, "rb").close()
    except OSError:
        return undo
    undo()
    import pytest
    pytest.skip("this user can still read a file it has no read permission for (root or an ACL override)")


def symlink(target, link):
    """os.symlink(target, link), or skip the calling test when this system refuses to create a symlink.
    Windows creates one only with SeCreateSymbolicLinkPrivilege (an elevated shell or Developer Mode); without it
    os.symlink raises WinError 1314 (ERROR_PRIVILEGE_NOT_HELD), and the case cannot be built (Argon R7). Only that
    refusal, seen by actually attempting the link, skips; any other error fails the test as before."""
    try:
        os.symlink(target, link)
    except OSError as e:
        if getattr(e, "winerror", None) != 1314:
            raise
        import pytest
        pytest.skip("Windows refused to create a symlink (WinError 1314: SeCreateSymbolicLinkPrivilege not held; "
                    "needs an elevated shell or Developer Mode). The junction case is test_v4_fixpass::"
                    "test_w1_a_junction_under_root_is_not_followed")

# Windows: `python -c JOB_LIMIT_SRC FLAG LIMIT ARGS...` runs the checker inside a new job object whose
# process (FLAG 0x100) or job (0x200) memory limit is LIMIT bytes: Windows' counterpart of setrlimit.
JOB_LIMIT_SRC = r'''
import ctypes, runpy, sys
from ctypes import wintypes as W
S, U, k = ctypes.c_size_t, ctypes.c_uint32, ctypes.windll.kernel32
class JL(ctypes.Structure):
    _fields_ = [("t", ctypes.c_int64 * 2), ("flags", U), ("ws", S * 2), ("procs", U), ("aff", S), ("cls", U * 2), ("io", ctypes.c_uint64 * 6), ("proc", S), ("job", S), ("peak", S * 2)]
k.CreateJobObjectW.restype = k.GetCurrentProcess.restype = W.HANDLE
k.SetInformationJobObject.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD]
k.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
flag, limit = int(sys.argv[1]), int(sys.argv[2])
j = JL(flags=flag)
j.proc, j.job = (limit, 0) if flag == 0x100 else (0, limit)
job = k.CreateJobObjectW(None, None)
assert job and k.SetInformationJobObject(job, 9, ctypes.byref(j), ctypes.sizeof(j)), ctypes.GetLastError()
assert k.AssignProcessToJobObject(job, k.GetCurrentProcess()), ctypes.GetLastError()
sys.argv = ["reality4"] + sys.argv[3:]
runpy.run_module("reality4", run_name="__main__", alter_sys=True)
'''

"""Run 09-let-call-by-name-exponential-blowup.rl uncapped vs under a 55 MB Win32 process memory cap."""
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
CMD = [PY, "-m", "reality2", "check", r"findings\09-let-call-by-name-exponential-blowup.rl", "--files", r"findings\09-val.tsv"]
ENV = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"), PYTHONIOENCODING="utf-8")

r1 = subprocess.run(CMD, cwd=ROOT, capture_output=True, env=ENV)
lines1 = r1.stdout.decode().splitlines()
print(f"[Uncapped] rc={r1.returncode}, stdout={len(r1.stdout)} bytes, verdict={lines1[-1]}")

kernel32 = ctypes.windll.kernel32
class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(f, ctypes.c_ulonglong) for f in ("r_op", "w_op", "o_op", "r_tr", "w_tr", "o_tr")]
class BASIC(ctypes.Structure):
    _fields_ = [("u1", ctypes.c_longlong), ("u2", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
                ("minws", ctypes.c_size_t), ("maxws", ctypes.c_size_t), ("ap", wintypes.DWORD),
                ("aff", ctypes.c_size_t), ("pc", wintypes.DWORD), ("sc", wintypes.DWORD)]
class EXT(ctypes.Structure):
    _fields_ = [("Basic", BASIC), ("Io", IO_COUNTERS), ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t), ("PeakProc", ctypes.c_size_t), ("PeakJob", ctypes.c_size_t)]

proc = subprocess.Popen(CMD, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, creationflags=0x4)
job = kernel32.CreateJobObjectW(None, None)
info = EXT()
info.Basic.LimitFlags = 0x100
info.ProcessMemoryLimit = 55 * 1024 * 1024
kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
kernel32.AssignProcessToJobObject(job, int(proc._handle))
ctypes.windll.ntdll.NtResumeProcess(int(proc._handle))
out2, err2 = proc.communicate(timeout=15)
kernel32.CloseHandle(job)
print(f"[55 MB cap] rc={proc.returncode}")
print(out2.decode(errors="replace").strip())

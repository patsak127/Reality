"""Run the reality2 CLI in this process under a Windows job-object memory limit (MB, 0 = none).
Usage: python memlimit_run.py MB check PROGRAM --files ...   The only outside factor is the limit."""
import ctypes, sys
from ctypes import wintypes
mb = int(sys.argv[1])
if mb:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]
    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]
    class EXT(ctypes.Structure):
        _fields_ = [("Basic", BASIC), ("Io", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    info = EXT()
    info.Basic.LimitFlags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info.ProcessMemoryLimit = mb * 1024 * 1024
    assert k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    assert k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(k32.GetCurrentProcess()))
sys.path.insert(0, "src")
from reality2.__main__ import main
out = []
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = main(sys.argv[2:])
for line in buf.getvalue().splitlines():
    print(line[:200])
print("exit", rc)

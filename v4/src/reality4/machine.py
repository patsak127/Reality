"""The memory floor (v4 SPEC 9.4): the checker runs only on a machine whose memory limit is at
least FLOOR bytes, so that no program inside the bounds can run out of memory. Below it nothing
is checked (X002, exit 3). The floor is part of the trusted base (principle section 1)."""

import os
import posixpath   # cgroup paths are POSIX paths on every host
import sys

FLOOR = 2 * 1024 ** 3   # [prov] SPEC 9.4


def _cgroup_max():
    try:
        with open("/proc/self/cgroup", "rb") as f:
            lines = f.read().decode("ascii", "replace").splitlines()
        parts = next(ln[3:].strip() for ln in lines if ln.startswith("0::")).strip("/").split("/")
    except (OSError, StopIteration):
        return None
    vals = []   # the limit in force is the smallest along the path to the root (cgroup v2)
    for i in range(len(parts), -1, -1):
        try:
            with open(posixpath.join("/sys/fs/cgroup", *parts[:i], "memory.max"), "rb") as g:
                v = g.read().strip()
            vals += [] if v == b"max" else [int(v)]
        except (OSError, ValueError):
            pass
    return min(vals) if vals else None


def _physical():
    """Physical memory; on Windows also the memory limits of the process's own job object."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        pass
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes
    SIZE_T = ULONG_PTR = ctypes.c_size_t
    ULONGLONG = ctypes.c_ulonglong

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ULONGLONG), ("ullAvailPhys", ULONGLONG),
                    ("ullTotalPageFile", ULONGLONG), ("ullAvailPageFile", ULONGLONG),
                    ("ullTotalVirtual", ULONGLONG), ("ullAvailVirtual", ULONGLONG),
                    ("ullAvailExtendedVirtual", ULONGLONG)]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", SIZE_T), ("MaximumWorkingSetSize", SIZE_T),
                    ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ULONG_PTR),
                    ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [("ReadOperationCount", ULONGLONG), ("WriteOperationCount", ULONGLONG),
                    ("OtherOperationCount", ULONGLONG), ("ReadTransferCount", ULONGLONG),
                    ("WriteTransferCount", ULONGLONG), ("OtherTransferCount", ULONGLONG)]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T),
                    ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T)]

    JobObjectExtendedLimitInformation = 9
    JOB_OBJECT_LIMIT_PROCESS_MEMORY, JOB_OBJECT_LIMIT_JOB_MEMORY = 0x100, 0x200
    kernel32 = ctypes.windll.kernel32
    vals = []
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        vals.append(int(m.ullTotalPhys))
    j = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    # hJob None: the job of the calling process (its immediate job if jobs are nested)
    if kernel32.QueryInformationJobObject(None, JobObjectExtendedLimitInformation,
                                          ctypes.byref(j), ctypes.sizeof(j), None):
        flags = j.BasicLimitInformation.LimitFlags
        if flags & JOB_OBJECT_LIMIT_PROCESS_MEMORY:
            vals.append(int(j.ProcessMemoryLimit))
        if flags & JOB_OBJECT_LIMIT_JOB_MEMORY:
            vals.append(int(j.JobMemoryLimit))
    return min(vals) if vals else None


def memory_limit():
    """The smallest of RLIMIT_AS, RLIMIT_DATA, the cgroup v2 memory.max of the process and of every
    ancestor, physical memory and (Windows) the job object's limits, or None if none can be read."""
    vals = []
    try:
        import resource
        vals += [s for s in (resource.getrlimit(r)[0] for r in (resource.RLIMIT_AS, resource.RLIMIT_DATA)) if s != resource.RLIM_INFINITY]
    except (ImportError, ValueError, OSError):
        pass
    for v in (_cgroup_max(), _physical()):
        if v is not None:
            vals.append(v)
    return min(vals) if vals else None


def below_floor():
    """None if the machine meets the floor, else the no-verdict line to print."""
    lim = memory_limit()
    if lim is None:
        return f"no verdict: this machine's memory limit cannot be read, so it is not known to reach Reality's floor ({FLOOR} bytes); nothing was checked"
    if lim < FLOOR:
        return f"no verdict: this machine's memory limit ({lim} bytes) is below Reality's floor ({FLOOR} bytes); nothing was checked"
    return None

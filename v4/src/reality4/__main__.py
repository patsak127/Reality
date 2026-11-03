"""python -m reality4 check PROGRAM... [--files PATH...] [--root DIR...]
   python -m reality4 manifest DIR [--out FILE]

check: PROGRAMs are Reality v4 texts. --files: files or folders whose files are supplied by
their SHA-256. --root: dataset roots; a manifest's entries are looked for there by path and
accepted only if their bytes hash to the entry. At least one PROGRAM; `-` (standard input) at
most once; an option other than --files and --root is a usage error. Exit 0 if every program is accepted, 1 if any
is refused, 2 for a usage error, 3 if there is no verdict (the machine is below Reality's memory
floor, or ran out of memory; no verdict is not a refusal).
Output is UTF-8 with LF line ends whatever the terminal or PYTHONIOENCODING says."""

import hashlib
import os
import sys

from . import machine, readers
from .kernel import check


def out(s: str):
    sys.stdout.buffer.write(s.encode("utf-8", errors="backslashreplace") + b"\n")


def usage():
    sys.stderr.buffer.write(__doc__.encode("utf-8") + b"\n")
    return 2


def main(argv):
    if not argv or argv[0] not in ("check", "manifest"):
        return usage()
    cmd, rest = argv[0], argv[1:]
    if cmd == "manifest":
        if len(rest) not in (1, 3) or (len(rest) == 3 and rest[1] != "--out") or rest[0].startswith("--"):
            return usage()
        try:
            data = readers.make_manifest(rest[0])
        except readers.ManifestError as e:
            sys.stderr.buffer.write(f"reality4 manifest: {e}; no manifest written\n".encode("utf-8", "backslashreplace"))
            return 2
        if len(rest) == 3:
            try:
                with open(os.fsencode(rest[2]), "wb") as f:
                    f.write(data)
            except OSError as e:   # O10: a usage error (exit 2), not a refusal and not a traceback
                sys.stderr.buffer.write(f"reality4 manifest: cannot write {rest[2]} ({e.strerror or type(e).__name__}); no manifest written\n".encode("utf-8", "backslashreplace"))
                return 2
            out(f"sha256:{hashlib.sha256(data).hexdigest()}  {rest[2]}")
        else:
            sys.stdout.buffer.write(data)
        return 0
    floor = machine.below_floor()
    if floor is not None:
        out(floor)
        return 3
    progs, files, roots = [], [], []
    cur = progs
    for a in rest:
        if a == "--files":
            cur = files
        elif a == "--root":
            cur = roots
        elif a.startswith("--"):
            return usage()
        else:
            cur.append(a)
    if not progs or progs.count("-") > 1:   # O10: nothing to check, or standard input read twice
        return usage()
    store = readers.Store(files, roots)
    worst = 0
    for p in progs:
        if p == "-":
            prog = sys.stdin.buffer.read()
        else:
            try:
                with open(p, "rb") as f:
                    prog = f.read()
            except OSError as e:
                prog = None
                ok, lines = False, [f"line 0: refused [F001, text]: the program file cannot be read ({e.strerror or type(e).__name__}), so there are no program bytes to check",
                                    "refused: the program is not Reality text"]
        if prog is not None:
            ok, lines = check(prog, store)
        worst = max(worst, 0 if ok else (1 if ok is False else 3))
        if len(progs) > 1:
            out(f"== {p}")
        for line in lines:
            out(line)
    sys.stdout.buffer.flush()
    return worst


def entry(argv):
    try:
        return main(argv)
    except MemoryError:
        # anywhere, printing included: no verdict, never a refusal (v4 SPEC 10)
        try:
            sys.stdout.buffer.write(b"no verdict: the machine ran out of memory; nothing more was checked\n")
            sys.stdout.buffer.flush()
        except Exception:
            pass
        return 3


if __name__ == "__main__":
    sys.exit(entry(sys.argv[1:]))

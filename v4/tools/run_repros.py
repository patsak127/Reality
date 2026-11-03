"""Run every review reproducer program (*.rl) under v3 and print each verdict line.

python3 tools/run_repros.py DIR [DIR...]   (default: tests/repros/*)
Each DIR's files are supplied (--files DIR plus the box copy); every sub-folder holding a
dataset_description.json is a --root, and so is the box copy. Report only."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from reality4 import readers  # noqa: E402
from reality4.kernel import check  # noqa: E402

BOX = os.path.join(HERE, "..", "tests", "data", "ds001734-box")


def roots_in(d):
    out = [BOX]
    for dp, dns, fns in os.walk(d):
        dns.sort()
        if "dataset_description.json" in fns:
            out.append(dp)
    return out


def programs(d):
    for dp, dns, fns in os.walk(d):
        dns.sort()
        for fn in sorted(fns):
            if fn.endswith(".rl"):
                yield os.path.join(dp, fn)


def summary(lines):
    """Per line: 'formed' or the refusal code; or 'no verdict'."""
    out = []
    for ln in lines:
        if ln.startswith("line "):
            n, rest = ln[5:].split(": ", 1)
            out.append(f"{n}:" + ("formed" if rest.startswith("formed") else rest.split("[", 1)[1].split(",", 1)[0]))
        elif ln.startswith("no verdict"):
            out.append("no-verdict")
    return " ".join(out)


def run_all(dirs, out, full=True):
    """One store over every directory (files and roots), as one CLI call with all of them."""
    roots = []
    for d in dirs:
        roots += roots_in(d)
    store = readers.Store(list(dirs) + [BOX], sorted(set(roots)))
    for d in dirs:
        out.write(f"#### {os.path.basename(os.path.normpath(d))}\n")
        run_dir(d, out, store, full)


def run_dir(d, out, store, full):
    for p in programs(d):
        with open(p, "rb") as f:
            prog = f.read()
        ok, lines = check(prog, store)
        rel = os.path.relpath(p, d).replace(os.sep, "/")
        if not full:
            out.write(f"{rel}\t{summary(lines)}\n")
            continue
        out.write(f"== {rel}  [{'accepted' if ok else 'refused' if ok is False else 'no verdict'}]\n")
        for ln in lines:
            if ln.startswith("line ") or ln.startswith("no verdict"):
                out.write("   " + (ln if len(ln) < 400 else ln[:400] + " ...") + "\n")


REPROS = os.path.join(HERE, "..", "tests", "repros")


def default_dirs():
    return sorted(os.path.join(REPROS, x) for x in os.listdir(REPROS) if os.path.isdir(os.path.join(REPROS, x)))


if __name__ == "__main__":
    args = sys.argv[1:]
    full = "--summary" not in args
    dirs = [a for a in args if a != "--summary"] or default_dirs()
    run_all(dirs, sys.stdout, full)

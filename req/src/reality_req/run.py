"""Run an adopted (or trial) measure through the unchanged v4 checker (req/SPEC.md section 7). Trusted.

The program is the data binding (two lines) followed by the fragment's bytes, unchanged. A
condition holds when its line formed and printed 'holds'; it does not hold only on V001 item 5
(G022 keeps 'is' out of fragments, so that code means a contradicted comparison). Anything else
means the measure was NOT CHECKED, and nothing is said about it.
"""
import re

from reality4 import machine, readers
from reality4.kernel import check

from .form import kind

LINE = re.compile(r"line (\d+): (formed|refused) ?(?:\[(\w+), ([\w ]+)\])?: (.*)")


class Runner:
    def __init__(self, files, roots=()):
        self.store = readers.Store(list(files), list(roots))

    def __call__(self, frag, data):
        floor = machine.below_floor()
        if floor is not None:
            return dict(verdict="NOT CHECKED", why=f"the v4 checker gives no verdict: {floor}", shown=[], failed=[])
        prog = f"file d = sha256:{data}\nlet t = tsv(d)\n".encode() + "\n".join(frag).encode("utf-8")
        ok, lines = check(prog, self.store)
        if ok is None:
            return dict(verdict="NOT CHECKED", why="the v4 checker gives no verdict: " + " ".join(lines), shown=[], failed=[])
        return verdict(frag, lines)


def verdict(frag, lines):
    seen, shown, failed, held = {}, [], [], 0
    for ln in lines:
        m = LINE.fullmatch(ln)
        if m:
            seen[int(m.group(1))] = m.groups()[1:]
        elif ln.startswith("line "):    # a result line this reader does not know: say nothing
            return dict(verdict="NOT CHECKED", why=f"the v4 checker printed a line this layer cannot read: {ln}", shown=shown, failed=[])
    for n in sorted(seen):
        status, code, item, text = seen[n]
        fl = n - 2
        k = kind(frag[fl - 1]) if 1 <= fl <= len(frag) else None
        if status == "refused" and not (k == "condition" and (code, item) == ("V001", "item 5")):
            where = f"fragment line {fl}" if fl >= 1 else f"data binding line {n}"
            return dict(verdict="NOT CHECKED", why=f"the v4 checker refused {where} [{code}]: {text}", shown=shown, failed=[])
        if status == "refused":
            failed.append((fl, "v4: " + text))
        elif k == "condition" and text.endswith(" holds"):
            held += 1
        elif k == "shown":
            shown.append((fl, frag[fl - 1].split("#")[0].strip()[6:].strip() + " = " + text.rsplit(" = ", 1)[-1]))
    total = sum(1 for src in frag if kind(src) == "condition")
    if held + len(failed) != total:
        return dict(verdict="NOT CHECKED", why=f"the v4 checker reported {held + len(failed)} of the {total} conditions", shown=shown, failed=[])
    return dict(verdict="HOLDS" if not failed else "DOES NOT HOLD", held=held, total=total, shown=shown, failed=failed)

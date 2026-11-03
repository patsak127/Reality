"""Sorts as trees. A sort is a tuple of parts: fixed text written by the checker's code, a File
(a file named by hash), a Lit (bytes the program wrote, printed escaped), or another sort.
Files are found by walking the tree, never by searching printed text, so no byte literal can
become a file (v2 hit 1). Size (sorts, files and byte literals, 1 each; text 0) and depth are bounded when a sort is made, so printing is
bounded too (principle item 4)."""

from .readers import Refusal

MAX_SORT_SIZE = 100_000
MAX_SORT_DEPTH = 400


class File:
    __slots__ = ("h",)

    def __init__(self, h):
        self.h = h

    def __eq__(self, o):
        return isinstance(o, File) and o.h == self.h

    def __hash__(self):
        return hash(("File", self.h))


class Lit:
    __slots__ = ("b",)

    def __init__(self, b):
        self.b = b

    def __eq__(self, o):
        return isinstance(o, Lit) and o.b == self.b

    def __hash__(self):
        return hash(("Lit", self.b))


class S:
    __slots__ = ("parts", "size", "depth", "meta", "_h")

    def __init__(self, *parts, meta=None):
        size, depth = 1, 0
        for p in parts:
            if isinstance(p, S):
                size += p.size
                depth = max(depth, p.depth)
            elif isinstance(p, File):
                size += 1
            elif isinstance(p, Lit):
                size += len(p.b) // 64 + 1   # v4 SPEC 9.2: a literal counts by its length
            elif not isinstance(p, str):
                raise TypeError(type(p))
            # fixed text (template text, labels, cutoffs, tolerances) counts 0: how a template's
            # text is split into parts is an implementation detail (SPEC 9.8, R006)
        if size > MAX_SORT_SIZE or depth + 1 > MAX_SORT_DEPTH:
            raise Refusal("R006", "bounds", f"the claim's sort would have more than {MAX_SORT_SIZE} parts or nest deeper than {MAX_SORT_DEPTH} (Reality bounds)")
        self.parts, self.size, self.depth, self.meta = parts, size, depth + 1, meta
        self._h = None

    def __eq__(self, o):
        return isinstance(o, S) and o.parts == self.parts

    def __hash__(self):
        if self._h is None:
            self._h = hash(self.parts)
        return self._h


def esc(b: bytes) -> str:
    out = []
    for x in b:
        if x == 34:
            out.append('\\"')
        elif x == 92:
            out.append("\\\\")
        elif 32 <= x < 127:
            out.append(chr(x))
        else:
            out.append(f"\\x{x:02x}")
    return '"' + "".join(out) + '"'


def nodes(s: S):
    """Every sub-sort and leaf, depth first, left to right (iterative)."""
    stack = [s]
    while stack:
        x = stack.pop()
        yield x
        if isinstance(x, S):
            stack.extend(reversed(x.parts))


def files(s: S):
    out = []
    for x in nodes(s):
        if isinstance(x, File) and x.h not in out:
            out.append(x.h)
    return out


def render(s: S, labels: dict) -> str:
    out = []
    for x in nodes(s):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, File):
            out.append(labels[x.h])
        elif isinstance(x, Lit):
            out.append(esc(x.b))
    return "".join(out)

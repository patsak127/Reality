"""Exact-decision phase 5 check: every S008/S011 the exact path gives on the generated part-H family
(tools/exact_diff.py part_h_family) is re-checked by brute force. Report only, untrusted.

Inputs per slot the statement reads: JSON g: every document whose named nodes are each a number from
NUMS, the string "s", null, an object holding any subset of its named keys, or an array of 0 to 4 items (each
a number or the named node); NIfTI n: NIfTI-1/2 headers with dim[0] 1 to 5 and each named dim from DIMS
(40000 needs NIfTI-2); raw r: sizes 0 to 22 and two byte patterns. Ground truth as tools/exact_bf.py.
python3 tools/exact_bfH.py [MAXSPACE]"""
import itertools
import json
import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src"), os.path.join(HERE, "..", "tests"), HERE]
import exact_bf as B  # noqa: E402
import exact_diff as X  # noqa: E402
from reality4 import witness as W, readers as R, decide as D  # noqa: E402
from reality4.kernel import Checker, check  # noqa: E402
from reality4.syntax import parse_line  # noqa: E402

NUMS = [0, 2, 4, 10, 31, 2.5]
DIMS = [1, 2, 3, 63, 64, 65, 32767, 40000]


def jdocs(paths):
    """Every document over the named trie (values of each node as the docstring says)."""
    nodes = sorted({p[:i] for p in paths for i in range(len(p) + 1)}, key=lambda p: (len(p), repr(p)))

    def build(p):
        kids = [q for q in nodes if len(q) == len(p) + 1 and q[:-1] == p]
        opts = [json.dumps(v) for v in NUMS] + ['"s"', "null"]
        mk = [q for q in kids if q[-1][0] == "m"]
        ik = sorted(q[-1][1] for q in kids if q[-1][0] == "i")
        for sub in itertools.product(*[[None] + list(build(q)) for q in mk]):
            opts.append("{" + ", ".join(json.dumps(q[-1][1].decode()) + ": " + v for q, v in zip(mk, sub) if v is not None) + "}")
        byi = {q[-1][1]: q for q in kids if q[-1][0] == "i"}
        for n in range(0, 5):
            for sub in itertools.product(*[list(build(byi[i])) if i in byi else ["1"] for i in range(1, n + 1)]):
                opts.append("[" + ", ".join(sub) + "]")
            if len(opts) > 400:
                break
        return opts[:400]
    return [d.encode() for d in build(())]


def nii(dims):
    if max(dims) <= 32767:
        return W._nii(dims, 1, data=False)
    b = bytearray(544)
    struct.pack_into("<i", b, 0, 540)
    b[4:12] = b"n+2\x00\r\n\x1a\n"
    struct.pack_into("<2h", b, 12, 2, 8)
    struct.pack_into("<8q", b, 16, len(dims), *dims, *[1] * (7 - len(dims)))
    struct.pack_into("<8d", b, 104, 1, 1, 1, 1, 1, 0, 0, 0)
    struct.pack_into("<q", b, 168, 544)
    struct.pack_into("<i", b, 500, 10)
    return bytes(b)


def space(stmt, e):
    sl = {}
    paths = [D.jpath(x)[1] for x in W.walk(e) if hasattr(x, "fn") and x.fn in ("member", "item")]
    if "json(g)" in stmt:
        sl["g"] = jdocs(paths)
    if "nifti(n)" in stmt:
        ks = sorted({int(k) for k in re.findall(r"dim\(nifti\(n\), (\d)\)", stmt)})
        sl["n"] = [nii([dict(zip(ks, v)).get(k, 1) for k in range(1, d0 + 1)]) for d0 in range(1, 6) for v in itertools.product(DIMS, repeat=len(ks))]
    if "(r" in stmt:
        sl["r"] = [bytes((7 * i + p) % 256 for i in range(n)) for n in range(23) for p in (1, 2)]
    return sl


def truth(stmt, maxspace):
    e = parse_line(f"claim {stmt}", 1).expr
    sl = space(stmt, e)
    names = sorted(sl)
    vals = W.subexprs(e)
    answers = {id(v): set() for v in vals}
    parts = [(node, mod, [(x, W._subst(x, node, mod)) for x in W._path(e, node)]) for node, mod, _ in W.parts(e)]
    bears = [False] * len(parts)
    combos = list(itertools.islice(itertools.product(*[sl[n] for n in names]), maxspace))
    for combo in combos:
        a = dict(zip(names, combo))
        g = W.evaluate(Checker, e, names, a, [0])
        if g is None:
            continue
        for v in vals:
            if id(v) in g:
                answers[id(v)].add(g[id(v)])
        for i, (node, mod, levels) in enumerate(parts):
            for top, whole in levels:
                a1 = B.outcome(W.evaluate(Checker, top, names, a, [0]), top)
                a2 = B.outcome(W.evaluate(Checker, whole, names, a, [0]), whole)
                if a1 is None:
                    break
                if a2 is None:
                    continue
                bears[i] = bears[i] or a1 != a2
                break
    return [len(answers[id(v)]) for v in vals], bears, len(combos)


def main(argv):
    maxspace = int(argv[0]) if argv else 20000
    tmp = tempfile.mkdtemp()
    files = X.part_h_files(tmp)
    head = "".join(f"file {n} = sha256:{h}\n" for n, (_, h) in sorted(files.items()))
    n = bad = 0
    for k, stmt in enumerate(X.part_h_family()):
        B.WHICH.clear()
        ok, out = check((head + f"claim {stmt}\n").encode(), R.Store([f for f, _ in files.values()]))
        line = next(ln for ln in out if ln.startswith("line 4"))
        if "decided exactly" not in line:
            continue
        n += 1
        w1, bears, size = truth(stmt, maxspace)
        kind, i = B.WHICH[-1]
        contra = (w1[i] >= 2) if kind == "W1" else bears[i]
        bad += bool(contra)
        print(f"ph{k:03d}\t{'CONTRADICTED' if contra else 'agrees'}\t{kind} #{i}\t{size} inputs\tW1 answers {w1}\tW2 bears {bears}\t{line[:150]}")
    print(f"{n} exact refusals re-checked; {bad} contradicted")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Exact-decision phase 3 check (plan section 7.2): every S008/S011 the exact path gives on the generated
part-T family is re-checked by brute force. Report only, untrusted.

For each refused statement, the space is every table of at most ROWS rows whose cells are, per column,
the statement's literals for that column and one other value (header group, site, sex). Ground truth as
tests/test_v4_bruteforce.py: W1 = two different answers somewhere in the space; W2 = some table on which
the statement with and without a part answer differently (a value refusal is an outcome).
A refusal is contradicted when the space shows the opposite. python3 tools/exact_bf.py [ROWS]"""
import itertools
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src"), os.path.join(HERE, "..", "tests"), HERE]
import exact_diff as X  # noqa: E402
import helpers  # noqa: E402
from reality4 import witness as W, readers as R  # noqa: E402
from reality4.kernel import Checker, check  # noqa: E402
from reality4.syntax import parse_line  # noqa: E402
from reality4 import decide as D  # noqa: E402

WHICH = []   # (kind, index) of the question the exact path answered "no"
_w1, _w2 = D.Decide.w1, D.Decide.w2


def w1(self, e):
    r = _w1(self, e)
    if r is not None:
        WHICH.append(("W1", [id(x) for x in W.subexprs(self.expr)].index(id(e))))
    return r


def w2(self, node, mod):
    r = _w2(self, node, mod)
    if not r:
        WHICH.append(("W2", [(id(x[0]), x[1]) for x in W.parts(self.expr)].index((id(node), mod))))
    return r


D.Decide.w1, D.Decide.w2 = w1, w2

COLS = ["group", "site", "sex"]


def outcome(g, e):
    if g is None:
        return None
    if id(e) in g:
        return g[id(e)]
    code = g.get("refused") or ""
    return ("V", code) if code[:1] == "V" else None


def space(stmt, rows):
    lits = [sorted(set(re.findall(r'"%s", "([^"]*)"' % c, stmt))) + ["o"] for c in COLS]
    kinds = list(itertools.product(*lits))
    for n in range(rows + 1):
        for rs in itertools.combinations_with_replacement(kinds, n):
            yield ("group\tsite\tsex\n" + "".join("\t".join(r) + "\n" for r in rs)).encode()


def truth(stmt, rows):
    e = parse_line(f"claim {stmt}", 1).expr
    vals = W.subexprs(e)
    answers = {id(v): set() for v in vals}
    parts = [(node, mod, desc, [(x, W._subst(x, node, mod)) for x in W._path(e, node)]) for node, mod, desc in W.parts(e)]
    bears = [False] * len(parts)
    for t in space(stmt, rows):
        g = W.evaluate(Checker, e, ["f"], {"f": t}, [0])
        if g is None:
            continue
        for v in vals:
            a = g.get(id(v))
            if a is not None:
                answers[id(v)].add(a)
        for i, (node, mod, desc, levels) in enumerate(parts):
            if bears[i]:
                continue
            for top, whole in levels:
                a1 = outcome(W.evaluate(Checker, top, ["f"], {"f": t}, [0]), top)
                a2 = outcome(W.evaluate(Checker, whole, ["f"], {"f": t}, [0]), whole)
                if a1 is None:
                    break
                if a2 is None:
                    continue
                bears[i] = a1 != a2
                break
    return [len(answers[id(v)]) for v in vals], bears


def main(argv):
    rows = int(argv[0]) if argv else 2
    tmp = tempfile.mkdtemp()
    p, h = helpers.tsv(tmp, "g.tsv", X.PART_T_TABLE)
    n = bad = 0
    for k, stmt in enumerate(X.part_t_family()):
        WHICH.clear()
        ok, out = check(f"file f = sha256:{h}\nclaim {stmt}\n".encode(), R.Store([p]))
        line = next(ln for ln in out if ln.startswith("line 2"))
        if "decided exactly" not in line:
            continue
        n += 1
        w1, bears = truth(stmt, rows)
        kind, i = WHICH[-1]
        contra = (w1[i] >= 2) if kind == "W1" else bears[i]
        bad += bool(contra)
        print(f"pt{k:03d}\t{'CONTRADICTED' if contra else 'agrees'}\t{kind} #{i}\tW1 answers {w1}\tW2 bears {bears}\t{line[:160]}")
    print(f"{n} exact refusals re-checked over tables of at most {rows} rows; {bad} contradicted")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Finding 18: reality2 and reality2_ref disagree once 'is' is part of the claim, which
tests/test_differential.py never exercises (its kernel_eval writes no 'is', its ref.evaluate call
passes no is_), although ref.py's docstring lists "with 'is'".

    python -I findings\\18-diff-is.py

Part 1: the two claims of 18-differential-is.rl, given to both implementations.
Part 2: the test's own random tables and queries (tests/test_differential.py: table, query, text),
each claim given an 'is' literal that is right or wrong at random, compared on both sides."""
import os
import random
import shutil
import sys
import tempfile
from fractions import Fraction

F = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(F)
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "tests")]
import helpers  # noqa: E402
import test_differential as TD  # noqa: E402
from reality2 import readers as R  # noqa: E402
from reality2.kernel import Checker  # noqa: E402
from reality2.readers import Refusal  # noqa: E402
from reality2.syntax import SyntaxRefusal, parse_line  # noqa: E402
from reality2_ref import ref  # noqa: E402


def kernel(store, h, text):
    ck = Checker(store)
    ck.statement(parse_line(f"file f = sha256:{h}", 1))
    try:
        ck.statement(parse_line("let t = tsv(f)", 2))
        ck.statement(parse_line("claim " + text, 3))
    except (Refusal, SyntaxRefusal) as e:
        return ("refused", e.code)
    return ("formed",)


def norm(r):
    return ("formed",) if r[0] == "formed" else r


# Part 1
data = open(os.path.join(F, "18-table.tsv"), "rb").read()
h = R.sha256_file(os.path.join(F, "18-table.tsv"))[0]
store = R.Store([os.path.join(F, "18-table.tsv")])
print("Part 1: the claims of 18-differential-is.rl")
for text, q, lit in [
        ('share(where(t, eq(2, "A"))) is 1/3', ("share", (("eq", ("pos", 2), b"A"),)), Fraction(1, 3)),
        ("exceeds(number(cell(t, 1, 3)), c = 0) is 1", ("exceeds", ("number", ("cell", ("pos", 1), ("pos", 3))), Fraction(0)), 1)]:
    print(f"  claim {text}\n    reality2:     {kernel(store, h, text)}\n    reality2_ref: {norm(ref.evaluate(data, q, lit))}")

# Part 2
rng = random.Random(5)
tmp = tempfile.mkdtemp(dir=os.path.join(ROOT, "scratch"))
disagree, n = {}, 0
for i in range(600):
    data, nc = TD.table(rng)
    p, h = helpers.tsv(tmp, f"t{i}.tsv", data)
    store = R.Store([p])
    for _ in range(8):
        q = TD.query(rng, nc)
        r0 = ref.evaluate(data, q)
        if r0[0] != "formed":
            continue
        kind, val = r0[1]
        right = rng.random() < 0.5
        if kind == "bytes":
            lit = val if right else val + b"x"
            lt = TD.esc(lit)
        elif kind == "count":
            lit = val if right else val + 1
            lt = str(lit)
        elif kind == "share":
            lit = Fraction(*val) if right else Fraction(val[0] + 1, val[1] + 1)
            lt = f"{lit.numerator}/{lit.denominator}"
        elif kind == "num":
            if val[0] < 0:                 # keep to literals the grammar has (no negative ratios)
                continue
            lit = val[0] if right else val[0] + 1
            lt = f"{lit.numerator}/{lit.denominator}" if lit.denominator != 1 else str(lit.numerator)
        else:
            lit, lt = 1, "1"
        text = TD.text(q) + " is " + lt
        a = kernel(store, h, text)
        b = norm(ref.evaluate(data, q, lit))
        n += 1
        if a != b:
            disagree.setdefault((kind, a, b), []).append(text)
print(f"\nPart 2: {n} random claims with 'is'; {sum(len(v) for v in disagree.values())} disagreements")
for k, v in sorted(disagree.items(), key=lambda kv: -len(kv[1])):
    print(f"  {len(v)} x kind={k[0]}: reality2 {k[1]}, reality2_ref {k[2]}; e.g. claim {v[0][:120]}")
shutil.rmtree(tmp)                      # the random tables are temporary

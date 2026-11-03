"""Compare reality2 and reality2_ref on the same table and claims, including 'is' (which
tests/test_differential.py never passes to the reference) and long decimals."""
import sys, os, tempfile, hashlib
from fractions import Fraction
sys.path[:0] = ["src", "tests"]
from reality2 import readers as R
from reality2.kernel import Checker
from reality2.readers import Refusal
from reality2.syntax import SyntaxRefusal, parse_line
from reality2_ref import ref

def kernel(data, claim):
    d = tempfile.mkdtemp(dir="scratch"); p = os.path.join(d, "t.tsv"); open(p, "wb").write(data)
    h = hashlib.sha256(data).hexdigest(); ck = Checker(R.Store([p]))
    ck.statement(parse_line(f"file f = sha256:{h}", 1))
    try:
        ck.statement(parse_line("let t = tsv(f)", 2))
        m, _, v = ck.statement(parse_line("claim " + claim, 3))
        return ("formed", v)
    except (Refusal, SyntaxRefusal) as e:
        return ("refused", e.code)
    except Exception as e:
        return ("EXCEPTION", type(e).__name__)

def reference(data, q, is_=None):
    try:
        return ref.evaluate(data, q, is_)
    except Exception as e:
        return ("EXCEPTION", type(e).__name__)

T = b"g\nA\nA\nB\n"
cases = [
    ("share 2/3 claimed as 1/3", T, 'share(where(t, eq(1, "A"))) is 1/3', ("share", (("eq", ("pos", 1), b"A"),)), Fraction(1, 3)),
    ("count 2 claimed as 5", T, 'count(where(t, eq(1, "A"))) is 5', ("count", (("eq", ("pos", 1), b"A"),)), 5),
    ("row 0", T, 'cell(t, 0, 1)', ("cell", ("pos", 0), ("pos", 1)), None),
    ("5000-digit decimal", b"v\n" + b"1" * 5000 + b"\n", 'number(cell(t, 1, 1))', ("number", ("cell", ("pos", 1), ("pos", 1))), None),
]
for name, data, claim, q, is_ in cases:
    print(f"{name}:\n  reality2     {kernel(data, claim)}\n  reality2_ref {reference(data, q, is_)}")

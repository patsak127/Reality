"""Compare reality2.kernel.check against reality2_ref.ref.evaluate on 16-table.tsv."""
import hashlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from reality2 import readers as R
from reality2.kernel import check
from reality2_ref import ref

p = os.path.join(ROOT, "findings", "16-table.tsv")
raw = open(p, "rb").read()
h = hashlib.sha256(raw).hexdigest()

cases = [
    ("row=0", ("cell", ("pos", 0), ("pos", 2)), None, f"file f = sha256:{h}\nclaim cell(tsv(f), 0, 2)\n"),
    ("row=-5", ("cell", ("pos", -5), ("pos", 2)), None, f"file f = sha256:{h}\nclaim cell(tsv(f), -5, 2)\n"),
    ("col=0", ("cell", ("pos", 1), ("pos", 0)), None, f"file f = sha256:{h}\nclaim cell(tsv(f), 1, 0)\n"),
    ("widen tol=-5", ("widen", ("number", ("cell", ("pos", 1), ("pos", 2))), -5), None,
     f"file f = sha256:{h}\nclaim widen(number(cell(tsv(f), 1, 2)), tolerance = -5)\n"),
    ("share false is_", ("share", (("eq", ("pos", 1), b"a"),)), (99, 100),
     f'file f = sha256:{h}\nclaim share(where(tsv(f), eq(1, "a"))) is 99/100\n'),
    ("exceeds with is_", ("exceeds", ("number", ("cell", ("pos", 1), ("pos", 2))), 5), True,
     f"file f = sha256:{h}\nclaim exceeds(number(cell(tsv(f), 1, 2)), c = 5) is 1\n"),
    ("@<64-hex> literal", ("count", (("eq", ("pos", 1), b"@" + b"0" * 64),)), 0,
     f'file f = sha256:{h}\nclaim count(where(tsv(f), eq(1, "@{"0"*64}"))) is 0\n'),
]

for name, expr, is_val, prog in cases:
    try:
        r_ref = repr(ref.evaluate(raw, expr, is_=is_val))
    except Exception as ex:
        r_ref = f"CRASH {type(ex).__name__}: {ex}"
    _, out_k = check(prog.encode(), R.Store([p]))
    print(f"[{name}]\n  reality2_ref : {r_ref}\n  reality2     : {out_k[0]}")

"""Finding 13: write a TSV whose column 1 has N distinct cells ("k0", "k1", ...) and a program
that selects one row with eq(). Deterministic.

    python -I findings\\13-gen.py N
writes findings\\13-distinct-N.tsv and findings\\13-where-lookalike-quadratic-N.rl"""
import hashlib
import os
import sys

F = os.path.dirname(os.path.abspath(__file__))
n = int(sys.argv[1])
data = ("id\tv\n" + "".join(f"k{i}\t{i % 7}\n" for i in range(n))).encode("ascii")
with open(os.path.join(F, f"13-distinct-{n}.tsv"), "wb") as f:
    f.write(data)
h = hashlib.sha256(data).hexdigest()
with open(os.path.join(F, f"13-where-lookalike-quadratic-{n}.rl"), "w", newline="\n", encoding="ascii") as f:
    f.write(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim rows(t)\nclaim count(where(t, eq(1, \"k5\")))\n")
print(f"13-distinct-{n}.tsv: {len(data)} bytes")

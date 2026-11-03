"""Write a one-column TSV of N distinct keys (k0000001 ...) and a program counting one value."""
import sys, hashlib
n, tsv, rl = int(sys.argv[1]), sys.argv[2], sys.argv[3]
data = ("v\n" + "".join(f"k{i:07d}\n" for i in range(n))).encode()
open(tsv, "wb").write(data)
h = hashlib.sha256(data).hexdigest()
open(rl, "w", newline="\n").write(f"file f = sha256:{h}\nclaim count(where(tsv(f), eq(1, \"zz\")))\n")

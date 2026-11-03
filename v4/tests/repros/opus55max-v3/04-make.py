"""Finding 04: writes 04-one.tsv and 04-memory.rl (33 KB, within every bound of SPEC 9.8).
14 lets double a sort whose two byte literals are 4096 bytes each; the claim's sort has
98 303 nodes (bound 100 000) and prints 16 384 copies of a literal: one 269 MB output line."""
import hashlib
data = b"a\nb\n"
open("04-one.tsv", "wb").write(data)
h = hashlib.sha256(data).hexdigest()
L1 = "\\xc3\\xa9" * 2048                  # U+00E9 x 2048 = 4096 bytes, printed as \xc3\xa9 ...
L2 = "\\xc3\\xa9" * 2047 + "e"
lines = [f"file f = sha256:{h}", "let t = tsv(f)",
         f'let a0 = count(where(t, ne(1, "{L1}")))', f'let b0 = count(where(t, ne(1, "{L2}")))']
for i in range(14):
    lines += [f"let a{i + 1} = difference(a{i}, b{i})", f"let b{i + 1} = difference(b{i}, a{i})"]
lines.append("claim a14")
open("04-memory.rl", "w").write("\n".join(lines) + "\n")

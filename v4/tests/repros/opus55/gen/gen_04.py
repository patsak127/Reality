"""Write findings/04-let-doubling-K.rl: K lets, each the difference of the previous with itself."""
import sys
k = int(sys.argv[1])
h = "7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b"  # findings/02-t.tsv
# a numeric cell is needed: use findings/04-n.tsv
h = sys.argv[2]
lines = [f"file f = sha256:{h}", "let x0 = number(cell(tsv(f), 1, 1))"]
for i in range(1, k + 1):
    lines.append(f"let x{i} = difference(x{i-1}, x{i-1})")
lines.append(f"claim below(x{k}, c = 1)")
open(sys.argv[3], "w", newline="\n").write("\n".join(lines) + "\n")

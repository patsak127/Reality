"""Programs used by the renaming and mutation fuzzers: the acceptance programs on the box copy,
plus programs over a small table."""
import acceptance as A

SMALL = "id\tgroup\tage\ns1\tA\t30\ns2\tB\t41\ns3\tB\t29.5\n"


def programs(box_hash, small_hash):
    out = []
    for cid, fixture, prog, expect, _ in A.CASES:
        if fixture == "box":
            out.append(prog.format(BOX=box_hash, P=A.P, EV=A.EV))
    t = f"file t = sha256:{small_hash}\n"
    out += [
        t + "let tab = tsv(t)\nlet sel = where(tab, eq(2, \"B\"))\nclaim count(sel) is 2\nclaim share(sel)\nclaim sum(sel, 3)\n",
        t + "let tab = tsv(t)\nlet m = max(tab, \"age\")\nclaim exceeds(widen(m, tolerance = 1), c = 39)\nclaim below(m, c = 50)\nclaim difference(m, min(tab, 3))\n",
        t + "file u = sha256:" + A.P + "\nlet x = tsv(u)\nlet y = tsv(t)\nclaim rows(x)\nclaim rows(y)\nclaim cell(y, key(1, \"s2\"), \"group\") is \"B\"\nclaim header(x, 3)\n",
        t + "let a = tsv(t)\nlet a2 = a\nlet c = where(a2, ne(2, \"A\"))\nclaim count(c)\nclaim number(cell(a, 3, 3)) is 29.5\nclaim bytes(t, 0, 2) is \"id\"\nclaim size(t)\n",
        t + "let q = tsv(t)\nlet q = tsv(t)\nclaim rows(zz)\nlet bad = nothing(q)\nclaim count(bad)\nclaim exceeds(max(q, 3), c = 41)\n",
    ]
    return out

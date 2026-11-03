"""Exact-decision phase 3 check for the part-T additions (BB's ruling 3: number conditions, cell() by
position and key, header(), number()): every S008/S011 the exact path gives on the generated family
tools/exact_diff.py part_t2_family() is re-checked by brute force. Report only, untrusted.

For each refused statement the space is every table of at most ROWS rows (row order kept when the
statement names a row by position) over the columns group, site, age: per column the statement's
literals for it and one other value; age also takes the decimals -5, 0, 0.4, 7, 10, 12.5, 30 and
"n/a"; a header cell the statement reads also takes "5" and "-1". Columns the statement does not
read hold one value. With more than MAXSPACE tables, ROWS - 1 is used (printed).
Ground truth as tools/exact_bf.py. python3 tools/exact_bf2.py [ROWS] [partT2|partN|partV]
partN (phase 4): columns group, site, age, score of PART_N_TABLE; age and score take the decimals
-5, 0, 0.4, 2, 7, 10, 12.5, 30 and "n/a"; rows are kept unordered (no named rows in part N)."""
import itertools
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src"), os.path.join(HERE, "..", "tests"), HERE]
import exact_bf as B  # noqa: E402  (its hooks record which question the exact path answered "no")
import exact_diff as X  # noqa: E402
import helpers  # noqa: E402
from reality4 import readers as R  # noqa: E402
from reality4.kernel import check  # noqa: E402

COLS = ["group", "site", "age"]
AGES = ["-5", "0", "0.4", "7", "10", "12.5", "30", "n/a"]
NUMCOLS = {"age"}
MAXSPACE = 40000


def space(stmt, rows):
    used = [bool(re.search(r'(?:"%s"|\(t?[^()]*\b%d\))' % (c, i + 1), stmt)) or f'"{c}"' in stmt or re.search(r", %d\)" % (i + 1), stmt) for i, c in enumerate(COLS)]
    vals = []
    for i, c in enumerate(COLS):
        lit = sorted(set(re.findall(r'"%s", "([^"]*)"' % c, stmt) + re.findall(r'\b%d, "([^"]*)"' % (i + 1), stmt)))
        if not used[i] and not lit:
            vals.append(["p" if c not in NUMCOLS else "1"])
        elif c in NUMCOLS:
            vals.append(sorted(set(AGES + lit)))
        else:
            vals.append(lit + ["o"])
    hk = [int(k) for k in re.findall(r"header\(tsv\(f\), (\d)\)", stmt)]
    heads = [list(h) for h in itertools.product(*[[c] + (["5", "-1"] if i + 1 in hk else []) for i, c in enumerate(COLS)])]
    kinds = list(itertools.product(*vals))
    ordered = "cell(" in stmt
    while True:
        n = sum((len(kinds) ** k if ordered else len(list(itertools.combinations_with_replacement(range(len(kinds)), k)))) for k in range(rows + 1)) * len(heads)
        if n <= MAXSPACE or rows <= 1:
            break
        rows -= 1
    out = []
    for hd in heads:
        for k in range(rows + 1):
            for rs in (itertools.product(kinds, repeat=k) if ordered else itertools.combinations_with_replacement(kinds, k)):
                out.append(("\t".join(hd) + "\n" + "".join("\t".join(r) + "\n" for r in rs)).encode())
    return out, rows


def main(argv):
    global COLS, AGES, NUMCOLS
    rows = int(argv[0]) if argv else 3
    fam = argv[1] if len(argv) > 1 else "partT2"
    tmp = tempfile.mkdtemp()
    if fam in ("partN", "partV"):
        COLS, AGES, NUMCOLS = ["group", "site", "age", "score"], ["-5", "0", "0.4", "2", "7", "10", "12.5", "30", "n/a"], {"age", "score"}
    p, h = helpers.tsv(tmp, "g.tsv", X.PART_N_TABLE if fam in ("partN", "partV") else X.PART_T2_TABLE)
    n = bad = 0
    for k, stmt in enumerate({"partN": X.part_n_family, "partV": X.part_v_family}.get(fam, X.part_t2_family)()):
        B.WHICH.clear()
        ok, out = check(f"file f = sha256:{h}\nclaim {stmt}\n".encode(), R.Store([p]))
        line = next(ln for ln in out if ln.startswith("line 2"))
        if "decided exactly" not in line:
            continue
        n += 1
        sp, used = space(stmt, rows)
        B.space = lambda s, r, sp=sp: iter(sp)
        w1, bears = B.truth(stmt, used)
        kind, i = B.WHICH[-1]
        contra = (w1[i] >= 2) if kind == "W1" else bears[i]
        bad += bool(contra)
        print(f"{ {'partN': 'pn', 'partV': 'pv'}.get(fam, 'pu')}{k:03d}\t{'CONTRADICTED' if contra else 'agrees'}\t{kind} #{i}\trows {used}, {len(sp)} tables\tW1 answers {w1}\tW2 bears {bears}\t{line[:150]}")
    print(f"{n} exact refusals re-checked over tables of at most {rows} rows (fewer where printed); {bad} contradicted")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

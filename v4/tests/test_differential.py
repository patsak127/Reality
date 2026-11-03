"""Differential test on full program text: reality4 (the checker) against reality4_ref (a
second implementation written separately, with its own parser, readers, skeleton and printing).

Random tables hold every TSV ambiguity the reader refuses, lookalike and invisible cells and
headers; random programs use every computation of the plain-TSV fragment, including 'is' with
right and wrong values of every kind, positions of 0 and below, negative and zero tolerances,
ratio cutoffs, difference() (also of a value with itself), composite keys, nested where(), and
programs that widen one value with two tolerances (call 4). The two must agree on every line:
the same refusal code, or a formed claim whose printed value is the same."""
import os
import random
import re

import helpers
from reality4 import readers as R
from reality4.kernel import check
from reality4_ref import ref

HEADS = [b"id", b"group", b"age", b"ID", b"gr\xd0\xbeup", b"a_b", b"", b"rn", b"m", b"x y", b"Id", b"v\xe2\x80\x8b"]
CELLS = [b"s1", b"sl", b"s2", b"A", b"B", b"b", b"30", b"-4.5", b"1.", b"n/a", b"equalRange", b"equaIRange",
         b"\xc3\xa9", b"e\xcc\x81", b"", b"0", b"O", b"12", b"007", b"2.250", b"rn", b"m", b'"q"', b"\\",
         b"x\xc2\xa0", b"t ", b"S1", b"\xd0\x851"]
LITS = [b"s1", b"A", b"B", b"30", b"12", b"rn", b"zz", b"\xc3\xa9", b"S1", b"x\ty", b"\xff", b"equalRange", b"007"]


CLEAN_HEADS = [b"id", b"group", b"age", b"a_b"]
CLEAN_CELLS = [b"s1", b"s2", b"A", b"B", b"30", b"12", b"-4.5", b"2.250", b"n/a", b"equalRange", b"7"]


def table(rng):
    nc = rng.randint(1, 4)
    clean = rng.random() < 0.5
    head = [rng.choice(CLEAN_HEADS if clean else HEADS) for _ in range(nc)]
    rows = [[rng.choice(CLEAN_CELLS if clean else CELLS) for _ in range(nc)] for _ in range(rng.randint(0, 6))]
    data = b"\n".join(b"\t".join(r) for r in [head] + rows) + (b"\n" if rng.random() < 0.8 else b"")
    if rng.random() < 0.04:
        data = data.replace(b"\n", b"\r\n", 1)
    if rng.random() < 0.03:
        data = b"\xef\xbb\xbf" + data
    if rng.random() < 0.03:
        data = data + b"\n"
    if rng.random() < 0.03 and rows:
        data = data + b"x\t" * nc + b"\n"
    if rng.random() < 0.02:
        data = data + b"\xff\n"
    if rng.random() < 0.02:
        data = data + b"a\xe2\x80\xa8b\n"
    if rng.random() < 0.01:
        data = b""
    return data, nc


def lit(b):
    return ref.esc(b)


def col(rng, nc):
    if rng.random() < 0.6:
        return str(rng.choice([0, -1] + list(range(1, nc + 2))) if rng.random() < 0.1 else rng.randint(1, nc + 1))
    return lit(rng.choice(HEADS))


def cond(rng, nc):
    return f"{rng.choice(['eq', 'ne'])}({col(rng, nc)}, {lit(rng.choice(LITS + CELLS))})"


def sel(rng, nc, depth=0):
    inner = "t" if depth or rng.random() < 0.8 else sel(rng, nc, 1)
    return f"where({inner}, " + ", ".join(cond(rng, nc) for _ in range(rng.randint(1, 2))) + ")"


def row(rng, nc):
    x = rng.random()
    if x < 0.55:
        return str(rng.choice([0, -5, 1, 2, 3, 4, 7]))
    pairs = [f"{col(rng, nc)}, {lit(rng.choice(LITS + CELLS))}" for _ in range(1 if x < 0.85 else 2)]
    return "key(" + ", ".join(pairs) + ")"


def tol(rng):
    return rng.choice(["-5", "0", "0.5", "1", "2.5", "1/2"])


def numq(rng, nc, depth=0):
    x = rng.random()
    if x < 0.3 or depth > 1:
        return f"number(cell(t, {row(rng, nc)}, {col(rng, nc)}))"
    if x < 0.6:
        return f"{rng.choice(['sum', 'mean', 'max', 'min'])}({sel(rng, nc) if rng.random() < 0.5 else 't'}, {col(rng, nc)})"
    if x < 0.8:
        return f"widen({numq(rng, nc, depth + 1)}, tolerance = {tol(rng)})"
    a = numq(rng, nc, depth + 1)
    return f"difference({a}, {a if rng.random() < 0.2 else numq(rng, nc, depth + 1)})"


def countq(rng, nc):
    return "rows(t)" if rng.random() < 0.3 else f"count({sel(rng, nc)})"


def value_is(rng):
    return rng.choice([" is 0", " is 1", " is 2", " is 3", " is 30", " is 12", " is -4.5", " is 1/2", " is 0/3",
                       ' is "A"', ' is "s1"', ' is ""', " is 2 s", " is 2.0", " is 1/-2"])


def claim(rng, nc):
    x = rng.random()
    if x < 0.12:
        e = countq(rng, nc)
    elif x < 0.22:
        e = f"share({sel(rng, nc)})"
    elif x < 0.37:
        e = f"cell(t, {row(rng, nc)}, {col(rng, nc)})"
    elif x < 0.42:
        e = f"header(t, {rng.choice([0, 1, 2, 5])})"
    elif x < 0.62:
        e = numq(rng, nc)
    elif x < 0.70:
        a = countq(rng, nc)
        e = f"difference({a}, {a if rng.random() < 0.2 else countq(rng, nc)})"
    else:
        arg = rng.choice([numq(rng, nc), countq(rng, nc), f"share({sel(rng, nc)})"])
        c = rng.choice(["-5", "0", "1", "2", "3", "12", "29", "30", "1/2", "0.4", "300"])
        e = f"{rng.choice(['exceeds', 'below', 'atleast', 'atmost'])}({arg}, c = {c})"
    return "claim " + e + (value_is(rng) if rng.random() < 0.4 else "")


def program(rng, h, nc):
    lines = [f"file f = sha256:{h}", "let t = tsv(f)"]
    for _ in range(rng.randint(1, 4)):
        lines.append(claim(rng, nc))
    if rng.random() < 0.1:   # the same value widened twice (call 4)
        lines.append(f"claim widen(max(t, 1), tolerance = 1)\nclaim widen(max(t, 1), tolerance = 2)")
    return "\n".join(lines) + "\n"


def kernel_lines(text):
    out = {}
    for ln in text.split("\n"):
        m = re.match(r"line (\d+): (formed|refused)(?: \[(\w+),)?", ln)
        if m:
            if (m.group(3) in ("S008", "S011", "R013") and "v4 SPEC 4." in ln) or (m.group(3) == "S012" and "v4 SPEC 5.3" in ln):
                out[int(m.group(1))] = ("witness", m.group(3))   # W1/W2: reality4_ref predates them
            else:
                out[int(m.group(1))] = ("refused", m.group(3)) if m.group(2) == "refused" else ("formed", ln)
    return out


def test_differential(tmp_path):
    rng = random.Random(1025)
    lines = formed = progs = witnessed = 0
    carved = []   # every line counted apart, with why (review finding 27): pinned in differential-carve-outs.tsv
    for i in range(6000):
        data, nc = table(rng)
        p, h = helpers.tsv(tmp_path, f"t{i}.tsv", data)
        store = R.Store([p])
        for j in range(4):
            prog = program(rng, h, nc)
            ok, out = check(prog.encode("ascii"), store)
            k = kernel_lines("\n".join(out))
            if 0 < data.count(b"\r\n") < data.count(b"\n"):
                # Patsak 25 Oct 22:29: mixed line ends refuse T010 (the v3-era reference reads them)
                assert "[T010," in "\n".join(out), out
                witnessed += 1
                carved.append(f"mixed-line-ends\t{i}.{j}\t-\tT010\t-\t{prog.splitlines()[-1]!r}")
                progs += 1
                continue
            bom = data.startswith(b"\xef\xbb\xbf")
            # v4 SPEC 6.1 (25 Oct, 22:2x): a BOM makes only the first header name ambiguous; the
            # v3-era reference refuses the whole file, so it reads the bytes after the BOM, and a
            # line it forms that v4 refuses T011 (a use of that name) is counted apart below
            r = ref.run(prog.encode("ascii"), {h: data[3:] if bom else data})
            assert sorted(k) == sorted(ln for ln, _, _ in r), (data, prog, out, r)
            for ln, status, v in r:
                ks, kv = k[ln]
                if ks == "witness":   # v4 SPEC 4.3 (W1/W2) and 5.3 (S012 by value identity, exact use
                    # = tolerance 0) refuse lines the v3-era reference may form; it gains both with
                    # checker B (STATUS.md). The reverse (reference refuses, v4 forms) still fails.
                    witnessed += 1
                    carved.append(f"w1-w2-s012\t{i}.{j}\t{ln}\t{kv}\t{status} {v if status == 'refused' else 'formed'}\t{prog.split(chr(10))[ln - 1]!r}")
                    continue
                src = prog.split("\n")[ln - 1]
                if bom and (ks, kv) == ("refused", "T011"):
                    witnessed += 1
                    carved.append(f"bom-t011\t{i}.{j}\t{ln}\tT011\t{status}\t{src!r}")
                    continue
                assert ks == status, (src, ln, k[ln], v)
                if status == "refused" and v in ("S008", "S011") and kv != v:
                    # v4 dropped the v3 hand idleness rules the reference still has; on these
                    # bytes another rule (V002, V004, K004, ...) refuses first. Both refuse.
                    witnessed += 1
                    carved.append(f"both-refuse\t{i}.{j}\t{ln}\t{kv}\trefused {v}\t{src!r}")
                    continue
                if status == "refused":
                    assert kv == v, (data, prog, ln, kv, v)
                else:
                    assert kv.endswith(" " + v), (data, prog, ln, kv, v)
                    formed += 1
                lines += 1
            progs += 1
    print(progs, "programs,", lines, "lines agree,", formed, "formed,", witnessed, "refused by W1/W2 only in reality4")
    assert progs == 24000 and formed > 2500
    path = os.path.join(os.path.dirname(__file__), "differential-carve-outs.tsv")
    text = "".join(c + "\n" for c in carved)
    if os.environ.get("REALITY_REGEN_CARVE_OUTS"):
        open(path, "w", encoding="utf-8").write(text)
    assert witnessed == len(carved) and open(path, encoding="utf-8").read() == text, "the lines counted apart changed: regenerate and audit"

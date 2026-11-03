"""Exact-decision phase 3 check (plan section 7.6): probes of the reader facts H1 and H2 that the part-T
model assumes (SPEC-EXACT 7), against the real TSV and CSV readers. Report only, untrusted.

Tables are written as decide.Model writes them (header c1 .. cw zpad; each row 'p' in every cell it
does not set; CSV cells quoted when they hold a comma, quote, tab, semicolon, CR or LF). Cells are every
string of length 0-2 over an alphabet of the bytes and characters readers split on or refuse: TAB, LF,
CR, '"', ',', ';', space, NUL, U+FEFF (BOM), U+2028, U+0085, a, 1, '.', '-', 'e', and U+00E9.

  H1a  a row with one cell set: read back exactly iff the cell is, alone, in that column (the model's
       probe), for every column of widths 1-3;
  H1b  a row with cells set in two columns is read back iff each cell is (a type is realisable iff
       each class is, SPEC-EXACT 3.2);
  H1c  a table of two or three such rows is read back exactly iff each row is (rows are accepted one
       by one; part T has no cross-row constraint), the header-only table included;
  H1d  a header cell (header(), SPEC-EXACT 3.4) is read back with rows present iff it is alone;
  H2   the spellings the model uses for a class are read back: the first 200 'other' spellings of a
       column with literals, and 200 decimal spellings (with zeros added) of 20 values.
python3 tools/exact_h1.py   (exit 1 on any counterexample)"""
import hashlib
import itertools
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src")]
from reality4 import decide as D, readers as R  # noqa: E402

ALPHA = ["\t", "\n", "\r", '"', ",", ";", " ", "\x00", "﻿", " ", "\x85", "a", "1", ".", "-", "e", "é"]
CELLS = [""] + ALPHA + ["".join(p) for p in itertools.product(ALPHA, repeat=2)]


class M(D.Model):
    def __init__(self, kind, width):
        self.kind, self.width, self.steps = {"s": kind}, {"s": width}, 0


def back(m, rows, hdr=None):
    """The rows are read back exactly (and the header cells)."""
    return m.readable("s", [list(r) for r in rows], hdr)


def row(w, cells):
    r = ["p"] * (w + 1)
    for k, c in cells.items():
        r[k - 1] = c
    return r


def main():
    bad = []
    n = 0
    for kind in ("tsv", "csv"):
        for w in (1, 2, 3):
            m = M(kind, w)
            acc = {(k, c): back(m, [row(w, {k: c})]) for k in range(1, w + 1) for c in CELLS}
            ok = [c for c in CELLS if acc[(1, c)]]
            n += len(acc)
            for k in range(2, w + 1):   # H1a: the same cells are accepted in every column
                bad += [(kind, w, "H1a", k, c) for c in CELLS if acc[(k, c)] != acc[(1, c)]]
            if w >= 2:   # H1b
                for c1, c2 in itertools.product(CELLS[:60], repeat=2):
                    n += 1
                    if back(m, [row(w, {1: c1, 2: c2})]) != (acc[(1, c1)] and acc[(2, c2)]):
                        bad.append((kind, w, "H1b", c1, c2))
            n += 1
            if not back(m, []):
                bad.append((kind, w, "H1c", "header only"))
            for c1, c2 in itertools.product(CELLS, repeat=2):   # H1c, two rows
                n += 1
                if back(m, [row(w, {1: c1}), row(w, {1: c2})]) != (acc[(1, c1)] and acc[(1, c2)]):
                    bad.append((kind, w, "H1c", c1, c2))
            for c1, c2, c3 in itertools.product(CELLS[:40], repeat=3):   # H1c, three rows
                n += 1
                if back(m, [row(w, {1: c1}), row(w, {1: c2}), row(w, {1: c3})]) != (acc[(1, c1)] and acc[(1, c2)] and acc[(1, c3)]):
                    bad.append((kind, w, "H1c3", c1, c2, c3))
            for h in CELLS:   # H1d
                alone = back(m, [], {1: h})
                for c in ok[:20]:
                    n += 1
                    if back(m, [row(w, {1: c})], {1: h}) != alone:
                        bad.append((kind, w, "H1d", h, c))
            m.lits = {("s", 1): [b"a", b"rn", b"l0"]}   # H2
            m.spell = {}
            for v in range(200):
                n += 1
                t = m.text("s", 1, ("oth", None, None), v)
                if not back(m, [row(w, {1: t})]) or R.decimal(t) is not None:
                    bad.append((kind, w, "H2 other", t))
            for q in [Fraction(x, y) for x in (-7, 0, 1, 10, 123456789) for y in (1, 2, 4, 1000)]:
                for v in range(10):
                    n += 1
                    t = m.text("s", 1, ("iv", None, q), v)
                    if not back(m, [row(w, {1: t})]) or R.decimal(t) != q:
                        bad.append((kind, w, "H2 decimal", t))
    for b in bad[:50]:
        print("COUNTEREXAMPLE", repr(b))
    print(f"{n} probes of H1/H2 (TSV and CSV, widths 1-3, {len(CELLS)} cells); {len(bad)} counterexamples")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

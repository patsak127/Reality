"""Exact-decision phase 5 check (plan section 7.6): the part-H atom domains of SPEC-EXACT 3.6 probed against
the real readers (reader fact H3 for files). Report only, untrusted.

  NIfTI  headers as decide.py writes them (NIfTI-1 when every dim fits int16, else NIfTI-2), dim[0] from -1
         to 8 and each dim from {-1, 0, 1, 2, 64, 32767, 32768, 2^31, 2^63 - 1}: the reader accepts exactly when
         1 <= dim[0] <= 7 and every dim up to dim[0] is >= 1, and then reads back every dim;
  JSON   documents built from every kind of node (object, array, number, string, null) two levels deep and the
         numbers decide.py spells (dec_text of 200 rationals): each parses, and each number reads back exact;
  raw    files of 0-300 bytes: size() is the length and every bytes(f, o, n) inside it the slice.
python3 tools/exact_h3.py   (exit 1 on any counterexample)"""
import itertools
import json
import os
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src")]
from reality4 import readers as R, witness as W  # noqa: E402


def header(d0, dims):
    if all(-32768 <= d <= 32767 for d in [d0] + dims):
        b = bytearray(W._nii([1], 1, data=False))
        struct.pack_into("<8h", b, 40, d0, *dims, *[1] * (7 - len(dims)))
        return bytes(b)
    b = bytearray(544)
    struct.pack_into("<i", b, 0, 540)
    b[4:12] = b"n+2\x00\r\n\x1a\n"
    struct.pack_into("<2h", b, 12, 2, 8)
    struct.pack_into("<8q", b, 16, d0, *dims, *[1] * (7 - len(dims)))
    struct.pack_into("<8d", b, 104, 1, 1, 1, 1, 1, 0, 0, 0)
    struct.pack_into("<q", b, 168, 544)
    struct.pack_into("<i", b, 500, 10)
    return bytes(b)


def main():
    bad, n = [], 0
    vals = [-1, 0, 1, 2, 64, 32767, 32768, 2 ** 31, 2 ** 63 - 1]
    for d0 in range(-1, 9):
        for k in range(1, 4):
            for v in vals:
                dims = [1] * 7
                dims[k - 1] = v
                n += 1
                want = 1 <= d0 <= 7 and all(dims[i] >= 1 for i in range(min(d0, 7)))
                try:
                    hd = R.nifti_header(header(d0, dims), "probe")
                    got = True
                    if hd.dim[1:8] != dims or hd.dim[0] != d0:
                        bad.append(("nifti read back", d0, dims, hd.dim))
                except R.Refusal:
                    got = False
                if got != want:
                    bad.append(("nifti", d0, k, v, got))
    kinds = ['1', '-2.5', '"s"', 'null', '{}', '[]', '{"a": 1}', '[1, "s"]']
    for a, b in itertools.product(kinds, repeat=2):
        for doc in ('{"x": %s, "y": [%s]}' % (a, b), '[%s, {"x": %s}]' % (a, b)):
            n += 1
            try:
                R.parse_json(doc.encode(), "probe")
            except R.Refusal as e:
                bad.append(("json", doc, e.code))
    for q in [Fraction(p, 10 ** e) for p in range(-50, 50, 7) for e in range(0, 6)] + [Fraction(10) ** 30, Fraction(-1, 10 ** 40)]:
        n += 1
        t = W.dec_text(q)
        if R.parse_json(('{"v": %s}' % t).encode(), "probe")["v"] != q:
            bad.append(("json number", t))
    for size in range(0, 301, 7):
        data = bytes((7 * i + 1) % 256 for i in range(size))
        st = W.MemStore({"h": data})
        n += 1
        if st.size("h") != size:
            bad.append(("size", size))
        for o, k in ((0, 1), (size // 2, 3), (max(size - 4, 0), 4)):
            if o + k <= size:
                n += 1
                if st.slice("h", o, k) != data[o:o + k]:
                    bad.append(("bytes", size, o, k))
    for b in bad[:30]:
        print("COUNTEREXAMPLE", b)
    print(f"{n} probes of the part-H domains (NIfTI headers, JSON documents and numbers, raw files); {len(bad)} counterexamples")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

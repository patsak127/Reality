"""Finding 21: RULES-1.0.1.md says it classifies every 1.0.1 statement once. Small datasets
showing sentences it leaves out or classifies differently from the code:
21a  no README                      (8.1 "a free form text file (README) ... should be provided": not listed)
21b  README not UTF-8               (8.1 "should be either in ASCII or UTF-8": checked, B18)
21c  task x with TaskName "x" in one sidecar and "x!" in another   (RULES: "checked"; no 1.0.1 sentence)
21d  EchoTime -0.03, InversionTime -1, FlipAngle -400               (RULES infers > 0 only for TR)
21e  TR 0                            (B08)
21f  notes.json, not JSON, at the root          (read as metadata: B03)
21g  sub-01/notes.json, not JSON                 (extra: forms)
21h  sub-01/func/notes.json, not JSON            (B17)
21i  dwi.bval at the root (8.8: bval/bvec "can be saved on any level"; RULES: inherited .bvec "B14 at the root")"""
import _lib as L
P = 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x"))\n'
cases = {
    "21a": ({}, ("README",)),
    "21b": ({"README": b"caf\xe9\n"}, ()),
    "21c": ({"sub-02/func/sub-02_task-x_bold.json": '{"TaskName": "x!"}'}, ()),
    "21d": ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 1, "EchoTime": -0.03, "InversionTime": -1, "FlipAngle": -400}'}, ()),
    "21e": ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 0}'}, ()),
    "21f": ({"notes.json": "my notes, not JSON"}, ()),
    "21g": ({"sub-01/notes.json": "my notes, not JSON"}, ()),
    "21h": ({"sub-01/func/notes.json": "my notes, not JSON"}, ()),
    "21i": ({"dwi.bval": "0 1000 1000\n"}, ()),
}
for nn, (extra, drop) in cases.items():
    f = L.base_files(subjects=("01", "02") if nn == "21c" else ("01",), extra=extra, drop=drop)
    m = L.build(nn, f)
    L.program(nn, "rules-coverage", P % m)

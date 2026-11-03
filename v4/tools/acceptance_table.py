"""Print the F/N results table (spec §5) as markdown: each case, what it expects, and what the
checker printed. Usage (from v4/): ~/reality-harness/venv/bin/python tools/acceptance_table.py"""
import os
import pathlib
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src"), os.path.join(HERE, "..", "tests")]
import acceptance as A  # noqa: E402
import bidsfix  # noqa: E402
import helpers  # noqa: E402
from test_acceptance import setup  # noqa: E402


def short(line):
    m = re.match(r"line (\d+): refused \[(\w+), [^\]]*\]: (.*)", line)
    if m:
        msg = m.group(3)
        return f"{m.group(2)}: {msg[:150] + '...' if len(msg) > 150 else msg}"
    m = re.match(r"line (\d+): formed: (.*)", line)
    return "formed: " + m.group(2) if m else None


def main():
    import io
    import contextlib
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        os.makedirs(t / "bm")
        box = (str(t / "bm"), bidsfix.box_copy(), helpers.manifest(bidsfix.box_copy(), str(t / "bm")))
        root = bidsfix.complete_copy(str(t / "cc"))
        os.makedirs(t / "cm")
        complete = (str(t / "cm"), root, helpers.manifest(root, str(t / "cm")))
        os.makedirs(t / "dec")
        _, dh = helpers.tsv(t / "dec", "decisions.tsv", A.DECISIONS)
        dec = (str(t / "dec"), dh)
        print("| id | expected | result | what the checker printed (per claim) | note |")
        print("|---|---|---|---|---|")
        for i, (cid, fixture, prog, expect, note) in enumerate(A.CASES):
            if expect == "all-refused":
                print(f"| {cid} | all refused | all refused | see tests/old/narps-*.rl | {note} |")
                continue
            tp = t / f"case{i}"
            os.makedirs(tp)
            subs, files, roots = setup(fixture, box, complete, dec, tp)
            with contextlib.redirect_stdout(io.StringIO()):
                ok, text = helpers.run(prog.format(**subs), files, roots)
            got = [s for s in (short(x) for x in text.splitlines()) if s]
            codes = [g.split(":")[0] for g in got if not g.startswith("formed")]
            result = "formed" if ok else "refused " + " ".join(codes)
            exp = "formed" if expect == "formed" else "refused " + " ".join(expect)
            cell = "<br>".join(g.replace("|", "\\|") for g in got)
            print(f"| {cid} | {exp} | {result}{'' if exp == result else ' **MISMATCH**'} | {cell} | {note} |")
        for cid, why in A.OUT_OF_SCOPE:
            kind = "covered elsewhere" if cid.startswith("N") else "out of scope"
            print(f"| {cid} | {kind} | - | - | {why} |")


if __name__ == "__main__":
    main()

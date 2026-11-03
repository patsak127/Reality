"""The 22 findings of Claude Opus 5.5's review of v1 (review-opus55-v1/CLASSIFICATION.md),
each shown fixed in v2 or shown to have no form in v2. N12 of the spec's acceptance list.
Findings that concern v1 parts v2 does not have (quantities, frames, statistical tests) are
marked 'no form'; their v1 texts are in tests/old/opus-v1-*.rl and are all refused
(test_old_programs.py)."""
import os
import re
import subprocess
import sys

import pytest

import acceptance as A
import bidsfix
import helpers
from reality4 import kernel
from reality4 import readers as R

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")


def codes(text):
    return re.findall(r"^line \d+: refused \[(\w+),", text, re.M)


@pytest.fixture()
def people(tmp_path):
    return helpers.tsv(tmp_path, "people.tsv", "id\tgroup\tage\ns1\tA\t30\ns2\tB\t41\ns3\tB\t29\n")


# 1. One test, two decisions depending on PYTHONHASHSEED.
def test_01_hash_seed_does_not_change_output(box):
    prog = (A.BOX_HEAD + "file p = sha256:{P}\nlet t = tsv(p)\nclaim count(where(t, eq(2, \"equalRange\"), ne(3, \"F\")))\n"
            "claim share(where(t, eq(\"group\", \"equalRange\")))\nclaim max(t, 4)\nclaim count(participants(b))\n"
            "claim count(where(t, eq(2, \"equaIRange\")))\n").format(BOX=box[2], P=A.P)
    outs = set()
    for seed in ("0", "1", "24", "42", "55", "80", "random"):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=SRC)
        p = subprocess.run([sys.executable, "-c", "import sys; from reality4.__main__ import main; sys.exit(main(sys.argv[1:]))",
                            "check", "-", "--files", box[0], box[1], "--root", box[1]],
                           input=prog.encode(), capture_output=True, env=env)
        outs.add(p.stdout)
    assert len(outs) == 1
    print(outs.pop().decode())


# 2. Renaming flips the verdict: see test_rename.py (fuzzer); here the v1 case, rewritten.
def test_02_renaming(people):
    path, h = people
    a = helpers.run(f"file t = sha256:{h}\nlet s1 = where(tsv(t), eq(1, \"s1\"))\nclaim count(s1)\n", [path])[1]
    b = helpers.run(f"file t = sha256:{h}\nlet q1 = where(tsv(t), eq(1, \"s1\"))\nclaim count(q1)\n", [path])[1]
    assert a == b


# 3. Support under-reported: a claim names every file its value is computed from (check 2).
def test_03_check2_refuses_an_unnamed_read(people, tmp_path, monkeypatch):
    path, h = people
    other, h2 = helpers.tsv(tmp_path, "other.tsv", "x\n1\n")
    orig = kernel.Checker.c_rows

    def leaky(self, c):
        self.store.text(h2)          # a (buggy) computation reads a file its sort does not name
        return orig(self, c)
    monkeypatch.setattr(kernel.Checker, "c_rows", leaky)
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim rows(tsv(t))\n", [path, other])
    assert codes(text) == ["C001"] and "does not name" in text


def test_03_check2_refuses_an_idle_name(people, monkeypatch):
    path, h = people
    monkeypatch.setattr(kernel.Checker, "c_size", lambda self, c: kernel.M("count", kernel.S("ByteCount[", kernel.File(h), "]"), 3, None, {h}))
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim size(t)\n", [path])
    assert codes(text) == ["C001"] and "was not computed from it" in text


def test_03_every_formed_claim_names_exactly_what_it_read(box, complete):
    """Over all must-form acceptance programs: the printed files are the files read."""
    for cid, fixture, prog, expect, _ in A.CASES:
        if expect != "formed" or fixture not in ("box", "complete"):
            continue
        files, roots, subs = ([box[0], box[1]], [box[1]], {"BOX": box[2]}) if fixture == "box" else ([complete[0]], [complete[1]], {"CMP": complete[2]})
        st = R.Store(files, roots)
        ck = kernel.Checker(st)
        from reality4.syntax import parse_line
        for ln, line in enumerate(prog.format(P=A.P, EV=A.EV, **subs).split("\n"), 1):
            s = parse_line(line, ln)
            if s is None:
                continue
            res = ck.statement(s)
            if res:
                m, named, _ = res
                assert named and set(named) == set(kernel.files(m.sort)), cid


# 4. ratio(A, B) is an unchecked kind cast: v2 has no ratio; a share is of a selection of its own set.
def test_04_no_kind_cast(people, complete):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim share(rows(tsv(t)))\nclaim ratio(rows(tsv(t)), rows(tsv(t)))\n"
                           "claim difference(number(cell(tsv(t), 1, 3)), sum(tsv(t), 3))\n", [path])
    assert codes(text) == ["S007", "S002"]
    assert "formed: Difference[" in text           # same kind (decimals without unit): forms
    ok, text = helpers.run(A.CMP_HEAD.format(CMP=complete[2]) + f"file t = sha256:{h}\nclaim difference(tr(r), number(cell(tsv(t), 1, 3)))\n",
                           [complete[0], path], [complete[1]])
    assert codes(text) == ["U001"]


# 5. Aliases give one test two decisions: aliases mean the same, and values are computed, never stated.
def test_05_aliases(people):
    path, h = people
    ok, text = helpers.run(f"file a = sha256:{h}\nfile b = sha256:{h}\nclaim rows(tsv(a)) is 3\nclaim rows(tsv(b)) is 2\nclaim rows(tsv(b))\n", [path])
    assert codes(text) == ["V001"]
    lines = [ln.split(": ", 1)[1] for ln in text.split("\n") if "formed" in ln]
    assert lines[0] == lines[1]                     # one meaning, printed once per claim, identically


# 6. Two individuals from one row; 'unknown' from a row: no author-declared individuals; BIDS rows are
#    participants only under participants.tsv with one row per participant (B11, test_bids).
def test_06_no_author_declared_members(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nindividual s1 : P from t row 1\nlet s1 = row(tsv(t), 1)\nclaim count(s1)\n", [path])
    assert codes(text) == ["P008", "S002", "N003"]   # the let is refused on its own line, its use after it


# 7. An observation reads another person's row or the wrong column.
def test_07_cells_come_from_the_named_row_and_column(tmp_path):
    root = bidsfix.mini(str(tmp_path / "ds"), groups={"01": "g1", "02": "g2"})
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nlet b = bids(d)\nclaim extra(participant(b, \"02\"), \"group\") is \"g2\"\n"
                           "claim extra(participant(b, \"01\"), \"group\") is \"g2\"\nclaim extra(participant(b, \"01\"), \"age\")\n", [str(md)], [root])
    assert codes(text) == ["V001", "V002"]


# 8. Lookalike keys.
def test_08_lookalikes(tmp_path):
    p, h = helpers.tsv(tmp_path, "k.tsv", "id\tv\nsub001\t1\nsubOO1\t2\nx\t3\n")
    q, h2 = helpers.tsv(tmp_path, "nb.tsv", "id\tv\nsub\u2011001\t1\n")
    ok, text = helpers.run(f"file t = sha256:{h}\nfile u = sha256:{h2}\nclaim cell(tsv(t), key(1, \"sub001\"), 2)\n"
                           "claim count(where(tsv(t), eq(1, \"SUB001\")))\nclaim cell(tsv(t), key(1, \"x\"), 2)\n"
                           "claim cell(tsv(u), key(1, \"sub\\xe2\\x80\\x91001\"), 2)\nclaim cell(u, 1, 1)\nclaim cell(tsv(u), 1, 1)\n", [p, q])
    # line 5 (key "x") refuses too since v3: the key column holds sub001 and subOO1, two strings
    # with one skeleton, so the claim's scope has a lookalike pair (Patsak's call 2: one rule).
    assert codes(text) == ["K002", "K002", "K002", "K001", "S007"]
    assert 'formed: Cell[TSV[#1], row 1, col 1] = "sub\\xe2\\x80\\x91001"' in text   # non-ASCII is printed escaped, never hidden


# 9. The claim's test is stipulated: v2 has no test catalogue yet; values are never written, cutoffs are printed parameters.
def test_09_no_stipulated_values(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim exceeds(41, c = 40)\nclaim exceeds(max(tsv(t), 3), c = 41)\n"
                           "claim exceeds(max(tsv(t), 3), c = 40)\nclaim significant(tsv(t), alpha = 0.99, permutations = 1)\n", [path])
    assert codes(text) == ["S001", "V001", "S002"]
    assert "Exceeds[Max[TSV[#1], col 3], c = 40] holds" in text


# 10. Exclusion without 'not': a complement is only over the rows of the table, a universe read from bytes.
def test_10_complement_is_over_the_table(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim count(where(tsv(t), eq(2, \"B\"))) is 2\nclaim count(where(tsv(t), ne(2, \"B\"))) is 1\n"
                           "claim rows(tsv(t)) is 3\n", [path])
    assert ok


# 11/12. Resource use depends on the machine: counted steps and byte bounds, the same everywhere.
def test_11_counted_steps(people, monkeypatch):
    path, h = people
    monkeypatch.setattr(R, "MAX_STEPS", 3)
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim count(where(tsv(t), eq(2, \"B\"), ne(1, \"s9\")))\n", [path])
    assert codes(text) == ["R002"] and "counted steps" in text


def test_12_bytes_read_are_bounded(people, monkeypatch):
    path, h = people
    monkeypatch.setattr(R, "MAX_TEXT_FILE", 10)
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim rows(tsv(t))\nclaim size(t)\n", [path])
    assert codes(text) == ["R003"]


# 13. S009 internal error was reachable. v2: v1's crashing inputs and edge values are refused with
# their rule; an internal error, if one remains, refuses (X001) and never forms. test_fuzz.py adds mutants.
def test_13_no_crash_and_bugs_refuse(people, monkeypatch):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nlet m = max(tsv(t), 3)\nclaim exceeds(m, c = 3, method = 3)\n"
                           "claim exceeds(m, c = 3, df_method = 3)\nclaim bytes(t, 99999999999999999999999, 1)\n"
                           "claim cell(tsv(t), 99999999999999999999999999, 1)\nclaim exceeds(m, c = 1/0)\n", [path])
    assert codes(text) == ["S004", "S004", "V002", "V002", "P007"]   # 1/0: a zero denominator (call 8)

    def boom(*a, **k):
        raise ZeroDivisionError("planted")
    monkeypatch.setattr(kernel.Checker, "c_rows", boom)
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim rows(tsv(t))\n", [path])
    assert not ok and codes(text) == ["X001"] and ": formed:" not in text


# 18. A refused re-declaration overwrote the first binding.
def test_18_refused_redeclaration_leaves_the_first(people, tmp_path):
    path, h = people
    q, h2 = helpers.tsv(tmp_path, "two.tsv", "a\n1\n")
    ok, text = helpers.run(f"file t = sha256:{h}\nfile t = sha256:{h2}\nclaim rows(tsv(t)) is 3\nlet z = nothing\nclaim rows(tsv(z))\nlet z = tsv(t)\n", [path, q])
    assert codes(text) == ["N002", "N001", "N003", "N002"]
    assert "RowCount[TSV[#1]] = 3" in text


# 14. 'one' one level up: no unit algebra; a count has no unit.
def test_14_counts_have_no_unit(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim rows(tsv(t)) is 3 s\nclaim rows(tsv(t)) is 3.0\nclaim share(where(tsv(t), eq(2, \"B\"))) is 2/3\n", [path])
    assert codes(text) == ["U002", "U002"]


# 15. A respect that ignores its arguments: v2 has no user-defined bodies; a part that does not bear is refused.
def test_15_idle_parts(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim count(where(tsv(t), eq(2, \"B\"), eq(2, \"B\")))\nclaim same(t, t)\n"
                           "claim rows(tsv(t), 3)\n", [path])
    assert codes(text) == ["S008", "S002", "S003"]


# 16. ref doi "TBD": no form (also N11).
def test_16_unread_reference(people):
    path, h = people
    ok, text = helpers.run(f"artifact paper = ref doi \"TBD\"\nfile t = doi:TBD\nclaim rows(tsv(paper))\n", [path])
    assert codes(text) == ["P008", "P003", "N001"]


# 17. df1, permutations, junk arguments: unknown slots refused, empty slots refused, no df slot exists.
def test_17_slots(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nlet m = max(tsv(t), 3)\nclaim exceeds(m, c = 3, df = 7)\nclaim exceeds(m)\n"
                           "claim exceeds(m, c = 3, c = 4)\nclaim widen(m, tolerance = -1)\nclaim exceeds(m, c = \"3\")\nclaim exceeds(m, c = t)\n"
                           "claim exceeds(m, anything = 7, c = 3)\n", [path])
    assert codes(text) == ["S004", "S005", "S004", "S004", "P006", "S004", "S004"]


# 19. Duplicate headers and an empty key.
def test_19_duplicate_headers_and_empty_key(tmp_path):
    p, h = helpers.tsv(tmp_path, "dup.tsv", "id\tgroup\tid\ns1\tA\ts9\n\tB\ts1\n")
    ok, text = helpers.run(f"file d = sha256:{h}\nlet t = tsv(d)\nclaim cell(t, 1, \"id\")\nclaim cell(t, key(3, \"\"), 2)\n"
                           "claim cell(t, 1, 3)\nclaim count(where(t, eq(\"ID\", \"s1\")))\nclaim cell(t, key(1, \"s1\"), \"group\")\n", [p])
    assert codes(text) == ["K002", "K001", "V002"]
    assert 'Cell[TSV[#1], row 1, col 3] = "s9"' in text
    p2, h2 = helpers.tsv(tmp_path, "case.tsv", "id\tID\nx\ty\n")
    ok, text = helpers.run(f"file d = sha256:{h2}\nclaim cell(tsv(d), 1, \"ID\")\n", [p2])
    assert codes(text) == ["K002"]


# 20. Overcorrections: a share of a group forms (F2, F12); angles and kind expressions are quantities, not in v2.
def test_20_share_of_a_group_forms(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nclaim share(where(tsv(t), eq(2, \"B\"))) is 2/3\n", [path])
    assert ok and "= 2/3 (Exact)" in text


# 21. A result 'significant' from a cell saying 'No': no decision form; cells are bytes (N3).
def test_21_no_decision_from_a_cell(tmp_path):
    p, h = helpers.tsv(tmp_path, "r.tsv", "result\tdecision\n1K0E/H7\tNo\n")
    ok, text = helpers.run(f"file r = sha256:{h}\nclaim significant(cell(tsv(r), 1, 2))\nclaim cell(tsv(r), 1, 2) is \"Yes\"\nclaim cell(tsv(r), 1, 2)\n", [p])
    assert codes(text) == ["S002", "V001"]


# 22. An origin from any row: v2 has no frames or anchors (an anchor time needs a fixed format or a
#     standard field such as BIDS acq_time in scans.tsv, which this reader does not implement: B14).
def test_22_no_anchor_from_a_row(people):
    path, h = people
    ok, text = helpers.run(f"file t = sha256:{h}\nframe earth origin rightnow from t row 1\nclaim origin(tsv(t), 1)\n", [path])
    assert codes(text) == ["P008", "S002"]


def test_fixture_pin(box):
    """tests/data/ds001734-box is byte for byte the box copy the spec's §4 describes."""
    assert box[2] == bidsfix.BOX_MANIFEST_SHA256
    assert helpers.sha(os.path.join(box[1], "participants.tsv")) == bidsfix.PARTICIPANTS_SHA256

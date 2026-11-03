"""v4 SPEC 9.2, 9.3: literal length counts in the sort size; per-statement (R014) and program
(R011) output bounds. Regression for review finding 04 (one 33 KB program printing 269 MB)."""
import os

import pytest

from helpers import run, tsv
from reality4 import kernel

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repros_v3")


def test_finding_04_refuses_r006_and_prints_little():
    prog = open(os.path.join(HERE, "04-memory.rl"), "rb").read()
    ok, text = run(prog, [os.path.join(HERE, "04-one.tsv")])
    assert not ok and "[R006" in text and len(text) < 100_000, text[:2000]


def test_literal_length_counts_in_sort_size(tmp_path):
    from reality4.sorts import S, Lit, File
    assert S(Lit(b"")).size == 2 and S(Lit(b"x" * 63)).size == 2 and S(Lit(b"x" * 64)).size == 3
    assert S(Lit(b"x" * 4096)).size == 1 + 65 and S(File("0" * 64)).size == 2
    p, h = tsv(tmp_path, "t.tsv", "a\nb\n")
    ok, text = run(f'file f = sha256:{h}\nclaim difference(count(where(tsv(f), ne(1, "{"x" * 4090}"))), count(where(tsv(f), ne(1, "{"y" * 4090}"))))\n', [p])
    assert "line 2: formed" in text, text


def test_statement_output_bound_r014(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, "MAX_LINE_OUTPUT", 200)
    p, h = tsv(tmp_path, "t.tsv", "a\nb\n")
    ok, text = run(f'file f = sha256:{h}\nclaim rows(tsv(f))\nclaim count(where(tsv(f), ne(1, "{"y" * 300}")))\n', [p])
    assert not ok and "line 2: formed" in text and "line 3: refused [R014" in text, text


def test_program_output_bound_r011(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, "MAX_PROGRAM_OUTPUT", 400)
    p, h = tsv(tmp_path, "t.tsv", "a\nb\n")
    claims = "".join("claim rows(tsv(f))\n" for _ in range(10))
    ok, text = run(f"file f = sha256:{h}\n" + claims, [p])
    assert not ok and "refused [R011" in text and "line 2: formed" in text, text
    assert len(text.encode()) < 400 + 2000


def test_accounted_memory_bound_r012(tmp_path, monkeypatch):
    from reality4 import readers
    monkeypatch.setattr(readers, "MAX_ACCOUNTED", 5000)
    p, h = tsv(tmp_path, "t.tsv", "a\tb\n" + "".join(f"{i}\tx\n" for i in range(200)))
    ok, text = run(f"file f = sha256:{h}\nclaim rows(tsv(f))\n", [p])
    assert not ok and "refused [R012" in text, text


def test_accounted_memory_is_per_program(tmp_path):
    from reality4 import readers
    from reality4.kernel import check
    p, h = tsv(tmp_path, "t.tsv", "a\n1\n")
    st = readers.Store([p], [])
    prog = f"file f = sha256:{h}\nclaim rows(tsv(f))\n".encode()
    a = check(prog, st)
    b = check(prog, st)
    assert a == b and a[0] is True

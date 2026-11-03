"""DESIGN 1.3 item 6, built 26 Oct 2026 (review finding 26): the brute-force soundness measurement.

For every program of a generated family over one TSV slot (column 1 a label from x, y, z; column 2
a decimal from 0, 1, 2, 3), every readable table of at most 3 rows over those cells is evaluated (as a
multiset of rows: no program here reads a row by position, so row order cannot change an answer).
Ground truth within that space: the statement's distinct answers (W1; a refusal is not an answer),
and for each W2 part (a value refusal V... an outcome, any other refusal no answer, SPEC 4.4 10), whether the statement with and
without it ever answer differently on one table.

Required (the soundness check, must be 0): no claim that forms is constant within the space, and
no part of a claim that forms is idle within it. Reported and pinned: the claims Reality refuses
S008/S011 that are not constant, every part bearing, within the space (the overcorrection count).
A pass is evidence for this family and space, not a proof for every program (DESIGN 1.3)."""
import itertools
import re

import helpers
from reality4 import witness as W
from reality4.kernel import Checker
from reality4.syntax import parse_line

ROWS = [(a, b) for a in "xyz" for b in ("0", "1", "2", "3")]
SPACE = [("c1\tc2\n" + "".join(f"{a}\t{b}\n" for a, b in rs)).encode() for n in range(4) for rs in itertools.combinations_with_replacement(ROWS, n)]
REAL = b"c1\tc2\nx\t1\ny\t3\nz\t0\n"
CONDS = ['eq(1, "x")', 'ne(1, "x")', 'eq(1, "y")', "gt(2, c = 1)", "le(2, c = 1)", "ge(2, c = 3)"]


def family():
    sels = [f"where(t, {a})" for a in CONDS] + [f"where(t, {a}, {b})" for a in CONDS for b in CONDS]
    out = [f"count({s})" for s in sels] + [f"atleast(count({s}), c = 1)" for s in sels[:12]]
    out += [f"difference(count(where(t, {a}, {b})), count(where(t, {b}, {a})))" for a, b in zip(CONDS, CONDS[1:])]
    out += [f"share(where(t, {a}, {b}), where(t, {a}))" for a in CONDS[:3] for b in CONDS[3:]]
    out += [f"share(where(t, {a}), where(t, {a}))" for a in CONDS[:2]]
    out += [f"{fn}(where(t, {a}), 2)" for fn in ("sum", "max", "min") for a in CONDS[:3]]
    out += ["difference(rows(t), count(t))", 'difference(count(where(t, eq(1, "x"))), count(where(t, eq(1, "x"))))',
            "atleast(difference(max(t, 2), min(t, 2)), c = 0)", "exceeds(sum(t, 2), c = 2)", "atleast(count(t), c = 2)",
            'atmost(widen(sum(where(t, eq(1, "x")), 2), tolerance = 1/2), c = 2)', 'below(widen(max(where(t, eq(1, "x")), 2), tolerance = 1/2), c = 2)']
    return [re.sub(r"\bt\b", "tsv(f)", s) for s in out]


def outcome(g, e):
    if g is None:
        return None
    if id(e) in g:
        return g[id(e)]
    code = g.get("refused") or ""
    return ("V", code) if code[:1] == "V" else None


def truth(stmt):
    e = parse_line(f"claim {stmt}", 1).expr
    variants = [(desc, W._subst(e, node, mod)) for node, mod, desc in W.parts(e)]
    answers, bears = set(), {d: False for d, _ in variants}
    judged = {d: False for d, _ in variants}
    for t in SPACE:
        a = outcome(W.evaluate(Checker, e, ["f"], {"f": t}, [0]), e)
        if a is None:
            continue
        answers.add(a) if a[0] != "V" else None   # W1 counts answers; a value refusal is not one
        for d, v in variants:
            b = outcome(W.evaluate(Checker, v, ["f"], {"f": t}, [0]), v)
            if b is not None:
                judged[d] = True
                bears[d] |= a != b
    return len(answers) >= 2, {d: bears[d] for d in bears if judged[d]}


def test_bruteforce_soundness_and_overcorrection(tmp_path):
    p, h = helpers.tsv(tmp_path, "f.tsv", REAL)
    unsound, over = [], []
    for stmt in family():
        ok, text = helpers.run(f"file f = sha256:{h}\nclaim {stmt}\n", [p])
        formed = "formed" in text.split("\n")[0]
        varies, parts = truth(stmt)
        if formed and (not varies or not all(parts.values())):
            unsound.append((stmt, varies, parts))
        if not formed and ("[S008" in text or "[S011" in text) and varies and all(parts.values()):
            over.append(stmt)
    assert not unsound, unsound
    assert len(family()) == 86 and len(over) == OVERCORRECTION, over


OVERCORRECTION = 0   # measured 26 Oct 2026: 86 programs, 0 unsound, 0 overcorrection (LOG)


def test_bruteforce_ground_truth_sees_idle_values():
    """The measurement can fail: values idle by construction are constant within the space."""
    for stmt in ["difference(rows(tsv(f)), count(tsv(f)))", 'difference(count(where(tsv(f), eq(1, "x"), gt(2, c = 1))), count(where(tsv(f), gt(2, c = 1), eq(1, "x"))))',
                 "atleast(difference(max(tsv(f), 2), min(tsv(f), 2)), c = 0)", 'share(where(tsv(f), eq(1, "x")), where(tsv(f), eq(1, "x")))']:
        assert truth(stmt)[0] is False, stmt
    assert truth('count(where(tsv(f), eq(1, "x"), eq(1, "x")))')[1] == {'the condition eq(...)': False}

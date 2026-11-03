"""Ground truth for brute-force re-checks of the exact path's refusals (28 Oct 2026; untrusted, report only).

Every brute-force runner that re-checks a W1 or W2 refusal must take a statement's answers from here, never from the
kernel: the kernel refuses a W1 statement S008 on every answering table, so re-running the claim through it can
never show two answers (the ad hoc runners' re-checks before 28 Oct 15:10 were vacuous that way). Answers come from
witness.evaluate: the real readers and evaluator, with no W1/W2 step. tools/exact_bf*.py and tests/test_v4_bruteforce.py
use the same evaluator.

    answer(stmt, files)                 the top answer: a value, ("bool", True/False), ("V", code), or None (none)
    check_line(program, store)          a kernel-shaped result line from ground truth (for runners written for K._check)
    recheck_w1(stmt, tables, ...)       Recheck: "contradicted" (two answers), "ok", or "unjudged" (no answering table)
    recheck_w2(stmt, part, tables, ...) the same for a part (its description as witness.parts gives it)
    selftest()                          a deliberately wrong W1 and W2 refusal must come back "contradicted"

A re-check is evidence only when it is judged: a runner must count "unjudged" apart and never as "ok"."""
import os
import re
import sys
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
if not any(os.path.isfile(os.path.join(p, "reality4", "witness.py")) for p in sys.path if p):
    sys.path.insert(0, os.path.join(HERE, "..", "src"))
from reality4 import witness as W  # noqa: E402
from reality4.kernel import Checker  # noqa: E402
from reality4.syntax import parse_line  # noqa: E402

STATS = {"evaluations": 0, "answered": 0}
Recheck = namedtuple("Recheck", "status answers judged")   # answers: distinct answers seen; judged: answering tables


def expr_of(stmt, lets=None):
    """The statement's expression, each `let` name replaced by its expression text (lets: {name: text})."""
    for n, t in (lets or {"t": "tsv(f)"}).items():
        stmt = re.sub(r"\b%s\b(?=\s*[,)])" % re.escape(n), t, stmt)
    return parse_line("claim " + stmt, 1).expr


def _blob(b):
    return b.encode() if isinstance(b, str) else b


def answers_of(e, files):
    """{id(node): answer} of every finished node, plus "refused" when it refuses; None when it gives no answer."""
    STATS["evaluations"] += 1
    return W.evaluate(Checker, e, list(files), {n: _blob(b) for n, b in files.items()}, [0])


def top(e, g):
    if g is None:
        return None
    if id(e) in g:
        return g[id(e)]
    c = g.get("refused") or ""
    return ("V", c) if c[:1] == "V" else None


def answer(stmt, files, lets=None):
    e = expr_of(stmt, lets) if isinstance(stmt, str) else stmt
    a = top(e, answers_of(e, files))
    STATS["answered"] += a is not None and a[0] != "V"
    return a


def check_line(program, store):
    """(True, [line]) for a one-claim program `file N = sha256:H`*, `let N = E`*, `claim E`, its line from ground truth
    in the kernel's shape: "formed: holds", "formed: <answer>", or "refused [CODE, truth]" (V001 for a comparison that
    does not hold; a V, K or I code as evaluated; N000 for no answer)."""
    files, lets, stmt = {}, {}, None
    for ln in (program.decode() if isinstance(program, bytes) else program).splitlines():
        m = re.match(r"file (\w+) = sha256:(\w+)$", ln)
        if m:
            files[m.group(1)] = store.blobs[m.group(2)]
            continue
        m = re.match(r"let (\w+) = (.*)$", ln)
        if m:
            lets[m.group(1)] = m.group(2)
            continue
        if ln.startswith("claim "):
            stmt = ln[6:]
    e = expr_of(stmt, lets)
    g = answers_of(e, files)
    a = top(e, g)
    if a is None:
        c = (g or {}).get("refused") or "N000"
        return True, [f"line 0: refused [{c if c[:1] in 'KI' else 'N000'}, truth]"]
    if a[0] == "V":
        return True, [f"line 0: refused [{a[1]}, truth]"]
    STATS["answered"] += 1
    if a == ("bool", False):
        return True, ["line 0: refused [V001, truth]"]
    return True, ["line 0: formed: holds" if a == ("bool", True) else f"line 0: formed: {a!r}"]


def recheck_w1(stmt, tables, slot="f", lets=None, fn=None):
    """A W1 refusal re-checked over tables (bytes or str): contradicted when two tables answer differently (a value
    refusal is not an answer, SPEC 4.4). The value is the top, or with fn (the refusal's "fn():") every sub-value
    calling fn: contradicted when one of them answers twice (name the refusal's own value when two share fn)."""
    e = expr_of(stmt, lets)
    vals = [e] if fn is None else [v for v in W.subexprs(e) if getattr(v, "fn", None) == fn]
    assert vals, f"no {fn}() in {stmt}"
    seen, judged = {id(v): set() for v in vals}, 0
    for X in tables:
        g = answers_of(e, {slot: X})
        got = [(v, top(v, g) if v is e else (g or {}).get(id(v))) for v in vals]
        got = [(v, a) for v, a in got if a is not None and a[0] != "V"]
        judged += bool(got)
        for v, a in got:
            seen[id(v)].add(a)
    STATS["answered"] += judged
    hit = [a for a in seen.values() if len(a) > 1]
    return Recheck("unjudged" if not judged else "contradicted" if hit else "ok",
                   hit[0] if hit else set().union(*seen.values()), judged)


def fn_of(line):
    """The value a refusal line names ("...]: fn(): ...")."""
    m = re.search(r"\]: (\w+)\(\)", line)
    return m and m.group(1)


def recheck_s011(stmt, tables, slot="f", lets=None):
    """An S011 (a comparison that holds on no readable input) re-checked: contradicted when one table holds."""
    r = recheck_w1(stmt, tables, slot, lets)
    return r._replace(status="unjudged" if not r.judged else "contradicted" if ("bool", True) in r.answers else "ok")


def recheck_w2(stmt, part, tables, slot="f", lets=None):
    """A W2 refusal (the part does not bear) re-checked: contradicted when on one table stmt with and without the part
    give different outcomes (a value refusal is an outcome, any other refusal none; SPEC 4.4 10). part: its index in
    witness.parts, or its description (every part with that description is tried: name the index when two share it)."""
    e = expr_of(stmt, lets)
    ps = W.parts(e)
    vs = [W._subst(e, *ps[part][:2])] if isinstance(part, int) else [W._subst(e, node, mod) for node, mod, d in ps if d == part]
    assert vs, f"no part {part!r} in {stmt}"
    seen, judged = set(), 0
    for X in tables:
        a = top(e, answers_of(e, {slot: X}))
        if a is None:
            continue
        for v in vs:
            b = top(v, answers_of(v, {slot: X}))
            if b is not None:
                judged += 1
                if a != b:
                    seen.add((a, b))
    STATS["answered"] += judged
    return Recheck("unjudged" if not judged else "contradicted" if seen else "ok", seen, judged)


SELF_TABLES = ["g\tx\n" + "".join(f"{g}\t{x}\n" for g, x in rows) for rows in
               ([("A", "1")], [("A", "1"), ("B", "2")], [("B", "0")], [("A", "2"), ("A", "3")])]


def selftest():
    """A deliberately wrong W1 refusal (count of A rows varies), a wrong W2 one (the condition bears) and a wrong S011
    one (holds on one table) must each be contradicted; a true W1 one (rows(t) - count(t) is 0) must not be."""
    bad = []
    if recheck_w1('count(where(t, eq("g", "A")))', SELF_TABLES).status != "contradicted":
        bad.append("wrong W1 not caught")
    if recheck_w2('count(where(t, eq("g", "A")))', 'the condition eq(...)', SELF_TABLES).status != "contradicted":
        bad.append("wrong W2 not caught")
    if recheck_s011('atleast(count(where(t, eq("g", "A"))), c = 2)', SELF_TABLES).status != "contradicted":
        bad.append("wrong S011 not caught")
    if recheck_w1("difference(rows(t), count(t))", SELF_TABLES).status != "ok":
        bad.append("true W1 contradicted")
    assert not bad, bad
    return True

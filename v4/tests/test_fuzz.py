"""Finding 13: no input makes the checker crash. Mutants of the programs in progs.py, run
against the same supplied files; every one must end in a verdict."""
import random

import helpers
import progs
from reality4 import readers
from reality4.kernel import check

ALPHABET = list('()",=/#-.:0123456789 \tabcdefghijklmnopqrstuvwxyzABCRT_') + ["\x00", "\u00e9", "\r", "\n", "99999999999999999999999999", "-1", "sha256:"]


def mutate(rng, s):
    k = rng.randrange(6)
    i = rng.randrange(len(s) + 1)
    if k == 0 and s:
        return s[:i] + s[i + 1:]
    if k == 1:
        return s[:i] + rng.choice(ALPHABET) + s[i:]
    if k == 2:
        j = rng.randrange(len(s) + 1)
        return s[:min(i, j)] + s[max(i, j):]
    if k == 3:
        lines = s.split("\n")
        a, b = rng.randrange(len(lines)), rng.randrange(len(lines))
        lines[a], lines[b] = lines[b], lines[a]
        return "\n".join(lines)
    if k == 4:
        j = rng.randrange(len(s) + 1)
        return s[:i] + s[min(i, j):max(i, j)] + s[i:]
    return s.replace("1", rng.choice(["0", "-1", "999999999999999999999", "1.5", "1/0"]), 1)


def test_mutants_never_crash(box, tmp_path):
    p, h = helpers.tsv(tmp_path, "small.tsv", progs.SMALL)
    store = readers.Store([box[0], box[1], p], [box[1]])
    rng = random.Random(7)
    n = 0
    for prog in progs.programs(box[2], h):
        for _ in range(60):
            m = prog
            for _ in range(rng.randint(1, 3)):
                m = mutate(rng, m)
            store.steps.n = 0
            ok, out = check(m.encode("utf-8"), store)
            assert out and out[-1].startswith(("accepted", "refused"))
            assert not any("[X001" in line for line in out), (m, out)
            n += 1
    print(n, "mutants, all with a verdict")


def test_edge_values(tmp_path):
    p, h = helpers.tsv(tmp_path, "s.tsv", "id\n1\n")
    prog = (f"file t = sha256:{h}\nclaim bytes(t, 99999999999999999999999, 1)\nclaim bytes(t, 9223372036854775806, 1)\n"
            "claim cell(tsv(t), 99999999999999999999999999, 1)\nclaim exceeds(number(cell(tsv(t), 1, 1)), c = 1/0)\n"
            "claim number(cell(tsv(t), 1, 1)) is 1/0\nclaim number(cell(tsv(t), 1, 1)) is 00001\nclaim bytes(t, 0, 5000)\n")
    ok, text = helpers.run(prog, [p])
    assert "X001" not in text and "formed: Decimal" in text


def test_bounds(tmp_path):
    """v3: let is evaluated once (call-by-value), so a long chain of lets costs one step per name and
    forms; nesting depth and program size are bounded (R001), never the interpreter's stack."""
    p, h = helpers.tsv(tmp_path, "s.tsv", "id\n1\n")
    chain = "".join(f"let a{i + 1} = a{i}\n" for i in range(5000))
    ok, text = helpers.run(f"file t = sha256:{h}\nlet a0 = tsv(t)\n" + chain + "claim rows(a5000)\n", [p])
    deep = "rows(" * 300 + "a0" + ")" * 300
    ok2, text2 = helpers.run(f"file t = sha256:{h}\nlet a0 = tsv(t)\nclaim {deep}\n", [p])
    assert ok and "RowCount[TSV[#1]] = 1" in text, text[-400:]
    assert "R001" in text2 and "X001" not in text + text2



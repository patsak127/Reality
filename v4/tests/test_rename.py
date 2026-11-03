"""Item 3: renaming user names one-to-one does not change the output at all (names are never
printed and never decide anything). A fuzzer over the acceptance programs and others."""
import random
import re

import pytest

import helpers
import progs

KEYWORDS = {"file", "dataset", "let", "claim", "is"}
TOK = re.compile(r'"(?:[^"\\]|\\.)*"|sha256:[0-9a-f]{64}|#.*|[A-Za-z_][A-Za-z0-9_]*|\s+|.')


def declared(prog):
    return [m.group(2) for m in re.finditer(r"^(file|dataset|let)\s+([A-Za-z_][A-Za-z0-9_]*)", prog, re.M)]


def rename(prog, mapping):
    out = []
    for line in prog.split("\n"):
        toks = TOK.findall(line)
        res = []
        for i, t in enumerate(toks):
            nxt = next((u for u in toks[i + 1:] if not u.isspace()), "")
            prev = next((u for u in reversed(toks[:i]) if not u.isspace()), "")
            is_decl = prev in ("file", "dataset", "let")
            if t in mapping and nxt != "(" and (nxt != "=" or is_decl):
                res.append(mapping[t])
            else:
                res.append(t)
        out.append("".join(res))
    return "\n".join(out)


def fresh(rng, used):
    while True:
        n = rng.choice("abcdefghijklmnopqrstuvwxyzXYZ_") + "".join(rng.choice("abcxyz0123456789_") for _ in range(rng.randint(0, 6)))
        if n not in KEYWORDS and n not in used:
            used.add(n)
            return n


@pytest.fixture(scope="module")
def setting(box, tmp_path_factory):
    d = tmp_path_factory.mktemp("small")
    p, h = helpers.tsv(d, "small.tsv", progs.SMALL)
    return progs.programs(box[2], h), [box[0], box[1], str(d)], [box[1]]


def test_rename_fuzz(setting):
    programs, files, roots = setting
    rng = random.Random(20261024)
    n = 0
    for prog in programs:
        names = list(dict.fromkeys(declared(prog)))
        _, base = helpers.run(prog, files, roots)
        for _ in range(6):
            used = set(names)
            mapping = {x: fresh(rng, used) for x in names}
            renamed = rename(prog, mapping)
            assert renamed != prog or not names
            _, text = helpers.run(renamed, files, roots)
            assert text == base, (prog, mapping)
            n += 1
    assert n >= 60


def test_swap_two_names(setting):
    """No rule refuses a name for its spelling: swapping two names changes nothing."""
    programs, files, roots = setting
    for prog in programs:
        names = list(dict.fromkeys(declared(prog)))
        if len(names) < 2:
            continue
        _, base = helpers.run(prog, files, roots)
        _, text = helpers.run(rename(prog, {names[0]: names[1], names[1]: names[0]}), files, roots)
        assert text == base

"""The integer step (src/reality4/intstep.py, SPEC-EXACT 4) against brute force and against Exact.lean's
decide as Lean evaluates it."""
import itertools
import os
import random
import shutil
import sys

import pytest

from reality4 import intstep as I

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))


def brute(atoms, nv, n):
    for x in itertools.product(range(n), repeat=nv):
        if all(I.holds(a, dict(enumerate(x))) for a in atoms):
            return dict(enumerate(x))
    return None


def rand_system(rng):
    nv = rng.randint(1, 3)
    atoms = []
    for _ in range(rng.randint(1, 4)):
        f = I.form({v: rng.randint(-4, 4) for v in range(nv)}, rng.randint(-12, 12))
        atoms.append(("ge", f) if rng.random() < 0.75 else ("dvd", rng.randint(0, 5), f))
    return nv, atoms


def test_agrees_with_brute_force():
    """3,600 random systems (divisibility atoms, modulus 0 included): a solution is a solution, and
    'none' is never said of a system brute force solves in [0, 40)^3."""
    rng = random.Random(7)
    seen = {"sat": 0, "unsat": 0}
    for _ in range(3600):
        nv, atoms = rand_system(rng)
        x, _ = I.solve(atoms, 10 ** 6)
        if x is not None:
            assert all(I.holds(a, x) for a in atoms), atoms
            seen["sat"] += 1
        else:
            assert brute(atoms, nv, 40) is None, atoms
            seen["unsat"] += 1
    assert seen["sat"] > 600 and seen["unsat"] > 400, seen


def test_unsat_without_a_bound():
    two = [("ge", I.form({0: 2, 1: -2}, -1)), ("ge", I.form({0: -2, 1: 2}, 1))]   # 2x - 2y = 1
    assert I.solve(two, 1000)[0] is None
    assert I.solve([("dvd", 3, I.form({0: 1}, 1)), ("ge", I.form({0: -1}, 1))], 1000)[0] is None
    assert I.solve([("dvd", 3, I.form({0: 1}, 1)), ("ge", I.form({0: -1}, 2))], 1000)[0] == {0: 2}
    assert I.solve([("dvd", 0, I.form({0: 1}, -5))], 1000)[0] == {0: 5}


def test_large_constants_cost_no_more():
    for p, q in ((1, 2), (333, 1000), (1, 10 ** 6), (999999, 10 ** 6), (10 ** 40 - 1, 10 ** 40)):
        atoms = [("ge", I.form({0: 1, 1: 1}, -1)), ("ge", I.form({0: q - p, 1: -p}, -1))]
        x, calls = I.solve(atoms, 1000)
        assert x is not None and all(I.holds(a, x) for a in atoms) and calls < 20


def test_too_big_refuses():
    nv, atoms = 2, [("ge", I.form({0: 7, 1: -5}, -1)), ("ge", I.form({0: -7, 1: 5}, 3)), ("dvd", 11, I.form({0: 3, 1: 1}, 4))]
    _, calls = I.solve(atoms, 10 ** 6)
    with pytest.raises(I.TooBig):
        I.solve(atoms, calls - 1)


@pytest.mark.skipif(not shutil.which(os.path.expanduser("~/.elan/bin/elan")), reason="Lean (elan) not installed")
def test_same_steps_as_lean():
    """300 random systems: Lean's decideTop pickStd, Lean's call-counting copy and intstep agree on the
    answer and on the number of calls."""
    import exact_lean_diff as D
    systems, _ = D.random_systems(300, seed=11)
    bad, _ = D.compare(systems, 300)
    assert not bad, bad[:3]


def test_enumeration_rule():
    """Call 2 (27 Oct 2026): a variable with an explicit range 0..B (a ge atom with its coefficient < 0 and none
    > 0) no larger than Cooper's branches is tried at each value (Exact.enum_rule). It agrees with brute force,
    and a system whose only bound is explicit and small decides in a few calls whatever its coefficients."""
    rng = random.Random(29)
    used = 0
    for _ in range(2000):
        nv, atoms = rand_system(rng)
        atoms.append(("ge", I.form({v: -rng.randint(1, 3) for v in range(nv)}, rng.randint(0, 9))))
        na = I.normalize(atoms)
        used += any(I.ub(na, j) is not None and I.ub(na, j) + 1 <= I.branches(na, j) for j in range(nv))
        x, _ = I.solve(atoms, 10 ** 6)
        if x is not None:
            assert all(I.holds(a, x) for a in atoms), atoms
        else:
            assert brute(atoms, nv, 12) is None, atoms
    assert used > 1000, used
    big = 10 ** 999
    atoms = [("ge", I.form({0: -1, 1: -1}, 5)), ("ge", I.form({0: big, 1: -big - 1}, 0)), ("ge", I.form({0: 1, 1: 1}, -1))]
    x, calls = I.solve(atoms, 1000)
    assert x is not None and all(I.holds(a, x) for a in atoms) and calls < 20
    assert I.ub([("ge", I.form({0: -3, 1: -1}, 10))], 0) == 3 and I.ub([("ge", I.form({0: -3, 1: 1}, 10))], 0) is None

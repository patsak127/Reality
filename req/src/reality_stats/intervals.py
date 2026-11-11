"""Wilson / bootstrap / kappa / seed-variance — pure stdlib, deterministic with pinned seed."""
from __future__ import annotations

import math
import random
from fractions import Fraction


def wilson_lower(k: int, n: int, conf: float = 0.95) -> Fraction:
    """Lower bound of the Wilson score interval for k successes in n trials.

    conf is the central confidence (e.g. 0.95). Uses a normal z from a small
    table (exact Fraction), not a live scipy call.
    """
    if n <= 0 or k < 0 or k > n:
        raise ValueError(f"need 0 <= k <= n and n > 0; got k={k} n={n}")
    if not (0 < conf < 1):
        raise ValueError(f"conf must be in (0,1); got {conf}")
    z_table = {
        Fraction(90, 100): Fraction(1645, 1000),
        Fraction(95, 100): Fraction(1960, 1000),
        Fraction(99, 100): Fraction(2576, 1000),
    }
    cf = Fraction(conf).limit_denominator(1000)
    if cf not in z_table:
        cf = min(z_table.keys(), key=lambda x: abs(float(x) - conf))
    z = z_table[cf]
    z2 = z * z
    nn = Fraction(n)
    kk = Fraction(k)
    denom = nn + z2
    centre = (kk + z2 / 2) / denom
    phat = kk / nn
    rad = phat * (1 - phat) / nn + z2 / (4 * nn * nn)
    pad_f = float(z) * math.sqrt(float(rad)) / float(denom)
    pad = Fraction(pad_f).limit_denominator(10**9)
    lo = centre - pad
    if lo < 0:
        return Fraction(0)
    return lo.limit_denominator(10**9)


def bootstrap_ci_lower(
    successes: list[int],
    *,
    seed: int,
    n_boot: int = 2000,
    conf: float = 0.95,
) -> Fraction:
    """Bootstrap lower CI for a Bernoulli mean.

    `successes` is a 0/1 list (one entry per trial). Seed and n_boot must be
    pinned in the adopted measure / producer invocation.
    """
    if not successes:
        raise ValueError("empty successes")
    if n_boot < 1:
        raise ValueError("n_boot >= 1")
    rng = random.Random(seed)
    n = len(successes)
    means = []
    for _ in range(n_boot):
        s = sum(successes[rng.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    alpha = 1 - conf
    idx = int(math.floor(alpha / 2 * n_boot))
    idx = max(0, min(n_boot - 1, idx))
    return Fraction(means[idx]).limit_denominator(10**9)


def seed_variance_lower(
    successes: list[int],
    *,
    seed: int,
    n_runs: int,
    n_boot: int = 2000,
    conf: float = 0.95,
) -> tuple[Fraction, Fraction]:
    """Mean and sample variance of bootstrap lower-CI across N pinned seeds.

    Seeds used: seed, seed+1, ..., seed+n_runs-1. Returns (mean_lo, variance).
    """
    if n_runs < 1:
        raise ValueError("n_runs >= 1")
    los = [
        bootstrap_ci_lower(successes, seed=seed + i, n_boot=n_boot, conf=conf)
        for i in range(n_runs)
    ]
    mean = sum(los, Fraction(0)) / Fraction(n_runs)
    if n_runs == 1:
        return mean.limit_denominator(10**9), Fraction(0)
    var = sum((x - mean) ** 2 for x in los) / Fraction(n_runs - 1)
    return mean.limit_denominator(10**9), var.limit_denominator(10**9)


def cohens_kappa(a: list[str], b: list[str]) -> Fraction:
    """Cohen's kappa for two equal-length label lists."""
    if len(a) != len(b) or not a:
        raise ValueError("label lists must be non-empty and equal length")
    n = len(a)
    labels = sorted(set(a) | set(b))
    idx = {lab: i for i, lab in enumerate(labels)}
    m = len(labels)
    mat = [[0] * m for _ in range(m)]
    for x, y in zip(a, b):
        mat[idx[x]][idx[y]] += 1
    po = sum(mat[i][i] for i in range(m)) / n
    row = [sum(mat[i][j] for j in range(m)) / n for i in range(m)]
    col = [sum(mat[i][j] for i in range(m)) / n for j in range(m)]
    pe = sum(row[i] * col[i] for i in range(m))
    if pe == 1:
        return Fraction(1)
    return (Fraction(po - pe) / Fraction(1 - pe)).limit_denominator(10**9)

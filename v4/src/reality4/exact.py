"""Exact square roots for the standard deviations (v4 SPEC 7.2).

A Surd is a + sqrt(v) with a, v exact rationals, v >= 0 and v not the square of a rational (a
root that is rational is returned as a Fraction instead, so a Surd never equals a Fraction).
Comparisons with rationals and with other Surds of the same v are decided exactly by squaring;
nothing is ever rounded. Arithmetic is only what widen() needs: adding or subtracting a rational."""
from fractions import Fraction
from math import isqrt


def _rational_sqrt(v: Fraction):
    n, d = v.numerator, v.denominator
    rn, rd = isqrt(n), isqrt(d)
    if rn * rn == n and rd * rd == d:
        return Fraction(rn, rd)
    return None


def sqrt(v: Fraction):
    if v < 0:
        raise ValueError("negative")
    r = _rational_sqrt(v)
    return r if r is not None else Surd(Fraction(0), v)


def _root_gt(v: Fraction, d: Fraction) -> bool:
    """sqrt(v) > d, exactly."""
    return d < 0 or v > d * d


def _root_lt(v: Fraction, d: Fraction) -> bool:
    """sqrt(v) < d, exactly (never equal: v is not a rational square)."""
    return d > 0 and v < d * d


class SurdMix(Exception):
    """Two Surds of different radicands, or a Surd minus a Surd: not decided in v4."""


class Surd:
    __slots__ = ("a", "v")

    def __init__(self, a: Fraction, v: Fraction):
        self.a, self.v = Fraction(a), Fraction(v)

    def _cut(self, o):
        if isinstance(o, Surd):
            if o.v != self.v:
                raise SurdMix()
            return None
        return Fraction(o) - self.a

    def __gt__(self, o):
        d = self._cut(o)
        return self.a > o.a if d is None else _root_gt(self.v, d)

    def __lt__(self, o):
        d = self._cut(o)
        return self.a < o.a if d is None else _root_lt(self.v, d)

    def __ge__(self, o):
        return not self < o

    def __le__(self, o):
        return not self > o

    def __eq__(self, o):
        return isinstance(o, Surd) and o.a == self.a and o.v == self.v

    def __ne__(self, o):
        return not self == o

    def __hash__(self):
        return hash(("surd", self.a, self.v))

    def __add__(self, o):
        if isinstance(o, Surd):
            raise SurdMix()
        return Surd(self.a + Fraction(o), self.v)

    __radd__ = __add__

    def __sub__(self, o):
        if isinstance(o, Surd):
            raise SurdMix()
        return Surd(self.a - Fraction(o), self.v)

    def __rsub__(self, o):
        raise SurdMix()

    def __neg__(self):
        raise SurdMix()

    def text(self, fmt) -> str:
        root = f"sqrt({fmt(self.v)})"
        if self.a == 0:
            return root
        return f"{root} {'+' if self.a > 0 else '-'} {fmt(abs(self.a))}"

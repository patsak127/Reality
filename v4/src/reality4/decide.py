"""The exact decision of W1 and W2 for part T (SPEC-EXACT): row types per table slot, the rows a
statement names (by position, by key, the header) as finitely many cases, values as forms over row
counts and named cell values, each question as systems for the integer step (intstep) after the
named cell values are eliminated exactly, and every "yes" turned into bytes and confirmed by the
real readers and evaluator (witness.evaluate). A "no" refuses; a "yes" the real code does not
confirm is no verdict (X001)."""
import collections
import functools
import hashlib
import itertools
import json
import struct
import zlib
from fractions import Fraction
from math import floor, gcd, isqrt, lcm
from . import bids101 as B
from . import cert as C
from . import intstep as I
from . import readers as R
from .keys import invisible, is_key, skeleton
from .syntax import Call, Dec, Int, Name, Ratio, Str
from . import witness as W

CMP = ("exceeds", "below", "atleast", "atmost")
NUMC = {"ge": lambda q, c: q >= c, "gt": lambda q, c: q > c, "le": lambda q, c: q <= c, "lt": lambda q, c: q < c}
AGG = {"sum": "Sum", "mean": "Mean", "max": "Max", "min": "Min", "order": "Order", "median": "Median"}
VARF = {"sample_variance": 1, "population_variance": 0, "sample_sd": 1, "population_sd": 0}   # ddof
FNS = ("tsv", "csv", "where", "eq", "ne", "rows", "count", "share", "difference", "cell", "key", "header", "number", "widen",
       "json", "member", "item", "nifti", "dim", "pixdim", "size", "bytes", "bids", "participants", "recording", "acq", "rec", "tr", "volumes", "onset", "recordings", "duration", "events", "trials", "participant", "extra") + tuple(NUMC) + CMP + tuple(AGG) + tuple(VARF)
READS = {"tsv": "tsv", "csv": "csv", "json": "json", "nifti": "nifti", "size": "raw", "bytes": "raw"}   # part H: one reader per file
MAX_DIM = 2 ** 63 - 1   # NIfTI-2's int64 dims; NIfTI-1's int16 dims reach 32767 (SPEC 7.6)
TRLO, TRHI = Fraction(1, 2 ** 1075 * 10 ** 6), Fraction(17, 10) * 10 ** 308   # (2c) RepetitionTime: nearest() > 0 in us, < its limit in s
MAX_VOL = 10 ** 6    # (2c) volumes a certificate's BOLD image holds (a byte each) [prov]; more refuses R013
MAX_ROWS = 100_000   # rows of one slot in one certificate input [prov]; a smaller one not existing refuses R013 (D3)
MAX_CASES = 10_000   # cases of one question (SPEC-EXACT 3.4) [prov]; more refuses R013
RSQ = ("volumes", "events", "tr", "trials")   # (R1) the quantities of a recording set (kernel.RSET_QUANTITIES)
RECF = ("tr", "volumes", "onset", "duration", "events", "trials")   # (2c, item 3) a named recording's values
RSBAD = {"volumes": ("3d",), "events": ("noev",), "trials": ("noev", "nocol"), "tr": ()}   # (R1) a recording whose value refuses
RSCODE = {"3d": "V008", "noev": "V007", "nocol": "V002"}
ONE = 1              # a form's constant: {variable: coefficient, ONE: constant}
STEP_BYTES = (2 ** 31 - R.MAX_ACCOUNTED) // W.MAX_WITNESS_STEPS   # 21: a step's share of the floor (SPEC 9.4) less the program's bytes
MEM, MEM_STEPS = [0], W.MAX_WITNESS_STEPS   # memory held now in steps of STEP_BYTES (hold); its bound, the stated one fixed here (a test lowering the step bound meters steps only; SPEC-EXACT 8)


class NotT(Exception):
    """The statement is outside part T (SPEC-EXACT 2), or a value one level of W2 cannot be formed."""


class Big(Exception):
    """R013: the message says what needs more than the bound."""


class Past(Big):
    """(F02) A bound the decision met past which the unbounded model still has inputs (more than MAX_ROWS rows, or
    a certificate the reader refuses past its read limit, R003): check() decides the statement again on the readable
    inputs only (each table at most MAX_TEXT_FILE, the text at most MAX_TEXT_TOTAL; SPEC-EXACT 1); as a refusal, R013."""


class OverRows(Past):
    """R013 shown, not searched: every witness has more than MAX_ROWS rows in one table (D3; item (h))."""


class OverRead(Past):
    """(F02) A certificate input the real reader refuses past its read limit (R003): with the limit modelled, R013."""


class Unchecked(Exception):
    """(C4) a refusal's certificate check passed a bound: the replay stops (find does not catch it: not a Big)."""


class Unreadable(Big):
    """R013 from back-substitution: no readable value between the ends it chose (P1)."""


def num(B):
    """Accounted bytes of a number whose numerator and denominator have at most B bits, above CPython's: a Fraction and
    its two ints (64 bytes each) and their digits (B // 7 + 1 bytes each; CPython keeps 4 bytes per 30 bits)."""
    return 3 * 64 + 2 * (B // 7 + 1)


def bits(cs):
    return max((max(abs(c.numerator).bit_length(), c.denominator.bit_length()) for c in cs), default=1)   # ints and Fractions


def side(budget, n):
    """n steps of side work (implied's tests) on the step bound only (SPEC-EXACT 8, item (g)): a round's budget is [steps,
    headroom above the steps really spent]; side work takes the headroom first, so a round's cap counts its solves only."""
    if len(budget) > 1:
        d = min(n, budget[1])
        budget[1] -= d
        n -= d
    budget[0] += n


CHK = [0, False, 0]   # (cert.py) checking's own account: steps spent checking, whether a "none" went unchecked, a refusal's replay steps
RB = [True]   # (F02) the read limit modelled (Model.rb): check() decides without it first, then with it after a Past
HELD = [0]   # (H03) the accounted bytes the program holds before the statement, less its own files' (readers.Store.held)
PRE = [None]   # (B0304) the earlier statements a certificate runs again on its candidate (prefix)
PEND, PM = [], [0]   # (cert.py, C4) the question's "none" finds (options, what) and shares, kept for a refusal's check; their memory


def pay(n):
    """n steps of checking certificates, in their own account (CHK) against the stated bound, never in the decision's
    budget: a verdict does not depend on the checks (BB's call 17:10); past the bound, Big, caught where it is checked."""
    CHK[0] += n
    if CHK[0] > W.MAX_WITNESS_STEPS:
        raise Big(f"checking its certificates needs more than {W.MAX_WITNESS_STEPS} counted steps (SPEC-EXACT 6.1, 8)")


pay.left = lambda: max(1, W.MAX_WITNESS_STEPS - CHK[0])


def hold(held, nbytes):
    """BB's call (28 Oct 2026 09:05): running out of memory is never an outcome. A structure that grows with a system is
    charged before it is built, or grown, to nbytes accounted bytes: STEP_BYTES a step against the stated bound, in
    MEM, the memory held now (only the steps above held[0], those already held for it; its owner gives them back,
    MEM[0] -= held[0], when it is freed). Past MEM_STEPS, R013, never MemoryError: the exact path's working
    memory stays under the floor less the program's accounted bytes (SPEC-EXACT 8). Steps done are counted apart."""
    need = -(-nbytes // STEP_BYTES)
    if need > held[0]:
        MEM[0] += need - held[0]
        held[0] = need
        if PM[0] and MEM[0] + PM[0] > MEM_STEPS:   # (C4) what a refusal's check would need is dropped first: the
            PEND[:], PM[0], CHK[1] = [], 0, True     # decision never meets it; a refusal now is not checked (R013)
        if MEM[0] > MEM_STEPS:
            raise Big(f"deciding it needs more than {MEM_STEPS} steps of memory held at {STEP_BYTES} bytes a step (SPEC-EXACT 8)")


def kept_bytes(x, seen=None):
    """(C4) Accounted bytes of what a refusal's check keeps (find's options, shares' forms): as size_of, each object
    once (the options of one find share their cases: counted per option they were 1.35 GB for pn472's 7,190 options,
    16.8 MB once), and an atom that is a tuple with attributes (RAtom, PAtom) counted as both."""
    seen = set() if seen is None else seen
    if id(x) in seen:
        return 0
    seen.add(id(x))
    if isinstance(x, dict):
        return 256 + sum(64 + kept_bytes(k, seen) + kept_bytes(v, seen) for k, v in x.items())
    if isinstance(x, (list, tuple, set, frozenset)):
        return 64 + sum(8 + kept_bytes(e, seen) for e in x) + (kept_bytes(vars(x), seen) if hasattr(x, "__dict__") else 0)
    if hasattr(x, "__dict__") and not isinstance(x, int):
        return 64 + kept_bytes(vars(x), seen)
    return size_of(x)


def size_of(x):
    """Accounted bytes of a case or a branch (SPEC-EXACT 8): each container, number and text counted as its own, shared
    or not (above CPython's: 256 a dict and 64 an entry, 64 a list or tuple and 8 an entry, num() a number)."""
    if isinstance(x, dict):
        return 256 + sum(64 + size_of(k) + size_of(v) for k, v in x.items())
    if hasattr(x, "__dict__"):
        return 64 + size_of(vars(x)) + (num(int(x).bit_length()) if isinstance(x, int) else 0)
    if isinstance(x, (list, tuple, set, frozenset)):
        return 64 + sum(8 + size_of(e) for e in x)
    if isinstance(x, (int, Fraction)):
        return num(bits([x]))
    return 49 + len(x) if isinstance(x, (str, bytes)) else 64


def take(it, held):
    """At most MAX_CASES + 1 cases of it, each held before it is kept (SPEC-EXACT 8)."""
    out = []
    for c in itertools.islice(it, MAX_CASES + 1):
        hold(held, held[0] * STEP_BYTES + size_of(c))
        out.append(c)
    return out


def scoped(f):
    """A Decide method whose cases and branches (held in self.bh) are given back when it returns (SPEC-EXACT 8)."""
    def g(self, *a, **k):
        h, self.bh = self.bh, [0]
        try:
            return f(self, *a, **k)
        finally:
            MEM[0] -= self.bh[0]
            self.bh = h
    return g


CERTS = {}   # (cert.py) leaf certificates checked, by how the leaf ended; "box" leaves are not certified yet (PLAN.md 6)


def lin(*terms):
    """The form sum of k * F over (k, F) pairs."""
    d = {}
    for k, F in terms:
        for v, c in F.items():
            d[v] = d.get(v, 0) + k * c
    return {v: c for v, c in d.items() if c}


def const(c):
    return {ONE: c} if c else {}


def ge(F):
    return (F, False)   # F >= 0


def gt(F):
    return (F, True)    # F > 0


def ground(a):
    return all(v == ONE for v in a[0])


def value(F, x):
    return sum(c * (1 if v == ONE else x.get(v, 0)) for v, c in F.items())


def holds(a, x):
    v = value(a[0], x)
    return v > 0 if a[1] else v >= 0


def prune(branches):
    """Branches with a false ground atom dropped, true ground atoms removed."""
    out = []
    for A, r in branches:
        if all(holds(a, {}) for a in A if ground(a)):
            out.append(([a for a in A if not ground(a)], r))
    return out


def natom(a):
    """The negation of an atom."""
    return (lin((-1, a[0])), not a[1])


def weak(g):
    """The weak orders of g values, as ranks 0, 1, ... (ties share a rank)."""
    return [r for r in itertools.product(range(g), repeat=g) if sorted(set(r)) == list(range(max(r) + 1))]


def nonnum(r):
    """A JSON string or tree where a number is needed: the kernel refuses S007 (no answer)."""
    return ("X", "S007") if r[0] in ("bytes", "jtree") else r


def vchain(e):
    """The variance or SD under a chain of widen() (item 5a), or None."""
    while isinstance(e, Call) and e.fn == "widen" and e.args:
        e = e.args[0]
    return e if isinstance(e, Call) and e.fn in VARF else None


def dchain(e):
    """The difference of two variances under a chain of widen() (item 5b), or None."""
    while isinstance(e, Call) and e.fn == "widen" and e.args:
        e = e.args[0]
    ok = isinstance(e, Call) and e.fn == "difference" and len(e.args) == 2 and not e.params
    return e if ok and all(isinstance(x, Call) and x.fn in VARF for x in e.args) else None


def nchain(e):
    """(3.7, the variance shape) a difference of variances under widen() chains, at least three, or two with a widen()
    inside: its terms [(sign, variance)] and its total width; else None (a plain variance or 5b difference: vchain, dchain)."""
    if not (isinstance(e, Call) and e.fn in ("widen", "difference")) or dchain(e) or vchain(e):
        return None
    terms, todo = [], [(1, e)]
    while todo:
        sg, x = todo.pop()
        while isinstance(x, Call) and x.fn == "widen" and len(x.args) == 1:
            x = x.args[0]
        if isinstance(x, Call) and x.fn == "difference" and len(x.args) == 2 and not x.params:
            todo += [(sg, x.args[0]), (-sg, x.args[1])]
        elif isinstance(x, Call) and x.fn in VARF:
            terms.append((sg, x))
        else:
            return None
    return terms, nwidth(e)


def nwidth(e, skip=None):
    """The half-width of a difference tree's widened value (SPEC 5.2): each widen() adds its tolerance, signed as its
    place in the tree, to the symbol of its base (the value under its widen() chain, O9); one value is one symbol, so
    widen(V) − widen(V) cancels; the width is the sum of the symbols' |coefficients|. skip: a widen() node left out."""
    co, todo = {}, [(1, e)]
    while todo:
        sg, x = todo.pop()
        if isinstance(x, Call) and x.fn == "widen" and x.args:
            if x is not skip:
                b = x.args[0]
                while isinstance(b, Call) and b.fn == "widen" and b.args:
                    b = b.args[0]
                k = repr(b).replace("fn='csv'", "fn='tsv'")   # (A06, Argon review 06) the value's identity names no reader (SPEC 5.1; vranges)
                co[k] = co.get(k, 0) + sg * cutoff(x, "tolerance")
            todo.append((sg, x.args[0]))
        elif isinstance(x, Call) and x.fn == "difference" and len(x.args) == 2:
            todo += [(sg, x.args[0]), (-sg, x.args[1])]
    return sum(abs(c) for c in co.values())


def width(e):
    """The total tolerance of the widen() chain above a variance (widths add, SPEC 5.2)."""
    w = Fraction(0)
    while e.fn == "widen":
        w, e = w + cutoff(e, "tolerance"), e.args[0]
    return w


def pneg(p, a=0):
    """The piece a − p of values (lo, lo closed, hi, hi closed; None: no bound)."""
    return (None if p[2] is None else a - p[2], p[3], None if p[0] is None else a - p[0], p[1])


def pclip(p, a=0):
    """The piece p + a cut to [0, ∞), or None when empty (item 5b)."""
    lo, lc, hi, hc = (None if p[0] is None else p[0] + a), p[1], (None if p[2] is None else p[2] + a), p[3]
    if lo is None or lo < 0:
        lo, lc = Fraction(0), True
    return None if hi is not None and (hi < lo or hi == lo and not (lc and hc)) else (lo, lc, hi, hc)


def rays(e, w=None):
    """(holds, fails) of the comparison e of a value under widen() chains of width w, as pieces of the value (5a)."""
    c, w = cutoff(e), width(e.args[0]) if w is None else w
    return {"exceeds": ((c + w, False, None, False), (None, False, c - w, True)), "atleast": ((c + w, True, None, False), (None, False, c - w, False)),
            "below": ((None, False, c - w, False), (c + w, True, None, False)), "atmost": ((None, False, c - w, True), (c + w, False, None, False))}[e.fn]


def pmeet(p, q):
    """The common part of two pieces (lo, lo closed, hi, hi closed; None: no bound), or None when empty."""
    if p is None or q is None:
        return None
    lo, lc = max([(p[0], p[1]), (q[0], q[1])], key=lambda e: (-1, 0) if e[0] is None else (0, e[0], not e[1]))
    hi, hc = min([(p[2], p[3]), (q[2], q[3])], key=lambda e: (1, 0) if e[0] is None else (0, e[0], e[1]))
    if lo is not None and hi is not None and (hi < lo or hi == lo and not (lc and hc)):
        return None
    return (lo, lc, hi, hc)


def unaff(r):
    """(base result, terms) of a number result: widened values carry their terms (SPEC 5.2)."""
    return (r[1], r[2]) if r[0] == "aff" else (r, {})


def id_cond(a, b):
    """None when value identities a and b differ on every input; else the (slot, types, types) whose
    row sets must be equal for them to be one identity ([]: always one)."""
    if a == b:
        return []
    if a[0] == "RS" == b[0] and a[1] == b[1] and a[2] == b[2] and a[5:] == b[5:]:   # (G01) one dataset's recordings sets: one
        return [(("rs", a[2], a[3], b[3]), a[4], b[4])]   # identity when they hold the same recordings (SPEC 5.1; Model.idsize)
    if a[0] != b[0] or len(a) != len(b) or a[0] in ("Decimal", "Header", "JSON", "size", "dim", "pixdim", "RS"):
        return None
    if a[0] in ("Difference", "Widened"):
        out = []
        for x, y in zip(a[1:], b[1:]):
            c = id_cond(x, y) if isinstance(x, tuple) else ([] if x == y else None)
            if c is None:
                return None
            out += c
        return out
    return [(a[1], a[2], b[2])] if a[1] == b[1] and a[3:] == b[3:] else None


def cutoff(e, slot="c"):
    """The one slot 'c' of a comparison or number condition (or 'tolerance' of widen; no unit) as a
    Fraction, else NotT."""
    if len(e.params) != 1 or e.params[0].slot != slot or e.params[0].unit not in (None, "s"):
        raise NotT("cutoff")   # "s" only with pixdim (the kernel checks units on the real bytes, by sort)
    v = e.params[0].value
    if isinstance(v, (Int, Dec)):
        return Fraction(v.v)
    if isinstance(v, Ratio):
        return Fraction(v.n, v.d)
    raise NotT("cutoff")


def norm(c):
    """A where() condition as (fn, column, literal bytes or cutoff), else NotT."""
    if isinstance(c, Call) and c.fn in ("eq", "ne") and len(c.args) == 2 and not c.params and isinstance(c.args[0], Int) and isinstance(c.args[1], Str):
        return (c.fn, c.args[0].v, c.args[1].v)
    if isinstance(c, Call) and c.fn in NUMC and len(c.args) == 1 and isinstance(c.args[0], Int):
        return (c.fn, c.args[0].v, cutoff(c))
    raise NotT("condition")


def key_of(e):
    """cell(t, key(k1, "v1", ...), k)'s pairs, sorted, else NotT."""
    a = e.args
    if len(a) < 2 or len(a) % 2 or e.params or not all(isinstance(a[j], Int) and isinstance(a[j + 1], Str) for j in range(0, len(a), 2)):
        raise NotT("key")
    return tuple(sorted((a[j].v, a[j + 1].v) for j in range(0, len(a), 2)))


def jpath(e):
    """(slot, path) of a member()/item() chain from json(f): path steps ("m", key bytes) or ("i", k)."""
    steps = []
    while isinstance(e, Call) and e.fn in ("member", "item"):
        if len(e.args) != 2 or e.params or not isinstance(e.args[1], Str if e.fn == "member" else Int) or (e.fn == "item" and e.args[1].v < 1):
            raise NotT(e.fn)
        steps.append(("m" if e.fn == "member" else "i", e.args[1].v))
        e = e.args[0]
    if not (isinstance(e, Call) and e.fn == "json"):
        raise NotT("json")
    return e.args[0].id, tuple(reversed(steps))


def rent(c):
    """(2c) a recording() call's entities (witness.rec_ents) as a sorted tuple."""
    return tuple(sorted(W.rec_ents(c).items()))


def rsel(e):
    """(R2) the dataset slot whose participants(bids(d)) a recordings() filter selects from (through where()s), else None."""
    while isinstance(e, Call) and e.fn == "where" and e.args:
        e = e.args[0]
    ok = isinstance(e, Call) and e.fn == "participants" and len(e.args) == 1 and isinstance(e.args[0], Call) and e.args[0].fn == "bids"
    return e.args[0].args[0].id if ok and e.args[0].args and isinstance(e.args[0].args[0], Name) else None


def rconds(x):
    """(R2) a recordings() call's filter as its conditions, as Model.br gathers them (None: no filter)."""
    if len(x.args) < 3:
        return None
    e, out = x.args[2], ()
    while e.fn == "where":
        out, e = tuple(map(norm, e.args[1:])) + out, e.args[0]
    return out


def tt_holds(b):
    """(G06, Opus 5.5 max review 06) whether an events file can hold the trial type b: the TSV reader refuses a double
    quote (T005) and the characters other readers take as a break (T006, readers._SEPARATORS), so a type holding one
    is in no readable events file: its count is 0 on every readable dataset."""
    t = b.decode("utf-8", "replace")
    return '"' not in t and not any(ch in R._SEPARATORS for ch in t)


def rs_lit(b):
    """(R1) a trial type the model takes: UTF-8 with no tab, line break or invisible character (else the kernel's
    own statement-level answer, outside the model)."""
    try:
        t = b.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return t != "" and not any(ch in t for ch in "\t\r\n") and invisible(t) is None


class RCase(dict):
    """(2c) a dataset slot's case: per named recording None (V004: not exactly one) or (dim[0] >= 4, the events file:
    None (V007) or how many of the onset rows named it has)."""

    def __hash__(self):
        return hash(tuple(sorted(self.items())))


def tslot(e):
    """W.slot_of, with participants(bids(d)) as the table slot d (item 2b)."""
    s = W.slot_of(e)
    return s[2:] if s and s.startswith("P:") else s


def plab(e):
    """(item 4) participant(bids(d), L)'s dataset slot d and label L (a BIDS label, else NotT: K001 on the real bytes)."""
    b = e.args[0] if e.args else None
    if len(e.args) != 2 or e.params or not (isinstance(b, Call) and b.fn == "bids" and len(b.args) == 1 and isinstance(b.args[0], Name)) or not isinstance(e.args[1], Str) or not is_key(e.args[1].v.decode("ascii", "replace")):
        raise NotT("participant")
    return b.args[0].id, e.args[1].v


def tsvof(e):
    """(3.13c) e is tsv(f), or a where() of it."""
    return isinstance(e, Call) and (e.fn == "tsv" or e.fn == "where" and bool(e.args) and isinstance(e.args[0], Call) and e.args[0].fn == "tsv")


def table_slot(e):
    if not (isinstance(e, Call) and e.fn in ("tsv", "csv")):
        raise NotT("table")
    return e.args[0].id


# The numbers the reader reads (readers.decimal: at most MAX_DIGITS digits, |exponent| <= MAX_EXPONENT) are R =
# {M·10^p : M an integer, |M| < 10^1000, -1999 <= p <= 1000} (P1; SPEC-EXACT 3.1). RMAX is the largest of them.
DIG, LOW, HIGH = R.MAX_DIGITS, -R.MAX_EXPONENT - R.MAX_DIGITS + 1, R.MAX_EXPONENT
RMAX = Fraction((10 ** DIG - 1) * 10 ** HIGH)


def mant(q):
    """(M, p) with q = M·10^p, M an integer of the fewest digits (p <= HIGH); None when q has no finite decimal."""
    q = Fraction(q)
    d = q.denominator
    a = (d & -d).bit_length() - 1   # d = 2^a 5^b exactly when q is a finite decimal
    b = round((d >> a).bit_length() / 2.321928094887362)
    b = next((i for i in (b - 1, b, b + 1) if i >= 0 and 5 ** i == d >> a), None)
    if b is None:
        return None
    M, p = q.numerator * 10 ** max(a, b) // d, -max(a, b)
    if p == 0 and M:   # an integer: its trailing zeros go to the exponent, up to HIGH
        z = min(len(str(abs(M))) - len(str(abs(M)).rstrip("0")), HIGH)
        M, p = M // 10 ** z, z
    return M, p


def in_r(q):
    """q is a number the reader reads."""
    mp = mant(q)
    return mp is not None and LOW <= mp[1] and abs(mp[0]) < 10 ** DIG


def scale(y, gap):
    """The finest exponent p >= LOW at which y > 0 is reached within DIG digits (gap(p): the digits used)."""
    p = max(LOW, len(str(y.numerator)) - len(str(y.denominator)) - DIG - 2)
    while gap(p) >= 10 ** DIG and p < HIGH:
        p += 1
    return p


def above(y):
    """The least readable number above y >= 0 (None past RMAX)."""
    if y >= RMAX:
        return None
    if y == 0:
        return Fraction(1, 10 ** -LOW)
    y = Fraction(y)
    p = scale(y, lambda p: floor(y / Fraction(10) ** p) + 1)
    return (floor(y / Fraction(10) ** p) + 1) * Fraction(10) ** p


def below_r(y):
    """The greatest readable number below y > 0 (0 when none is between)."""
    y = Fraction(y)
    p = scale(y, lambda p: -floor(-y / Fraction(10) ** p) - 1)
    return min(-floor(-y / Fraction(10) ** p) - 1, 10 ** DIG - 1) * Fraction(10) ** p


def nxt(x):
    """The least readable number > x (None: none); x None is below every number."""
    if x is None:
        return -RMAX
    return above(x) if x >= 0 else -below_r(-x)


def prv(x):
    """The greatest readable number < x (None: none); x None is above every number."""
    r = nxt(None if x is None else -x)
    return None if r is None else -r


def dec_forms(q):
    """(G04) The exponents x a spelling of q != 0 can carry, with its sign and fewest-digit mantissa (M, p): x None is
    the plain spelling, else a mantissa q/10^x and an exponent x (|x| <= MAX_EXPONENT)."""
    M, p = mant(abs(q))
    return ("-" if q < 0 else ""), M, p


def dec_mant(M, p, x):
    """(G04) The shortest text of M·10^(p - x) (x None: 0) and its digit count."""
    k = p - (x or 0)
    if k >= 0:
        return str(M) + "0" * k, len(str(M)) + k
    s = str(M).rjust(-k + 1, "0")
    return s[:k] + "." + s[k:], len(s)


FILLC = "abcdefghijkmnopqrstuvwxyzABCDEFGHIJKMNOPQRSTUVWXYZ_#$%&*@^~"   # (H04) one-byte made-up cells: no separator, quote, digit or l


def fills(head):
    """(H04, Opus 5.5 max2 review 04) made-up names that never run out: head's, then witness._fresh's (a, ..., zz, ...)."""
    return itertools.chain(head, W._fresh())


OTHC = "abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!#$%&'()*+,-./:;<=>?@[\\]^`{|}~ \"\tl"


def dec_or_none(w):
    """(H02) readers.decimal(w), or False for a text it does not read as a number (a refusal, R007: None)."""
    try:
        q = R.decimal(w)
    except R.Refusal:
        return None
    return False if q is None else q


def dec_len(q):
    """(G04) The bytes of q's shortest spelling the reader reads (readers.decimal), or None: the plain one, or a
    mantissa and exponent; the best exponent is one of a few (the mantissa's own digits, its dot moved within them
    toward exponent 0, or the exponent bound)."""
    if q == 0:
        return 1
    if not in_r(q):
        return None
    sg, M, p = dec_forms(q)
    n, E = len(str(M)), R.MAX_EXPONENT
    xs = {None} | {x for x in (p, p - 1, p + 1, p + n - 1, p + n, min(max(0, p + 1), p + n - 1), -E, E, min(max(-E, p + 1), p + n - 1), max(-E, p + n), min(E, p)) if -E <= x <= E}
    best = None
    for x in xs:
        t, d = dec_mant(M, p, x)
        if d <= DIG:
            ln = len(sg) + len(t) + (0 if x is None else 1 + (x < 0) + len(str(abs(x))))
            best = ln if best is None else min(best, ln)
    return best


def dec_spells(q, ell):
    """(G04) Every spelling of q of exactly ell bytes the reader reads as q: a mantissa (fraction zeros added) and,
    but for the plain one, e or E, a + on an exponent >= 0, and leading zeros in it (at most 6 exponent digits)."""
    E = R.MAX_EXPONENT
    if q == 0:
        sgs, M, p = ("", "-"), 0, 0
    else:
        sg, M, p = dec_forms(q)
        sgs = (sg,)
    out = []
    n = len(str(M))
    for x in [None] + list(range(-E, E + 1)):
        k = p - (x or 0)
        if q != 0 and (n + k if k >= 0 else max(n, 1 - k) + 1) > ell:
            continue   # its mantissa alone is longer
        t, d = ("0", 1) if q == 0 else dec_mant(M, p, x)
        for sg in sgs:
            for xs in (("",) if x is None else ("-",) if x < 0 else ("", "+", "-") if x == 0 else ("", "+")):
                for pad in ((0,) if x is None else range(0, 7 - len(str(abs(x))))):
                    base = len(sg) + len(t) + (0 if x is None else 1 + len(xs) + pad + len(str(abs(x))))
                    z = ell - base
                    if z < 0 or z == 1 and "." not in t or d + max(0, z - ("." not in t)) > DIG:
                        continue
                    mt = t + ("" if z == 0 else "0" * z if "." in t else "." + "0" * (z - 1))
                    for e in (("",) if x is None else ("e", "E")):
                        out.append(sg + mt + ("" if x is None else e + xs + "0" * pad + str(abs(x))))
    return out


@functools.lru_cache(maxsize=4096)   # a certificate's rows repeat values (item (h): thousands of rows of two)
def dec_seq(q, v):
    """The v-th readable spelling of q, or None when the reader reads fewer: its shortest decimal text, then with
    one, two, ... more zeros while MAX_DIGITS allows; then mantissa-and-exponent forms, e or E, the exponent with
    0-2 leading zeros, the mantissa with 0, 1, ... more zeros (P1: 1e-1999 has no plain spelling)."""
    t = W.dec_text(q) if in_r(q) else None
    if t is None:
        return None
    room = DIG - sum(ch.isdigit() for ch in t)
    if v <= room:
        return t if v == 0 else t + ("" if "." in t else ".") + "0" * v
    v -= max(room, -1) + 1
    M, p = mant(abs(q))
    e, pad, v = "eE"[v % 2], "0" * (v // 2 % 3), v // 6
    ds = str(M) + "0" * v
    p -= v
    L = max(0, LOW + DIG - 1 - p)   # fraction digits so that the exponent is at least -MAX_EXPONENT
    ds = ds.rjust(L + 1, "0")
    if len(ds) > DIG or p + L > HIGH:
        return None
    x = p + L
    return ("-" if q < 0 else "") + ds[:len(ds) - L] + ("." + ds[len(ds) - L:] if L else "") + e + ("-" if x < 0 else "") + pad + str(abs(x))


def inside(lo, hi, pay):
    """A readable number strictly between lo and hi (None: unbounded), or None when none is: 0 or an integer if one
    fits, else the shortest decimal step above lo, else the least readable number above lo (P1). Steps paid (P2)."""
    first = nxt(lo)
    if first is None or (hi is not None and first >= hi):
        return None
    if lo is None or hi is None and lo < 0:
        return Fraction(0) if hi is None or hi > 0 else (Fraction(floor(hi) - 1) if in_r(floor(hi) - 1) else prv(hi))
    d = 1
    while True:   # the steps fall toward lo; below first none is readable, so this ends by first's scale
        pay[0] += 1
        c = Fraction(floor(lo * d) + 1, d)
        if c < first:
            return first
        if (hi is None or c < hi) and in_r(c):
            return c
        d *= 10


def root(x, up=None):
    """sqrt(x) for a rational x >= 0: exact when it is rational (up None, else None); else a rational bound strictly
    inward of it to 10^-2100 (up 1: above, 0: below)."""
    x = Fraction(x)
    if up is None:
        n, q = isqrt(x.numerator), isqrt(x.denominator)
        return Fraction(n, q) if n * n == x.numerator and q * q == x.denominator else None
    P = 10 ** 2100
    r = Fraction(isqrt(x.numerator * P * P // x.denominator), P)
    return r + Fraction(up, P)


def bands():
    """R in bands, in increasing order (item 2, SPEC-EXACT 3.1): (step, jmin, jmax), the band's numbers being j·step for
    jmin <= j <= jmax; the numbers of magnitude [10^m, 10^(m+1)) have step 10^(m-999), those below 10^-1000 step 10^-1999."""
    if not BANDS:
        neg = [(Fraction(10) ** (m - DIG + 1), -(10 ** DIG - 1), -10 ** (DIG - 1)) for m in range(HIGH + DIG - 1, LOW + DIG - 2, -1)]
        BANDS.extend(neg + [(Fraction(10) ** LOW, -(10 ** (DIG - 1) - 1), 10 ** (DIG - 1) - 1)] + [(a, -c, -b) for a, b, c in reversed(neg)])
    return BANDS


BANDS = []

# (f) pixdim: a NIfTI-2 pixdim is a finite float64 (precision 53, exponents -1022 to 1023). A NIfTI-1 one is a float32,
# which is a float64 too, and NIfTI-2 holds every dim NIfTI-1 does, with the same answers: so NIfTI-2 inputs suffice.
FMAX = Fraction((1 << 53) - 1) * Fraction(2) ** 971
EMIN, EMAX = -1074, 971   # the floats' steps: 2^EMIN (subnormals and the first normal binade) to 2^EMAX


def fpair(A, B, L, H, pay):
    """Integers |x|, |y| < 2^53 with L <= A·x - B·y <= H (A, B > 0), or None: y's residues mod A/g (g = gcd) in its
    interval; moving y by A/g moves x's interval by exactly B/g, so a class holds one iff some t meets both bounds."""
    M, g = (1 << 53) - 1, gcd(A, B)
    per, be, ya, yb = A // g, B // g, max(-((A * M + H) // B), -M), min((A * M - L) // B, M)
    for r in range(ya, min(yb, ya + per - 1) + 1):
        pay[0] += 1
        c0, c1 = -(-(L + B * r) // A), (H + B * r) // A
        ta, tb = max(-((M + c1) // be), -((M + r) // per)), min((M - c0) // be, (M - r) // per)
        if c0 <= c1 and ta <= tb:
            return max(c0 + be * ta, -M), r + per * ta
    return None


def fwin(atoms, pay):
    """(f) Two floats u, v met only in bounds on one form u + r·v (and |u|, |v| <= FMAX): atoms pinning a pair of floats
    in that window, [] when none is, None for any other system. q(u + r·v) = A·u - B·w (r = p/q, w = ±v); floats are
    m·2^e (|m| < 2^53): for each smaller exponent e, gap d and order, fpair meets the window's multiples of 2^e; d stops
    where B·2^d passes them all, so every pair is reached (exact; SPEC-EXACT 3.6)."""
    form, lo, hi = None, None, None
    for F, st in atoms:
        p = [v for v in F if v != ONE and v[:2] == ("z", "pix")]
        if p and (len(p) != len(F) - (ONE in F) or len(p) > 2 or len(p) == 1 and (st or abs(F[p[0]]) != 1 or F.get(ONE, 0) < FMAX)):
            return None
        if len(p) == 2:
            u, v = sorted(p, key=repr)
            f, b = (u, v, Fraction(F[v]) / F[u]), (-Fraction(F.get(ONE, 0)) / F[u], st)
            if (form or f) != f:
                return None
            form, lo, hi = f, *((max(lo or b, b), hi) if F[u] > 0 else (lo, min(hi or b, b, key=lambda t: (t[0], not t[1]))))
    if form is None:
        return None
    (u, v, r), M = form, (1 << 53) - 1
    (L, ls), (H, hs) = [(r.denominator * t[0], t[1]) if t else (r.denominator * k * FMAX * (1 + abs(r)), False) for t, k in ((lo, -1), (hi, 1))]
    for e in range(EMIN, EMAX + 1):
        sc = Fraction(2) ** e
        Kl, Kh = floor(L / sc) + 1 if ls else -floor(-L / sc), -floor(-H / sc) - 1 if hs else floor(H / sc)
        Kmin = 0 if Kl <= 0 <= Kh else min(abs(Kl), abs(Kh))
        for o, A, B, L1, H1 in ((0, r.denominator, abs(r.numerator), Kl, Kh), (1, abs(r.numerator), r.denominator, -Kh, -Kl)) if Kl <= Kh else ():
            d = max(0, ((Kmin - A * M) // (B * M)).bit_length() - 1) if Kmin > A * M else 0
            d += next(i for i in itertools.count() if B * M << (d + i) >= Kmin - A * M)
            while d <= EMAX - e and (d == 0 or B << d <= max(-Kl, Kh) + A * M):
                pay[0] += 1
                if pay[0] > W.MAX_WITNESS_STEPS:
                    raise Big(f"deciding it needs more than {W.MAX_WITNESS_STEPS} counted steps (SPEC-EXACT 3.6, 8)")
                xy = fpair(A, B << d, L1, H1, pay)
                if xy:
                    a, w = (xy[0] * sc, xy[1] * sc * 2 ** d) if not o else (xy[1] * sc * 2 ** d, xy[0] * sc)
                    w *= -1 if r > 0 else 1
                    return [ge({u: 1, ONE: -a}), ge({u: -1, ONE: a}), ge({v: 1, ONE: -w}), ge({v: -1, ONE: w})]
                d += 1
    return []

class RAtom(tuple):
    """(f) An atom (F, strict) of a float range: it knows its variable and range, so a split can replace it."""

    def __new__(cls, A, z, r):
        o = tuple.__new__(cls, A)
        o.z, o.r = z, r
        return o


def frange(z, sg, ea, eb):
    """Atoms putting the float variable z in a range of the floats of sign sg: those with steps 2^ea to 2^eb (binades;
    ea = EMIN holds the subnormals and the first normal binade): z = sg·2^ea·J, J a natural from the range's least to
    its greatest float over 2^ea. Every float of the range is such a point (a superset); with ea = eb every such point
    is a float (one binade), so the leaves are exact; the ranges are halved down to them (frange_split)."""
    J, st = ("j",) + z, Fraction(2) ** ea
    lo, hi = (1 if ea == EMIN else 1 << 52), ((1 << 53) - 1) << (eb - ea)
    A = [ge({z: 1, J: -sg * st}), ge({z: -1, J: sg * st}), ge({J: 1, ONE: -lo}), ge({J: -1, ONE: hi})]
    return [RAtom(x, z, (sg, ea, eb)) for x in A]


def zkind(z):
    """(A01, A04; Argon reviews 01, 04) A rational variable's kind by the model's tag (H01: index 1): "read" a number the
    reader reads (in R: a band split), "sum" a sum of such, a multiple of R's finest step (a step split; a region's sum
    of RepetitionTimes, ("z", "rs", d, "y", ..), is one), else None (a float, a byte range's number, a mean, or no variable)."""
    if not (isinstance(z, tuple) and len(z) > 3 and z[0] == "z"):
        return None
    return ("sum" if z[3] == "y" else "read") if z[1] == "rs" else "read" if z[1] in ("cell", "j", "tr", "w") else "sum" if z[1] in ("y", "yp", "ps") else None


def frange_of(z, more):
    """The range (sg, ea, eb) frange put z in among the atoms more, or None (search.py's: by the atoms' own .r)."""
    return next((A.r for A in more if isinstance(A, RAtom) and A.z == z), None)


def two_log(q):
    """e with q = 2^e (q a Fraction > 0), or None."""
    q = Fraction(q)
    n, d = q.numerator, q.denominator
    if n > 0 and n & (n - 1) == 0 and d & (d - 1) == 0 and (n == 1 or d == 1):
        return n.bit_length() - d.bit_length()
    return None


def frange_in(z, more):
    """(D01, review 4 01) The float range (sg, ea, eb) the atoms more state for z, read from their forms alone (the
    model's reader of a range; never an atom's .r or .z, which the search may set): the first atom z - sg·2^ea·J >= 0
    whose range's other three frange atoms (by form) are there too, EMIN <= ea <= eb <= EMAX; None when none is."""
    J, M = ("j",) + z, (1 << 53) - 1
    his = [G[ONE] for G, s in more if not s and set(G) == {J, ONE} and G[J] == -1]
    for F, s in more:
        if s or set(F) != {z, J} or F[z] != 1 or not F[J]:
            continue
        sg, ea = (1 if F[J] < 0 else -1), two_log(abs(F[J]))
        for hi in his:
            k = two_log(Fraction(hi) / M) if ea is not None else None
            if k is not None and k >= 0 and EMIN <= ea <= ea + k <= EMAX \
                    and all(any(s2 == st and C.same(G, A) for G, s2 in more) for A, st in frange(z, sg, ea, ea + k)):
                return (sg, ea, ea + k)
    return None


def frange_split(z, r, v):
    """(f) The parts of the range r (None: every float) a non-float point v of its lattice splits it into (the float 0
    on its own; a range of two or more binades halved), the part holding v last (solved first). A one-binade range
    has only floats on its lattice, so it is never split (SPEC-EXACT 3.6)."""
    if r is None:
        parts = [[ge({z: 1}), ge({z: -1})], frange(z, -1, EMIN, EMAX), frange(z, 1, EMIN, EMAX)]
        return parts if v is None or v > 0 else [parts[2], parts[0], parts[1]] if v < 0 else parts[1:] + parts[:1]
    sg, ea, eb = r
    m = (ea + eb) // 2
    lo, hi = frange(z, sg, ea, m), frange(z, sg, m + 1, eb)
    up = v is not None and abs(v) >= Fraction(2) ** (m + 53)
    return [lo, hi] if up else [hi, lo]


# (item 4, shape 3; SPEC-EXACT 3.11) number(bytes(f, o, n)): the numbers readers.decimal reads from exactly n bytes, by
# layout (sign, digits before and after the point, exponent sign and digits): a finite union of lattices M·10^q. A spelling the
# reader refuses R007 is no readable input (SPEC 4.1: within the bounds of SPEC 9), as for a cell. The longest it reads:
# '-', 1000 digits, '.', 'e', a sign, 6 exponent digits (1010 bytes).
RAW_LONG = 1 + R.MAX_DIGITS + 3 + 6


def pow10(q):
    return Fraction(10) ** q


@functools.lru_cache(maxsize=2048)
def rlays(m):
    """The unsigned layouts of m bytes as lattices (m0, m1, qa, qb): values M·10^q, M in [m0, m1], q in [qa, qb] (q = E - lb).
    A layout: la digits before the point (no leading zero unless la = 1), lb after it (with a point), an exponent of lx
    digits (0 to 6, leading zeros allowed, value <= R.MAX_EXPONENT) after 'e' and xs sign bytes (0 or 1)."""
    out = set()
    for lx in range(0, 7):
        for xs in ((0, 1) if lx else (0,)):
            rest = m - (1 + xs + lx if lx else 0)
            for lb in range(0, rest):
                la = rest - (1 + lb if lb else 0)
                if la < 1 or la + lb > R.MAX_DIGITS:
                    continue
                hi = min(10 ** lx - 1, R.MAX_EXPONENT) if lx else 0
                ea = -hi if xs else 0
                m0, m1 = (0, 10 ** (1 + lb) - 1) if la == 1 else (10 ** (la - 1 + lb), 10 ** (la + lb) - 1)
                out.add((m0, m1, ea - lb, hi - lb))
    return tuple(sorted(out))


def lg10(v):   # an integer near log10(v), v > 0
    return len(str(v.numerator)) - len(str(v.denominator))


def lnext(L, v):
    """The least value of the lattice L above v, or None."""
    m0, m1, qa, qb = L
    if v < 0:
        return Fraction(0) if m0 == 0 else m0 * pow10(qa)
    q = max(qa, lg10(v) - len(str(m1)) - 2)
    while m1 * pow10(q) <= v:
        q += 1
    while q > qa and m1 * pow10(q - 1) > v:
        q -= 1
    if q > qb:
        return None
    g = pow10(q)
    return m0 * g if m0 * g > v else (floor(v / g) + 1) * g


def lprev(L, v):
    """The greatest value of the lattice L below v, or None."""
    m0, m1, qa, qb = L
    if v <= 0:
        return None
    if m0 * pow10(qa) >= v:
        return None
    q = max(qa, lg10(v) - len(str(m1)) - 2)   # qin: the least q (>= qa) with m1·10^q >= v
    while m1 * pow10(q) < v:
        q += 1
    while q > qa and m1 * pow10(q - 1) >= v:
        q -= 1
    best = m1 * pow10(q - 1) if q - 1 >= qa and q - 1 <= qb else None   # every value at q - 1 is below v
    if q > qb:
        return m1 * pow10(qb)
    g = pow10(q)
    if m0 * g < v:
        c = (-floor(-v / g) - 1) * g
        best = c if best is None or c > best else best
    return best


def ext_(xs, f):
    xs = [x for x in xs if x is not None]
    return f(xs) if xs else None


@functools.lru_cache(maxsize=4096)
def rnext(n, v):
    """The least number spelled in exactly n bytes above v (None: none); v None is below every number."""
    if n > RAW_LONG:
        return None
    if v is None:
        v = -pow10(2 * R.MAX_EXPONENT + 2 * R.MAX_DIGITS)
    a = ext_([lnext(L, v) for L in rlays(n)], min)
    b = ext_([lprev(L, -v) for L in rlays(n - 1)], max) if n >= 2 else None   # '-' and an unsigned spelling of n - 1 bytes
    return ext_([a, None if b is None else -b], min)


@functools.lru_cache(maxsize=4096)
def rprev(n, v):
    """The greatest number spelled in exactly n bytes below v (None: none); v None is above every number."""
    if n > RAW_LONG:
        return None
    if v is None:
        v = pow10(2 * R.MAX_EXPONENT + 2 * R.MAX_DIGITS)
    a = ext_([lprev(L, v) for L in rlays(n)], max)
    b = ext_([lnext(L, -v) for L in rlays(n - 1)], min) if n >= 2 else None
    return ext_([a, None if b is None else -b], max)


def rin(n, v):
    """v is a number spelled in exactly n bytes."""
    return rnext(n, rprev(n, v)) == v


class RawFile(W.Periodic):
    """(shape 3) a certificate's raw file: the periodic bytes with the spellings of its number()-read ranges written over them."""

    def __init__(self, n, seed, ov):
        super().__init__(n, seed)
        self.ov = ov
        self.args = (n, seed, ov)   # (BLD, plain) rebuilt from these, the same file
        if self.whole is not None:
            b = bytearray(self.whole)
            for o, t in ov:
                b[o:o + len(t)] = t
            self.whole = bytes(b)
        self.sha = hashlib.sha256(self.whole if self.whole is not None else b"raw %d %d %r" % (n, seed, ov)).hexdigest()

    def __getitem__(self, sl):
        if self.whole is not None:
            return self.whole[sl]
        a, b, _ = sl.indices(self.n)
        out = bytearray(super().__getitem__(slice(a, b)))
        for o, t in self.ov:
            for i in range(max(a, o), min(b, o + len(t))):
                out[i - a] = t[i - o]
        return bytes(out)


class PAtom(tuple):
    """(e) S = mu·N for a mean inside a difference, mu a rational variable: as an atom it says only N >= 1; Model.solve
    adds the range of N it is solved in (prange) and checks S = mu·N on each solution (SPEC-EXACT 3.5). (e2) A piece of
    a summed and ordered column: S its rows' sum, N >= 0 its rows, mu their value (w_j) or their mean; key: its range's."""

    def __new__(cls, mu, S, N, lo=None, hi=None, ty=None, a0=1, key=None):
        o = tuple.__new__(cls, ge(lin((1, N), (1, const(-a0)))))
        o.mu, o.S, o.N, o.lo, o.hi, o.ty, o.ends = mu, S, N, lo, hi, ty or {}, []   # lo, hi: bounds of mu (its rows' classes), or None
        o.a0, o.key, o.k = a0, key or mu, None   # k: a mean's column (nest compares means of one column only)
        return o


def cends(cs):
    """The least lower and greatest upper end of these classes (None: unbounded), each with whether every class is
    open at it (an interval class is open at its ends, a point is its own end)."""
    out = []
    for j, pick in ((0, min), (1, max)):
        es = [(c[1][j], True) if c[0] == "iv" else (c[2], False) for c in cs]
        if not es or any(v is None for v, _ in es):
            out.append((None, True))
        else:
            L = pick(v for v, _ in es)
            out.append((L, all(o or v != L for v, o in es)))
    return out


def nest(P, Q):
    """(e) Cases for a mean Q over the rows of a mean P and of types R more (no named rows): Q lies between P and R's
    mean, which lies in [l, h], R's classes' ends; so P >= h: l <= Q <= P; P <= l: P <= Q <= h; else l <= Q <= h
    (closed ends: a relaxation that holds on every input, whatever rows R has). None when Q is not such a mean."""
    if P.mu == Q.mu or P.k != Q.k or ONE in P.N or ONE in Q.N or not set(P.N) < set(Q.N) or any(Q.N[v] != c for v, c in P.N.items()):
        return None
    (l, _), (h, _) = cends([Q.ty[v] for v in Q.N if v not in P.N])
    p, q = {P.mu: 1}, {Q.mu: 1}
    at = lambda a, b: ge(lin((1, a), (-1, b)))   # noqa: E731 (a >= b; a constant as const())
    if l is None and h is None:
        return None
    L, H = const(l or 0), const(h or 0)
    out = [] if h is None else [[at(p, H), at(p, q)] + ([at(q, L)] if l is not None else [])]
    out += [] if l is None else [[at(L, p), at(q, p)] + ([at(H, q)] if h is not None else [])]
    return out + [([at(p, L), at(q, L)] if l is not None else []) + ([at(H, p), at(H, q)] if h is not None else [])]


def caps(Ms):
    """(pm) For two means of one column whose rows share types without either holding the other's: the mean P of the
    shared types, a free rational (their mean; any value when they have no rows), with nest's cases for each of the
    two (true on every input: a relaxation), so the two are compared through it."""
    out = {}
    for Q1 in Ms:
        for Q2 in Ms:
            I = {v: c for v, c in Q1.N.items() if Q2.N.get(v) == c}
            if Q1.k != Q2.k or repr(Q1.mu) >= repr(Q2.mu) or ONE in Q1.N or ONE in Q2.N or not I or len(I) in (len(Q1.N), len(Q2.N)):
                continue
            P = PAtom(("z", "mu", "cap", Q1.k, fz(I)), {}, I)
            P.k = Q1.k
            g = [(("nest", P.mu, Q.mu), nest(P, Q)) for Q in (Q1, Q2)]
            out[P.mu] = [(k, b) for k, b in g if b]
    return [(v, g) for v, g in out.items() if g]


def fz(F):
    """A form as a key."""
    return tuple(sorted(F.items(), key=lambda vc: repr(vc[0])))


def prange(P, a, b, sg):
    """Atoms putting P's N in [a, b] (b None: unbounded) with mu of sign sg, and the hull of {(mu·N, mu)} there:
    a·mu <= S <= b·mu for mu >= 0, mirrored for mu <= 0, and with mu's bounds l <= mu <= h McCormick's
    (mu - l)(N - a) >= 0, (h - mu)(N - a) >= 0, and with b (mu - l)(b - N) >= 0, (h - mu)(b - N) >= 0, S for mu·N;
    at a = b (sg 0) S = a·mu exactly; sg None (e2: mu between two finite bounds of either sign): McCormick's only.
    Each atom knows P and the range."""
    m, S, N = {P.mu: 1}, P.S, P.N
    A = [ge(lin((1, N), (1, const(-a))))] + ([ge(lin((-1, N), (1, const(b))))] if b is not None else [])
    if sg == 0:
        A += [ge(lin((1, S), (-a, m))), ge(lin((-1, S), (a, m)))]
    else:
        A += [] if sg is None else [ge(lin((sg, m))), ge(lin((sg, S), (-sg * a, m)))] + ([ge(lin((sg * b, m), (-sg, S)))] if b is not None else [])
        for e, d in [(a, 1)] + ([(b, -1)] if b is not None else []):   # (q·mu - q·w)(d·N - d·e) >= 0, q = 1 at l, -1 at h
            for q, w in ((1, P.lo), (-1, P.hi)):
                if w is not None:   # q·d·(S - w·N - e·mu + e·w) >= 0
                    A.append(ge(lin((q * d, S), (-q * d * w, N), (-q * d * e, m), (q * d * e * w, const(1)))))
    return [RAtom(x, P.key, (a, b, sg)) for x in A]


class NiiFile(W.Periodic):
    """(3.10) a certificate's NIfTI file of n bytes: its header, then the periodic bytes (held as its rule, as W.Periodic)."""

    def __init__(self, head, n, seed):
        super().__init__(n, seed)
        self.head = head
        self.args = (head, n, seed)   # (BLD, plain) rebuilt from these, the same file
        if self.whole is not None:
            self.whole = head + self.whole[len(head):]
        self.sha = hashlib.sha256(self.whole if self.whole is not None else b"nifti %s %d %d" % (hashlib.sha256(head).hexdigest().encode(), n, seed)).hexdigest()

    def __getitem__(self, s):
        a, b, _ = s.indices(self.n)
        return self.head[a:b] + super().__getitem__(slice(max(a, len(self.head)), max(b, len(self.head)))) if self.whole is None else self.whole[s]


class NCase(int):
    """A NIfTI slot's case when pixdim() reads it: dim[0], and the time unit code (8, 16, 24; 0 for any other: I005);
    (3.10) when size() reads it: how the header is held (z: n2, n1, gz)."""

    def __new__(cls, d0, unit=None, z=None):
        o = int.__new__(cls, d0)
        o.unit, o.z = unit, z
        return o

    def __eq__(self, o):
        return int(self) == int(o) and (getattr(o, "unit", None), getattr(o, "z", None)) == (self.unit, self.z)

    def __hash__(self):
        return hash((int(self), self.unit, self.z))


def band(p):
    """The band of R (bands()) holding the readable number p."""
    if abs(p) < Fraction(10) ** (LOW + DIG - 1):
        return Fraction(10) ** LOW, -(10 ** (DIG - 1) - 1), 10 ** (DIG - 1) - 1
    M, e = mant(abs(p))
    g = Fraction(10) ** (len(str(M)) + e - DIG)
    return (g, 10 ** (DIG - 1), 10 ** DIG - 1) if p > 0 else (g, -(10 ** DIG - 1), -10 ** (DIG - 1))


class Extra:
    """The aggregates' part of a case (SPEC-EXACT 3.5): the summed types that may have rows and which of
    them have, and for each order statistic its region and rank among the others in that region."""

    def __init__(self, sums, pres, ordv, nw, sel, npc=None):
        self.sums, self.pres, self.ordv, self.nw, self.sel, self.npc = sums, pres, ordv, nw, sel, npc or {}


class JCase:
    """A JSON slot's case (SPEC-EXACT 3.6): the kind of each node of the named paths ('obj', 'arr', 'num',
    'str', 'word' for true/false/null), whether each named member is there, each array's length."""

    def __init__(self, kind, there, length):
        self.kind, self.there, self.length = kind, there, length


class Slot:
    """One slot's case (SPEC-EXACT 3.4): how many of the named positions exist (h), the type of
    each named row (the present positions, then the key rows elsewhere), what each key does
    ('none', 'many', or the index of its row), and the class of each header cell read."""

    def __init__(self, pos, kp, h, types, keys, hdr):
        self.pos, self.kp, self.h, self.types, self.keys, self.hdr = pos, kp, h, types, keys, hdr


class Model:
    """SPEC-EXACT 3 for one statement as judged: slots (file names, in the order of their hashes),
    the literals and cutoffs of each column the statement reads, the classes a cell can take, the
    row types, and the cases of the rows it names."""

    def __init__(self, expr, names, kinds):
        self.k0, self.rb = kinds, RB[0]   # rb (F02): each table's and the statement's text within the read limit (SPEC-EXACT 1)
        self.lmemo = {}   # (G04) each row type's least line (Model.lline)
        self.big_ok = False   # (G02b) a point past MAX_ROWS answered as it is (Decide.limit_shown confirms it), not Past
        self.kind, lits, cuts, self.num, self.cells, self.hcols, agg, self.pix, self.dimr, self.memo = {}, {}, {}, set(), set(), set(), {}, set(), set(), {}
        self.leaf_at = self.tree = self.checked = self.trees = None   # (cert.py) the option's tree, the node a leaf closes, the last checked system; a replayed find's trees
        self.cert = False   # (C4) True only while a refusal's "none" finds are replayed with certificates (Decide.certify)
        self.mcut = {}   # (e) a mean's (S, N) forms: the classes of its rows' values
        self.rs, self.rsagg, self.rsets = {}, [], []   # (R1) per dataset slot of kind "rs" or "pt" (R2): its tasks; the aggregates over recordings() sets; the sets
        self.recs, self.rval = {}, []   # (2c) per dataset slot, the entities of the recordings named; the tr/volumes/onset calls
        self.rnum = set()   # (shape 3) the byte ranges (file, offset, length) number() reads
        tops = expr if isinstance(expr, list) else [expr]   # a list: a statement and its copy with one slot renamed (R3)
        vtop = {id(vchain(e.args[0] if e.fn in CMP and e.args else e)) for e in tops if isinstance(e, Call)}   # item 5a
        vtop |= {id(x) for e in tops if isinstance(e, Call) for d in [dchain(e.args[0] if e.fn in CMP and e.args else e)] if d for x in d.args}   # 5b
        nt = [t for e in tops if isinstance(e, Call) for t in [nchain(e.args[0] if e.fn in CMP and e.args else e)] if t]   # the variance shape
        if nt and (len(names) > 1 or any(v.fn.endswith("sd") or not (v.args and isinstance(v.args[0], Call) and v.args[0].fn in ("tsv", "csv")) for t, _ in nt for _, v in t)):
            raise NotT("a variance inside a larger value")   # 3.7: variances of one table, no selection (an SD there: S006 by sort)
        vtop |= {id(v) for t, _ in nt for _, v in t}
        calls = [x for e in tops for x in W.walk(e) if isinstance(x, Call)]
        fr = lambda f: {x.args[0].id for x in calls if x.fn == f and x.args and isinstance(x.args[0], Name)}
        self.tc, self.nr = fr("csv") & fr("tsv"), fr("nifti") & fr("size")   # (3.10) a file read by csv() and tsv(), by nifti() and size()
        self.st = fr("size") & (fr("tsv") | fr("csv"))   # (shape 2, 3.12) a table's size: the slot is the table's; (3.13h) also of a file read by both
        rt = {id(x.args[0]) for x in calls if x.fn == "rows" and len(x.args) == 1}
        nc = {id(x.args[0].args[0]) for x in calls if x.fn == "number" and len(x.args) == 1 and isinstance(x.args[0], Call) and x.args[0].fn == "cell"
              and len(x.args[0].args) == 3 and not x.args[0].params and isinstance(x.args[0].args[1], Int) and isinstance(x.args[0].args[2], Int) and x.args[0].args[2].v == 1}
        nc |= {id(x.args[0].args[0]) for x in calls if x.fn == "number" and len(x.args) == 1 and not x.params and isinstance(x.args[0], Call) and x.args[0].fn == "header" and len(x.args[0].args) == 2
               and isinstance(x.args[0].args[1], Int) and x.args[0].args[1].v == 1 and isinstance(x.args[0].args[0], Call) and x.args[0].args[0].fn == "tsv"}   # (3.13d) number(header(tsv(f), 1))
        nc |= {id(x.args[0].args[0]) for x in calls if x.fn == "number" and len(x.args) == 1 and not x.params and isinstance(x.args[0], Call) and x.args[0].fn == "cell" and len(x.args[0].args) == 3
               and not x.args[0].params and isinstance(x.args[0].args[1], Call) and x.args[0].args[1].fn == "key" and x.args[0].args[2] == Int(1) and isinstance(x.args[0].args[0], Call)
               and x.args[0].args[0].fn == "tsv" and all(a == Int(1) for a in x.args[0].args[1].args[0::2])}   # (3.13e) number(cell(tsv(f), key(1, b), 1))
        fs = lambda f: [x for x in calls if x.fn in ("tsv", "csv") and x.args and getattr(x.args[0], "id", None) == f]   # noqa: E731
        self.tc1 = {f for f in self.tc if len(names) == 1 and not any(x.fn == "widen" for x in calls) and all(id(x) in rt | nc for x in fs(f))}
        rw = {id(y.args[0]) for y in calls if y.fn in ("rows", "count") and len(y.args) == 1 and not y.params}
        aw = {id(y.args[0]) for y in calls if (y.fn in AGG or y.fn in VARF) and len(y.args) == (3 if y.fn == "order" else 2) and not y.params and isinstance(y.args[1], Int) and y.args[1].v == 1}   # (3.13c, 3.13g) an aggregate or a variance of column 1
        rw |= aw
        tw = {id(y.args[0]): y for y in calls if y.fn == "where" and id(y) in rw and y.args and isinstance(y.args[0], Call) and y.args[0].fn == "tsv"
              and len(y.args) >= 2 and not y.params and all(isinstance(c, Call) and c.fn in ("eq", "ne") and norm(c)[1] == 1 for c in y.args[1:])}
        self.tw = {x.args[0].id for x in calls if x.fn == "tsv" and x.args and getattr(x.args[0], "id", None) in self.tc - self.tc1 and id(x) in set(tw) | nc | aw}
        self.tn = {x.args[0].id for x in calls if x.fn == "tsv" and x.args and getattr(x.args[0], "id", None) in self.tw and (id(x) in nc | aw or id(x) in tw and id(tw[id(x)]) in aw)}   # (3.13b, 3.13c) a tsv() line read as a number
        if any(x.fn == "tsv" and x.args and getattr(x.args[0], "id", None) in self.tc - self.tc1 and id(x) not in rt | set(tw) | (nc | aw if x.args[0].id in self.tw else set()) for x in calls):
            raise NotT("slot")   # a file read by tsv() and csv(): rows() of its tsv(), or (tc1) only rows() and number() of column 1 (SPEC-EXACT 3.10)
        for x in calls:
            if x.fn not in FNS:
                raise NotT(x.fn)
            if x.fn in READS:
                k = "csv" if x.fn == "tsv" and x.args[0].id in self.tc else "nifti" if x.fn == "size" and x.args[0].id in self.nr else READS[x.fn]
                k = ("csv" if x.args[0].id in fr("csv") else "tsv") if x.fn == "size" and x.args and getattr(x.args[0], "id", None) in self.st else k   # (3.10) rows(tsv(f)): the csv slot's rows; size(n): the NIfTI slot's size
                if not x.args or not isinstance(x.args[0], Name) or kinds.get(x.args[0].id) != "file" or self.kind.get(x.args[0].id, k) != k:
                    raise NotT("slot")   # part H: a file read by two kinds of reader is not modelled (but tsv() and csv(): 3.10)
                self.kind[x.args[0].id] = k
                if len(x.args) != (3 if x.fn == "bytes" else 1) or (x.fn == "bytes" and not (isinstance(x.args[1], Int) and isinstance(x.args[2], Int) and x.args[1].v >= 0 and 1 <= x.args[2].v)):
                    raise NotT(x.fn)
            elif x.fn == "extra":   # item 4: extra(participant(bids(d), L), k): the cell (d, k) of the row labelled sub-L
                if len(x.args) != 2 or x.params or not (isinstance(x.args[0], Call) and x.args[0].fn == "participant") or not isinstance(x.args[1], Int) or x.args[1].v < 2:
                    raise NotT("extra")   # k = 1 (participant_id): S006, on the real bytes too
                self.cells.add((plab(x.args[0])[0], x.args[1].v))
            elif x.fn == "participant":   # item 4: participant(bids(d), L) names the row of participants() whose label is sub-L
                d, L = plab(x)
                if self.kind.setdefault(d, "pt") not in ("pt", "rs", "rec"):
                    raise NotT("participant")
                self.kind[d] = "pt"
                lits.setdefault((d, 1), set()).add(b"sub-" + L)
            elif x.fn in ("bids", "participants", "recording"):   # item 2b: participants(bids(d)) is the table slot d, kind "pt";
                b = x.args[0] if x.fn != "bids" and x.args else x   # (2c) recording(bids(d), ...) makes d a dataset slot of kind "rec"
                if x.params or not isinstance(b, Call) or b.fn != "bids" or b.params or len(b.args) != 1 or not isinstance(b.args[0], Name) or kinds.get(b.args[0].id) != "dataset" or x.fn == "participants" and len(x.args) != 1:
                    raise NotT(x.fn)
                k = {"participants": "pt", "recording": "rec"}.get(x.fn)
                if k == "pt" and self.kind.get(b.args[0].id) in ("rs", "rec"):   # (R2) recordings() of a dataset whose participants it reads;
                    self.kind[b.args[0].id] = "pt"   # (3.8b) a named recording of it
                k = "pt" if k == "rec" and self.kind.get(b.args[0].id) == "pt" else k
                if k and self.kind.setdefault(b.args[0].id, k) != k:
                    raise NotT("recordings() and a named recording of one dataset")
                if x.fn == "recording":
                    if any(not isinstance(a, Str) and not (isinstance(a, Call) and a.fn in ("acq", "rec") and len(a.args) == 1 and isinstance(a.args[0], Str)) for a in x.args[1:]):
                        raise NotT("recording")
                    self.recs.setdefault(b.args[0].id, set()).add(rent(x))
            elif x.fn == "recordings":   # (R1) recordings(bids(d), task): d a dataset slot of kind "rs"
                b = x.args[0] if x.args else None
                if x.params or len(x.args) not in (2, 3) or not (isinstance(b, Call) and b.fn == "bids" and not b.params and len(b.args) == 1 and isinstance(b.args[0], Name) and kinds.get(b.args[0].id) == "dataset") or not isinstance(x.args[1], Str) or x.args[2:] and rsel(x.args[2]) != b.args[0].id:
                    raise NotT("recordings")
                t = x.args[1].v.decode("ascii", "replace")
                if not is_key(t):
                    raise NotT("recordings")
                if self.kind.setdefault(b.args[0].id, "rs") not in ("rs", "pt"):
                    raise NotT("recordings() and a named recording of one dataset")
                self.rs.setdefault(b.args[0].id, set()).add(t)
                self.rsets.append(x)
            elif x.fn in AGG and x.args and isinstance(x.args[0], Call) and x.args[0].fn == "recordings":   # (R1) sum/mean/min/max(rs, q[, type])
                q = x.args[1].v.decode("ascii", "replace") if len(x.args) >= 2 and isinstance(x.args[1], Str) else None
                if x.fn not in ("sum", "mean", "min", "max") or x.params or q not in RSQ or len(x.args) != (3 if q == "trials" else 2) or (q == "trials" and not (isinstance(x.args[2], Str) and rs_lit(x.args[2].v))):
                    raise NotT(x.fn)
                self.rsagg.append(x)
            elif x.fn in RECF:   # (2c, item 3) a named recording's values, anywhere in the statement
                if not (x.args and isinstance(x.args[0], Call) and x.args[0].fn == "recording") or len(x.args) != (2 if x.fn in ("onset", "duration", "trials") else 1) or x.params or (
                        x.fn in ("onset", "duration") and not (isinstance(x.args[1], Int) and x.args[1].v >= 1)) or (x.fn == "trials" and not (isinstance(x.args[1], Str) and rs_lit(x.args[1].v))):
                    raise NotT(x.fn)
                self.rval.append(x)
            elif x.fn == "dim":
                if len(x.args) != 2 or not (isinstance(x.args[0], Call) and x.args[0].fn == "nifti") or not isinstance(x.args[1], Int) or x.args[1].v < 1:
                    raise NotT("dim")
                self.dimr.add(x.args[0].args[0].id)
            elif x.fn == "pixdim":   # (f): along time only (else S006 on the real bytes)
                if len(x.args) != 2 or x.params or not (isinstance(x.args[0], Call) and x.args[0].fn == "nifti") or x.args[1] != Int(4):
                    raise NotT("pixdim")
                self.pix.add(x.args[0].args[0].id)
            elif x.fn in ("member", "item"):
                jpath(x)
            elif x.fn == "where":
                for c in self.wconds(x):
                    (lits if c[0] in ("eq", "ne") else cuts).setdefault((tslot(x), c[1]), set()).add(c[2])
            elif x.fn == "cell":
                if len(x.args) != 3 or not isinstance(x.args[2], Int) or (not isinstance(x.args[1], Int) and not (isinstance(x.args[1], Call) and x.args[1].fn == "key")):
                    raise NotT("cell")
                s = table_slot(x.args[0])
                self.cells.add((s, x.args[2].v))
                for k, b in (self.tkey(x) if isinstance(x.args[1], Call) else ()):
                    lits.setdefault((s, k), set()).add(b)
            elif x.fn == "header":
                if len(x.args) != 2 or not isinstance(x.args[1], Int):
                    raise NotT("header")
                self.hcols.add((table_slot(x.args[0]), x.args[1].v))
            elif x.fn == "number":
                a = x.args[0] if len(x.args) == 1 and not x.params else None
                if isinstance(a, Call) and a.fn == "extra" and len(a.args) == 2 and isinstance(a.args[0], Call) and a.args[0].fn == "participant" and isinstance(a.args[1], Int):
                    self.num.add(("cell", plab(a.args[0])[0], a.args[1].v))   # item 4: number(extra(...)) reads the cell as number()
                    continue
                if isinstance(a, Call) and a.fn == "bytes" and len(a.args) == 3 and isinstance(a.args[0], Name) and isinstance(a.args[1], Int) and isinstance(a.args[2], Int):
                    self.rnum.add((a.args[0].id, a.args[1].v, a.args[2].v))   # (shape 3, 3.11) number() of a file's byte range
                    continue
                if not (isinstance(a, Call) and a.fn in ("cell", "header") and len(a.args) == (3 if a.fn == "cell" else 2) and isinstance(a.args[-1], Int)):
                    raise NotT("number")
                self.num.add((a.fn, table_slot(a.args[0]), a.args[-1].v))
            elif x.fn in AGG:
                if len(x.args) != (3 if x.fn == "order" else 2) or x.params or not all(isinstance(a, Int) and a.v >= 1 for a in x.args[1:]):
                    raise NotT(x.fn)
                agg.setdefault((tslot(x), x.args[1].v), set()).add("sum" if x.fn in ("sum", "mean") else "ord")
            elif x.fn == "widen" and (len(x.args) != 1 or cutoff(x, "tolerance") <= 0):
                raise NotT("widen")
            elif x.fn in VARF:   # the variance fragment (SPEC-EXACT 3.7): the statement, or a comparison of it
                if len(x.args) != 2 or x.params or not isinstance(x.args[1], Int) or id(x) not in vtop:
                    raise NotT("a variance inside a larger value")
                agg.setdefault((tslot(x), x.args[1].v), set()).add("var")
        self.rreg = {}   # (shape 3) per raw slot its number()-read ranges (o, n), sorted; two that overlap and differ: not modelled
        for f, o, n in sorted(self.rnum):
            if any(o < o2 + n2 and o2 < o + n for o2, n2 in self.rreg.get(f, [])):
                raise NotT("number() of two overlapping byte ranges of one file")
            self.rreg.setdefault(f, []).append((o, n))
        self.rread = {}   # (item 3) per (slot, recording) the values read
        for y in self.rval:
            self.rread.setdefault((y.args[0].args[0].args[0].id, rent(y.args[0])), set()).add(y.fn)
        if any({"onset", "tr", "volumes"} <= v for v in self.rread.values()):
            raise NotT("onset with tr and volumes of one recording")   # onset < volumes x tr: bilinear (3.8)
        self.rdep = {}   # (3.8a) per named recording its sidecar's folder (2 func, 1 subject, 0 root): above each whose labels hold its own
        for d, es in self.recs.items():
            for E in sorted(es, key=len, reverse=True):
                self.rdep[(d, E)] = min([2] + [self.rdep[(d, F)] - 1 for F in es if F != E and set(E) <= set(F)])
        if any(v < 0 for v in self.rdep.values()):
            raise NotT("four recordings nested by labels")   # one of them adds the run alone to another: never both there (B30, S0265)
        for (s, E) in self.rread:
            ls = {y.args[1].v for y in self.rval if y.fn == "trials" and (y.args[0].args[0].args[0].id, rent(y.args[0])) == (s, E)}
            if len({skeleton(b.decode("utf-8")) for b in ls}) < len(ls):
                raise NotT("look-alike trial types")   # a row holding one makes the other's trials() refuse K002
        self.rsq, self.rsm = {}, {}   # (R1) per rs slot its one quantity (q, trial type); mean, min and max only as the statement's one recordings() set
        for x in self.rsagg:   # (3.9a, 3.9b) or its quantities (rsm): volumes, events, trials of types
            self.rsm.setdefault(x.args[0].args[0].args[0].id, set()).add((x.args[1].v.decode(), x.args[2].v if len(x.args) == 3 else None))
        for d, Q in sorted(self.rsm.items()):
            if len(Q) == 1:
                self.rsq[d] = Q.pop()
                continue
            ls = [lit for q, lit in Q if q == "trials"]
            if len({skeleton(b.decode("utf-8")) for b in ls}) < len(ls):
                raise NotT("look-alike trial types of recordings")   # a row of one makes the other's trials() refuse K002
            if any(q == "tr" for q, _ in Q):
                raise NotT("tr beside another quantity of recordings")   # the tr reader reads the image's header too (B09)
            if any(x.fn != "sum" for x in self.rsagg if x.args[0].args[0].args[0].id == d):
                raise NotT("a mean, min or max of two quantities of recordings")
            self.rsm[d] = tuple(sorted(Q, key=repr))
        self.rsm = {d: Q for d, Q in self.rsm.items() if d not in self.rsq}
        self.rs7 = {}   # (3.9e) per (dataset, task) whose recordings have a sum beside a max or a min: that one
        if any(x.fn != "sum" for x in self.rsagg) and any(sum(isinstance(y, Call) and y.fn == "recordings" for y in W.walk(e)) > 1 for e in tops):
            if any(x.fn == "mean" for x in self.rsagg):
                raise NotT("a mean of recordings and another recordings() set")
            fs, cnt = {}, {(x.args[0].args[0].args[0].id, x.args[0].args[1].v.decode("ascii", "replace")) for e in tops for x in W.walk(e)
                           if isinstance(x, Call) and x.fn == "count" and x.args and isinstance(x.args[0], Call) and x.args[0].fn == "recordings"}
            for x in self.rsagg:
                fs.setdefault((x.args[0].args[0].args[0].id, x.args[0].args[1].v.decode("ascii", "replace")), set()).add(x.fn)
            for (d, t), F in sorted(fs.items()):
                if {"min", "max"} <= F:
                    raise NotT("a min and a max of one task's recordings beside another recordings() set")
                if "sum" in F and len(F) > 1:   # y <= N m (max) or y >= N m (min): linear only with N read nowhere else (3.9e)
                    q = self.rsq.get(d, ("tr",))[0]
                    if (d, t) in cnt or q == "tr" or (q == "volumes" and "min" in F) or d in self.rsm:
                        raise NotT("a sum beside a count, or of tr, or a min of volumes, beside a min or max of one task's recordings")
                    self.rs7[(d, t)] = (F - {"sum"}).pop()
        if any(len(v) > 1 and v != {"sum", "ord"} for v in agg.values()):
            raise NotT("a variance and another aggregate of one column in one statement")
        self.agg = {sk: "both" if len(v) > 1 else v.pop() for sk, v in agg.items()}   # (e2) both: summed and ordered
        if any(n not in self.kind for n in names):
            raise NotT("slot")
        self.names = [n for n in names if n in self.kind]
        self.tabs = [n for n in self.names if self.kind[n] in ("tsv", "csv", "pt")]
        self.jkeys = {}
        for x in (x for e in tops for x in W.walk(e)):   # two look-alike keys named under one JSON object: a document holding both refuses K003
            if isinstance(x, Call) and x.fn == "member":
                s, p = jpath(x)
                self.jkeys.setdefault((s, p[:-1]), set()).add(p[-1][1])
        for ks in self.jkeys.values():
            if len({skeleton(k.decode("utf-8")) for k in ks}) < len(ks):
                raise NotT("look-alike keys")
        for f in sorted(self.tw):   # (shape 1, 3.13) a tsv() line's pieces: literals of the csv columns the statement reads
            rk = {k for (s2, k) in set(lits) | set(cuts) | self.cells | set(agg) if s2 == f and k >= 1}
            for b in lits.get((f, 0), ()):
                for k, q in enumerate(b.split(b","), 1):
                    if k in rk:
                        lits.setdefault((f, k), set()).add(q)
        self.lits = {sk: sorted(v) for sk, v in lits.items()}   # sorted, so the types do not depend on the text's order
        for d in self.recs:
            if d in self.rs:
                raise NotT("recordings() and a named recording of one dataset")   # the named one is one of the set's
            ls = {skeleton(b.decode("utf-8", "replace")): b for b in self.lits.get((d, 1), ())} if self.kind[d] == "pt" else {}
            for E in self.recs[d]:   # (3.8b) its subject's row: sub-L, a literal or not; a look-alike literal: K003 with both, else no row
                L = "sub-" + dict(E)["sub"]
                if ls.get(skeleton(L), L.encode()) != L.encode():
                    raise NotT("look-alike participant and recording labels")
        for es in self.recs.values():   # (2c) two named labels that look alike: a dataset holding both refuses K003
            for k in ("sub", "task", "acq", "rec"):
                ls = {dict(E)[k] for E in es if k in dict(E)}
                if len({skeleton(v) for v in ls}) < len(ls):
                    raise NotT("look-alike labels")
        if any(sk[0] not in self.kind for sk in self.agg):
            raise NotT("slot")
        if self.nr & self.pix:
            raise NotT("slot")   # (3.10) pixdim() and size() of one file: not modelled
        cols = {sk for sk in self.lits if sk[1] != 0 or sk[0] not in self.tw} | set(cuts) | self.cells | set(self.agg)
        for s in {s for s, k in cols if k == 1 and self.kind.get(s) == "pt"}:   # item 4: participant_id, column 1: sub-<label>, distinct
            if (s, 1) in cuts or (s, 1) in self.agg or ("cell", s, 1) in self.num or (s, 1) in self.cells:
                raise NotT("participant_id")   # read as a number, or as a cell (S006 in extra(); a key() needs a table slot)
            ls = [b.decode("utf-8", "replace") for b in self.lits.get((s, 1), ())]
            if len({skeleton(t) for t in ls}) < len(ls):
                raise NotT("look-alike participant labels")   # sub-L and a look-alike label: K003 with both rows, V004 with one
            if s in self.rs and "trials" in self.rsqs(s):
                raise NotT("trials of recordings and participant_id")   # the certificate's labels no longer follow the regions' order
        self.cols = {s: sorted(k for (s2, k) in cols if s2 == s) for s in self.tabs}
        self.width = {s: max(self.cols[s] + [k for (s2, k) in self.hcols if s2 == s] + [1]) for s in self.tabs}
        self.steps, self.spell, self.classes, self.regs, self.only, self.pay, self.parts, self.cb = 0, {}, {}, {}, {}, [0], {}, {}
        for s in self.tabs:
            for k in self.cols[s]:
                self.classes[(s, k)] = self.column(s, k, self.lits.get((s, k), []), sorted(cuts.get((s, k), ())))
        self.types = {s: list(itertools.product(*[range(len(self.classes[(s, k)])) for k in self.cols[s]])) for s in self.tabs}
        self.wcs, self.tok, self.wo = {}, {}, {}
        for s in sorted(self.tw):   # (shape 1, 3.13) the tsv line as its own class (lit b, oth), the file's csv width Wc a case
            self.tw_classes(s)
        self.empty_ok = {s: self.readable(s, [], None) for s in self.tabs}
        self.st_len, self.st_len2, self.lay, self.wo2 = {}, {}, set(), {}   # (shape 2, 3.12) per (table read by size(), or beside one, type): its least line's bytes
        self.sl = set(self.tabs) if self.st else set()   # (3.12a) every table of a statement with a table's size: its text is charged
        for s in sorted(self.sl & self.tw):   # (3.13h) the 'o' case's least is at its least width: the least >= w no literal line has
            self.wo[s] = next(v for v in itertools.count(self.width[s]) if v not in self.wcs[s])
        if any(s2 in self.tn and k >= 2 for s2, k in self.hcols):
            raise NotT("a header name past column 1 of a file read by tsv() and csv()")   # (3.13d) the tsv header's spelling would be bound
        self.sk = [k for e in tops for k in stmts(e) if self.sl & set(k)]   # (G03) per statement: a let's in its own
        self.rl = [s for s in self.tabs if self.kind[s] in ("tsv", "csv") and s not in self.sl and s not in self.tw]   # (F02) each one's least text
        self.rk = [k for e in tops for k in [collections.Counter({s: n for s, n in c.items() if s in self.rl}) for c in stmts(e)] if k]   # (G03)
        self.ek = [C for e in tops for C in evreads(e) if C]   # (G04c) each statement's events-file reads
        self.rm = [(ws[0] - {k[1] for k in ks}, ws[1], ks) for e in tops for ws in [wheres(e)] for ks in [sorted({k for C in evreads(e) for k in C}, key=repr)]
                   if (ws[0] or ks) and ws[0] - {k[1] for k in ks} <= set(self.rl)]   # (G05; H07) each statement's accounted memory, its events files'
        for s in sorted(self.sl):   # (3.12a) each tsv()/csv() call charges its whole text to MAX_TEXT_TOTAL (readers.text, _cached)
            if any(x.fn == "widen" for x in calls) or any(s2 == s for s2, _ in self.cells | self.hcols | set(cuts) | set(self.agg)) or any(v[1] == s for v in self.num):
                raise NotT("size() of a table with its cells, header or numbers read")
            if any(self.kind[n] not in ("tsv", "csv", "raw", "nifti") for n in self.names) or self.width[s] > 26:
                raise NotT("size() of a table beside other reads")
            if s in self.tw:   # (3.13h) per csv width case W0, each type that can be: its least line at width W0
                self.steps += len(self.types[s]) * (len(self.wcs[s]) + 1) * (max(self.wo[s], len(self.wcs[s]), 2) + len(self.classes[(s, 0)]))
                for wc in self.wcs[s]:
                    W0 = wc if wc != "o" else self.wo[s]
                    for t in sorted(self.tok[(s, wc)]):
                        self.st_len[(s, t, W0)] = self.tw_len(s, t, W0)
                        if self.st_len[(s, t, W0)] is None and wc != "o":
                            raise NotT("size() of a file read by both readers: a row with no line")   # not reached: tok's wc = 1 has no empty cell
                if any(self.st_len[(s, t, self.wo[s])] is None for t in self.tok[(s, "o")]):   # the 'o' case at width 1: a row with an empty csv cell
                    if s not in self.st:   # has no line there (CSV '""', which TSV refuses, T005): from width 1 or from the next (3.12b's split)
                        raise NotT("a one-column table with an empty literal beside a table's size")   # as 3.12b
                    self.lay.add(s)
                    self.wo2[s] = next(v for v in itertools.count(2) if v not in self.wcs[s])
                    for t in sorted(self.tok[(s, "o")]):
                        self.st_len[(s, t, self.wo2[s])] = self.tw_len(s, t, self.wo2[s])
                continue
            if self.width[s] == 1 and any(c[:2] == ("lit", b"") for c in self.classes.get((s, 1), [])):   # (3.12b) one column, an empty literal
                if s not in self.st:
                    raise NotT("a one-column table with an empty literal beside a table's size")   # its least: the lesser of two layouts
                self.lay.add(s)
            for t in self.types[s]:
                if s in self.lay:   # (3.12b) its rows in one column (an empty cell: none in a TSV, '""' in a CSV), or in two
                    try:
                        self.st_len[(s, t)] = len(self.sline(s, t, None).encode("utf-8"))
                    except NotT:
                        self.st_len[(s, t)] = None
                    self.st_len2[(s, t)] = len(self.sline(s, t, None, 2).encode("utf-8"))
                else:
                    self.st_len[(s, t)] = len(self.sline(s, t, None).encode("utf-8"))
        self.steps += sum(len(t) for t in self.types.values())
        self.rsreg, self.rsin = {}, {}   # (R2) per (dataset, task): its regions, the types no set tells apart; per set its regions
        for x in self.rsets:
            C = rconds(x)   # a part's whole drops the filter, or one of its conditions
            for v in [None, C] + [C[:i] + C[i + 1:] for i in range(len(C or ()))]:
                self.rsin[(x.args[0].args[0].id, x.args[1].v.decode("ascii", "replace"), v)] = None
        self.rs8 = set()   # (3.9d) datasets whose two tasks' trials are read over participant groups: one partition for both
        for d in sorted({k[0] for k in self.rsin}):
            if self.kind[d] == "pt" and "trials" in self.rsqs(d) and len(self.rs[d]) > 1:
                ks = sorted((k for k in self.rsin if k[0] == d), key=repr)
                S = {k: set(self.types[d] if k[2] is None else self.selected(d, k[2])) for k in ks}
                if len({tuple(ty in S[k] for k in ks) for ty in self.types[d]}) > 1:
                    if len(self.rs[d]) > 2 or d in self.rsm or 1 in self.cols[d]:
                        raise NotT("trials of three or more tasks, or beside another quantity, or with participant_id read, over participant groups")
                    self.rs8.add(d)
        for d, t in sorted({k[:2] for k in self.rsin}):
            ks = sorted((k for k in self.rsin if k[:2] == (d, t) or k[0] == d and d in self.rs8), key=repr)
            if self.kind[d] == "rs":
                self.rsreg[(d, t)], _ = [None], self.rsin.update({k: [0] for k in ks})
                continue
            S = {k: set(self.types[d] if k[2] is None else self.selected(d, k[2])) for k in ks}
            cells = {}
            for ty in self.types[d]:
                cells.setdefault(tuple(ty in S[k] for k in ks), []).append(ty)
            regs = sorted(v for c, v in cells.items() if any(c))
            self.rsreg[(d, t)] = [frozenset(r) for r in regs]
            self.rsin.update({k: [i for i, r in enumerate(regs) if r[0] in S[k]] for k in ks})

    # ---- classes and spellings (SPEC-EXACT 3.1, 3.2) ---------------------------------------------

    def column(self, s, k, ls, cuts):
        """The realisable classes of column k: ('lit', bytes, value), ('oth', None, None) for text
        that is no literal and no decimal, ('pt', p, p) and ('iv', (lo, hi), a value inside) for the
        decimals at each point and in each open interval the cutoffs and literal values cut out,
        when the column is read as a number."""
        numeric = bool(cuts) or ("cell", s, k) in self.num or (s, k) in self.agg
        vals = []
        for b in ls:
            try:
                vals.append(R.decimal(b.decode("utf-8")) if numeric else None)
            except R.Refusal:
                raise NotT("a literal the number reader refuses") from None
        out = [("lit", b, v) for b, v in zip(ls, vals)] + [("oth", None, None)]
        if numeric:
            pts = sorted(set(cuts) | {v for v in vals if v is not None})
            ends = [None] + pts + [None]
            self.regs[(s, k)] = [r for i in range(len(pts) + 1) for r in [("iv", ends[i], ends[i + 1])] + ([("pt", pts[i])] if i < len(pts) else [])]
            for i in range(len(pts) + 1):
                a = inside(ends[i], ends[i + 1], self.pay)
                out += [("iv", (ends[i], ends[i + 1]), a)] if a is not None else []   # P1: no readable number there
                if i < len(pts) and in_r(pts[i]):
                    out.append(("pt", pts[i], pts[i]))
        if self.kind[s] == "pt" and k == 1:   # item 4: a row's label is sub-<a key> (B11); a literal that is not one has no row
            out = [c for c in out if c[0] == "oth" or (c[1].startswith(b"sub-") and is_key(c[1][4:].decode("ascii", "replace")))]
        return [c for c in out if self.probe(s, k, c)]

    def text(self, s, k, c, v, z=None):
        """The v-th spelling of class c in column k of slot s (a decimal class: of the value z, or of
        its own value): no two spellings in a column look alike, and none looks like a literal."""
        if c[0] == "lit":
            return c[1].decode("utf-8")
        lit = self.lits.get((s, k), [])
        strs = {b.decode("utf-8") for b in lit}
        sks = {skeleton(t) for t in strs}
        if c[0] == "oth":
            have = self.spell.setdefault((s, k), [])
            fresh = W._fresh()
            while len(have) <= v:
                w = next(fresh)
                sk = skeleton(w)
                if w not in strs and sk not in sks and not any(ch.isdigit() for ch in sk) and invisible(w) is None and sk not in {skeleton(h) for h in have}:
                    have.append(w)
            return have[v]
        q = c[2] if z is None else z
        j = n = 0
        while True:
            w = dec_seq(q, j)
            if w is None:
                raise Big("a certificate needs more spellings of one number than the reader reads (P1, SPEC-EXACT 3.1)")
            if w not in strs and skeleton(w) not in sks:
                if n == v:
                    return w
                n += 1
            j += 1

    def htext(self, k, c, v, z=None):
        """The v-th spelling of header cell k: c<k> and other names, or the decimal z."""
        if c[0] == "oth":
            return f"c{k}" if v == 0 else f"c{k}v{v}"
        return dec_seq(c[2] if z is None else z, v)

    def hclasses(self, s, k):
        return [c for c in [("oth", None, None)] + ([("iv", (None, None), Fraction(0))] if ("header", s, k) in self.num else []) if self.readable(s, [], {k: self.htext(k, c, 0)})]

    def scell(self, s, k, c, one):
        """(shape 2) the least spelling of class c in column k (one: of at least one byte); a least one the classes'
        spellings cannot reach (an empty text that looks like a literal): not modelled."""
        if c[0] == "lit":
            if one and c[1] == b"" and (self.kind[s] != "csv" or s in self.tc):   # (3.12b) an empty line of a one-column TSV is refused (T003): no such row; (3.13h) read by tsv() too: CSV's '""' is refused by TSV (T005)
                raise NotT("size() of a one-column table with an empty literal")
            return c[1].decode("utf-8")
        strs = {b.decode("utf-8") for b in self.lits.get((s, k), [])}
        sks = {skeleton(t) for t in strs}
        w = next(w for w in fills(([] if one else [""]) + list(FILLC)) if w not in strs and skeleton(w) not in sks and invisible(w) is None)
        if len(w) != (0 if not one and "" not in strs else 1):
            raise NotT("size() of a table whose least text looks like a literal")
        return w

    def sline(self, s, t, sep, w=None):
        """(shape 2) a row of type t at its least bytes (sep None: the line's text; else its cells); w: the file's width
        (3.12b: a one-column table's rows written with one more column)."""
        w = w or self.width[s]
        W1 = w == 1
        cells = self.tw_least(s, t, w) if s in self.tw else [self.scell(s, k, self.cls(s, t, k), W1) if k in self.cols[s] else "p" if W1 else "" for k in range(1, w + 1)]
        if W1 and cells == [""]:   # (3.12b) a one-column CSV's empty cell: quoted ("" is no empty line)
            return ['""'] if sep else '""\n'
        q = lambda c: '"' + c.replace('"', '""') + '"' if self.kind[s] == "csv" and any(x in c for x in ',";\t') else c  # noqa: E731
        return cells if sep else ("\t" if self.kind[s] == "tsv" else ",").join(q(c) for c in cells) + "\n"

    def tw_len(self, s, t, W0):
        """(3.13h) the bytes of a type's least line at width W0; None: no line (one column, an empty csv cell: '""', T005)."""
        return None if W0 == 1 and self.tw_least(s, t, 1) is None else len(self.sline(s, t, None, W0).encode("utf-8"))

    def tw_least(self, s, t, W0):
        """(3.13h) the least cells of a row of type t in a file read by both readers at csv width W0 (None: no line): a line literal's
        pieces; else each read column's least spelling (scell) and, in a column not read, the empty text or the first
        letter no width-W0 line literal's piece there looks like (so the line is no literal line, as tw_rows)."""
        c0 = self.cls(s, t, 0)
        if c0[0] == "lit":
            return [q.decode("utf-8") for q in c0[1].split(b",")]
        if W0 == 1 and 1 in self.cols[s] and self.cls(s, t, 1)[:2] == ("lit", b""):
            return None   # one column, an empty csv cell: CSV writes '""', which TSV refuses (T005): no such line
        L = [c[1].decode("utf-8") for c in self.classes[(s, 0)] if c[0] == "lit"]
        ps = [b.split(",") for b in L if b.count(",") + 1 == W0]
        out = []
        for k in range(1, W0 + 1):
            if k in self.cols[s]:
                out.append(self.scell(s, k, self.cls(s, t, k), W0 == 1))
            else:
                taken = {skeleton(p[k - 1]) for p in ps}
                out.append(next(w for w in fills(([] if W0 == 1 else [""]) + list(FILLC)) if skeleton(w) not in taken and invisible(w) is None))
        if skeleton(",".join(out)) in {skeleton(b) for b in L}:
            raise NotT("size() of a file read by both readers whose least line looks like a literal")
        return out

    def table(self, s, rows, hdr=None, bare=False, w=None):
        if s in self.tc1:   # (3.10) one column, no extra one: its TSV reading is then its CSV reading
            rows = [r[:1] for r in rows]
        hs = [f"c{k}" for k in range(1, (w or self.width[s]) + 1)] + ([] if s in self.tc1 or bare else ["zpad"])
        for k, t in (hdr or {}).items():
            hs[k - 1] = t
        if self.kind[s] == "pt":   # item 2b: participants.tsv: participant_id first, a sub- label per row (as W._dataset writes);
            hs, rows = ["participant_id"] + hs[1:], [[self.plabel(s, r[0], i)] + r[1:] for i, r in enumerate(rows, 1)]   # item 4: a literal's
        if self.kind[s] in ("tsv", "pt"):
            return "".join("\t".join(r) + "\n" for r in [hs] + rows).encode("utf-8")
        q = lambda c: '"' + c.replace('"', '""') + '"' if any(x in c for x in ',";\t\r\n') else c  # noqa: E731
        return "".join(",".join(q(c) for c in r) + "\n" for r in [hs] + rows).encode("utf-8")

    def plabel(self, s, t, i):
        """(item 4) row i's participant label: its literal's when column 1 is read and its class is one, else sub-w<i> (or,
        when that looks like a literal, the first letter that does not)."""
        ls = {skeleton(b.decode("utf-8", "replace")) for b in self.lits.get((s, 1), ())}
        if 1 in self.cols.get(s, ()) and t.encode("utf-8") in self.lits.get((s, 1), ()):
            return t
        return next(f"sub-{a}{i}" for a in fills("wvqxyz" + "abcdefghijkmnoprstu") if skeleton(f"sub-{a}{i}") not in ls)

    def readable(self, s, rows, hdr):
        """The slot's real reader accepts the table and reads back exactly these cells and header."""
        data = self.table(s, rows, hdr)
        self.steps += len(data) // 64 + 1
        try:
            h = hashlib.sha256(data).hexdigest()
            tab = B.bids_tsv(data, h, "participants.tsv", R.Steps()) if self.kind[s] == "pt" else (R.parse_tsv if self.kind[s] == "tsv" else R.parse_csv)(data, h, R.Steps())
            if s in self.tc and len(R.parse_tsv(data, h, R.Steps()).rows) != len(tab.rows):   # (3.10) read by tsv() too: as many rows
                return False
        except R.Refusal:
            return False
        if s in self.tc1:   # (3.10) one column: the TSV reader reads the same cells
            rows = [r[:1] for r in rows]
            if [list(r) for r in R.parse_tsv(data, h, R.Steps()).rows] != rows:
                return False
        return [list(r)[self.kind[s] == "pt":] for r in tab.rows] == [r[self.kind[s] == "pt":] for r in rows] and all(tab.header[k - 1] == t for k, t in (hdr or {}).items())

    def probe(self, s, k, c):
        """SPEC-EXACT 3.2: a class is realisable when one row holding its spelling is read back (H1:
        with the extra column, a row is read when each of its cells is)."""
        r = ["p"] * (self.width[s] + 1)
        r[k - 1] = self.text(s, k, c, 0)
        return self.readable(s, [r], None)

    def cls(self, s, t, k):
        return self.classes[(s, k)][t[self.cix(s, k)]]

    def tkey(self, x):
        """cell(t, key(...), k)'s pairs; (3.13e) on tsv(f) of a file read by both readers, column 1 is the line (column 0)."""
        ks = key_of(x.args[1])
        return tuple((0, b) for _, b in ks) if isinstance(x.args[0], Call) and x.args[0].fn == "tsv" and x.args[0].args and getattr(x.args[0].args[0], "id", None) in self.tw else ks

    def cix(self, s, k):
        """A column's place in a type: (shape 1) the tsv line of a file read by both readers is the last."""
        return -1 if k == 0 and s in self.tw else self.cols[s].index(k)

    def tw_classes(self, s):
        """(shape 1, SPEC-EXACT 3.13) a file read by tsv() and csv(): its TSV reading is one column whose cell is the CSV
        line (the cells joined by ','; no TAB, quote or ';'), so a tsv() literal b is a line of exactly b's commas plus
        one CSV columns, Wc, one per file. Classes of the line: each literal b read back so by both readers in a table of
        b's width (its pieces in the columns read: their literal classes), and oth. Cases: Wc = c + 1 per literal's
        comma count c, or any other width ('o'); in each, the types that cannot be (tok)."""
        w, L = self.width[s], []
        for b in self.lits.get((s, 0), []):
            ps = b.split(b",")
            if len(ps) < w or any(k in self.cols[s] and not any(c[:2] == ("lit", q) for c in self.classes[(s, k)]) for k, q in enumerate(ps, 1)) or not self.tw_line(b):
                continue
            L.append(("lit", b, None))
        sl, lf = {skeleton(c[1].decode("utf-8")) for c in L}, set()   # (shape 1 review, 3.13a) a line every read column forces that looks like a literal
        for wc in sorted({c[1].count(b",") + 1 for c in L}):
            if all(k in self.cols[s] for k in range(1, wc + 1)):
                self.steps += len(self.types[s])
                for t in self.types[s]:
                    if all(self.cls(s, t, k)[0] == "lit" for k in range(1, wc + 1)):
                        line = b",".join(self.cls(s, t, k)[1] for k in range(1, wc + 1))
                        if line not in {c[1] for c in L} and skeleton(line.decode("utf-8")) in sl and self.tw_line(line):
                            lf.add(line)
        L += [("lit", b, None) for b in sorted(lf)]   # its own class: the where()'s look-alike scope refuses its rows K002, as a csv column's
        self.classes[(s, 0)] = L + [("oth", None, None)]
        self.types[s] = [t + (j,) for t in self.types[s] for j in range(len(L) + 1)]
        self.wcs[s] = sorted({c[1].count(b",") + 1 for c in L} | ({1} if s in self.tn and w == 1 else set())) + ["o"]   # (3.13b) number() of the line: Wc = 1 its own case
        self.wo[s] = next(v for v in itertools.count(w + 1) if v not in self.wcs[s])
        for wc in self.wcs[s]:
            ok = set()
            for t in self.types[s]:
                c0 = self.cls(s, t, 0)
                if c0[0] == "lit":
                    ps = c0[1].split(b",")
                    good = len(ps) == wc and all(self.cls(s, t, k)[:2] == ("lit", ps[k - 1]) for k in self.cols[s])
                elif wc == "o":
                    good = True
                else:
                    full = all(k in self.cols[s] for k in range(1, wc + 1)) and all(self.cls(s, t, k)[0] == "lit" for k in range(1, wc + 1))
                    line = b",".join(self.cls(s, t, k)[1] for k in range(1, wc + 1)) if full else None
                    good = line not in {c[1] for c in L} and not (wc == 1 and 1 in self.cols[s] and self.cls(s, t, 1)[:2] == ("lit", b""))
                    if good and line is not None and skeleton(line.decode("utf-8")) in {skeleton(c[1].decode("utf-8")) for c in L}:
                        good = False   # (3.13a) not a class above: the line is not read back as one line by both readers, so no readable file holds it
                if good:
                    ok.add(t)
            self.tok[(s, wc)] = ok
        self.steps += len(self.types[s]) * len(self.wcs[s])

    def tw_line(self, b):
        """(shape 1) b is read back as one line of its comma count plus one columns by both readers."""
        if any(ch in b for ch in b'\t";\r\n'):
            return False
        ps = b.split(b",")
        try:
            data = (",".join(f"c{k}" for k in range(1, len(ps) + 1)) + "\n").encode() + b + b"\n"
            h = hashlib.sha256(data).hexdigest()
            return [list(r) for r in R.parse_csv(data, h, R.Steps()).rows] == [[q.decode("utf-8") for q in ps]] and [list(r) for r in R.parse_tsv(data, h, R.Steps()).rows] == [[b.decode("utf-8")]]
        except (R.Refusal, UnicodeDecodeError):
            return False

    def sat(self, s, t, c):
        """Condition c on a row of type t: True, False, or None (a number condition on a cell that
        is not a decimal)."""
        x = self.cls(s, t, c[1])
        if c[0] in ("eq", "ne"):
            return (x[0] == "lit" and x[1] == c[2]) == (c[0] == "eq")
        return None if x[2] is None else NUMC[c[0]](x[2], c[2])

    def wconds(self, e):
        """A where()'s conditions; (shape 1) on tsv(f) of a file read by both readers, column 1 is the line (column 0)."""
        cs = tuple(map(norm, e.args[1:]))
        a = e.args[0]
        return tuple((c[0], 0, c[2]) for c in cs) if isinstance(a, Call) and a.fn == "tsv" and a.args and getattr(a.args[0], "id", None) in self.tw else cs

    def selected(self, s, conds):
        self.steps += len(self.types[s])
        return [t for t in self.types[s] if all(self.sat(s, t, c) for c in conds)]

    def undecided(self, s, conds):
        """SPEC v4 7.3: the types on which where() refuses V005 (every byte condition holds, every
        number condition holds or cannot read its cell, and one cannot)."""
        out = []
        for t in self.types[s]:
            v = [self.sat(s, t, c) for c in conds]
            if None in v and all(x is not False for x in v):
                out.append(t)
        return out

    def keyed(self, s, t, kp):
        return all(self.cls(s, t, k)[:2] == ("lit", b) for k, b in kp)

    # ---- cases (SPEC-EXACT 3.4) -------------------------------------------------------------------

    def named(self, es):
        """Per slot: the row positions, keys and header columns the expressions es name."""
        pos, keys, hdr = {}, {}, {}
        for e in es:
            for x in W.walk(e):
                if isinstance(x, Call) and x.fn == "cell":
                    s = table_slot(x.args[0])
                    if isinstance(x.args[1], Int):
                        pos.setdefault(s, set()).add(x.args[1].v)
                    else:
                        keys.setdefault(s, set()).add(self.tkey(x))
                elif isinstance(x, Call) and x.fn == "header":
                    hdr.setdefault(table_slot(x.args[0]), set()).add(x.args[1].v)
                elif isinstance(x, Call) and x.fn == "participant":   # item 4: the row labelled sub-L, as key(1, "sub-L")
                    d, L = plab(x)
                    keys.setdefault(d, set()).add(((1, b"sub-" + L),))
        return {s: (sorted(pos.get(s, ())), sorted(keys.get(s, ())), sorted(hdr.get(s, ()))) for s in self.tabs}

    def slot_cases(self, s, pos, keys, hcols):
        if s in self.tw:   # (shape 1) per csv width Wc, only the types that can be
            for wc in self.wcs[s]:
                for c in self.slot_cases1(s, pos, keys, hcols, [t for t in self.types[s] if t in self.tok[(s, wc)]]):
                    c.wc = wc
                    yield c
            return
        yield from self.slot_cases1(s, pos, keys, hcols, self.types[s])

    def slot_cases1(self, s, pos, keys, hcols, T):
        K = [[t for t in T if self.keyed(s, t, kp)] for kp in keys]
        hcs = list(itertools.product(*[self.hclasses(s, k) for k in hcols]))
        for h in range(len(pos) + 1):
            for st in itertools.product(*[["none", "many"] + [("p", j) for j in range(h)] + [("x", g) for g in range(len(keys))] for _ in keys]):
                xs = [a[1] for a in st if a[0] == "x"]
                if xs != [sorted(set(xs), key=xs.index).index(g) for g in xs]:
                    continue   # extra rows numbered in order of first use
                n = h + len(set(xs))
                serve = [h + a[1] if a[0] == "x" else a[1] if a[0] == "p" else a for a in st]
                allowed = []
                for i in range(n):
                    ok = [t for t in T if all((t in K[j]) == (serve[j] == i) for j in range(len(keys)) if serve[j] != "many")]
                    allowed.append(ok)
                for ts in itertools.product(*allowed):
                    for hc in hcs:
                        yield Slot(pos, keys, h, list(ts), serve, dict(zip(hcols, hc)))

    def rindex(self, s, k, c):
        """The region of column k (SPEC-EXACT 3.5) a decimal class lies in, or None."""
        return None if c[2] is None else self.regs[(s, k)].index(("iv",) + c[1] if c[0] == "iv" else ("pt", c[2]))

    def agg_cases(self, es):
        """SPEC-EXACT 3.5: where each order statistic's value lies (which summed types of an interval class have rows
        is decided in solve, item 8): a region of its column and, among those in the same interval, a rank."""
        seen, sums, ords, sel = set(), set(), [], {}
        for e in es:
            for x in W.walk(e):
                if isinstance(x, Call) and x.fn in AGG and id(x) not in seen and not (x.args and isinstance(x.args[0], Call) and x.args[0].fn == "recordings"):
                    seen.add(id(x))
                    sh, k = self.shape(x.args[0]), x.args[1].v
                    if x.fn in ("sum", "mean"):
                        sums |= {(sh[1], t) for t in self.selected(sh[1], sh[2]) if self.cls(sh[1], t, k)[0] == "iv"}
                    else:   # its value is one of its rows': only regions holding a class of a type it selects
                        ts = self.selected(sh[1], sh[2])
                        ords.append((id(x), sh[1], k, sorted({self.rindex(sh[1], k, self.cls(sh[1], t, k)) for t in ts} - {None})))
                        sel.setdefault((sh[1], k), set()).update(ts)
        sums = sorted(sums)
        for regs in itertools.product(*[rs or [0] for _, _, _, rs in ords]):
            groups = {}
            for (i, s, k, _), r in zip(ords, regs):
                if self.regs[(s, k)][r][0] == "iv":
                    groups.setdefault((s, k, r), []).append(i)
            gs = sorted(groups)
            for ranks in itertools.product(*[weak(len(groups[g])) for g in gs]):
                ordv = {i: (s, k, r, 0) for (i, s, k, _), r in zip(ords, regs)}
                for g, rk in zip(gs, ranks):
                    ordv.update({i: g + (q,) for i, q in zip(groups[g], rk)})
                yield Extra(sums, {}, ordv, {g: max(rk) + 1 for g, rk in zip(gs, ranks)}, sel)

    def file_cases(self, s, es):
        """SPEC-EXACT 3.6: a NIfTI slot's cases are its dim[0] (1 to 7); a JSON slot's, the kinds and
        presence of the nodes on the named paths; a raw slot has one."""
        if s in self.nr:   # (3.10) with size(): a NIfTI-2 header (size >= 544), a NIfTI-1 one (352 to 543, dims <= 32767), gzip (19 to 543)
            yield from (NCase(d, None, z) for d in range(1, 8) for z in ("n2", "n1", "gz"))
            return
        if self.kind[s] == "nifti":   # (f) with pixdim(): from dim[0] = 4 also the time unit (0: I005); with no dim() read,
            for d in (1, 4) if s in self.pix - self.dimr else range(1, 8):   # dim[0] 1 and 4 stand for 1-3 and 4-7
                yield from [NCase(d, u) for u in (8, 16, 24, 0)] if d >= 4 and s in self.pix else [d]
            return
        if self.kind[s] == "raw":   # (shape 3) per number()-read range: not a number (V005), or a number of its n bytes
            yield from itertools.product(*[("nan",) + (("num",) if rnext(n, None) is not None else ()) for _, n in self.rreg.get(s, [])]) if s in self.rreg else [None]
            return
        if self.kind[s] == "rs":   # (R1) its cases are rs_cases'
            yield None
            return
        if self.kind[s] == "rec":
            yield from self.rec_cases(s)
            return
        paths = {()}
        for e in es:
            for x in W.walk(e):
                if isinstance(x, Call) and x.fn in ("member", "item") and jpath(x)[0] == s:
                    p = jpath(x)[1]
                    paths |= {p[:i] for i in range(len(p) + 1)}
        nodes = sorted(paths, key=lambda p: (len(p), repr(p)))
        kids = {p: [q for q in nodes if len(q) == len(p) + 1 and q[:-1] == p] for p in nodes}
        for kinds in itertools.product(*[("obj", "arr", "num", "str", "word") for _ in nodes]):
            K = dict(zip(nodes, kinds))
            mem = [q for p in nodes for q in kids[p] if K[p] == "obj" and q[-1][0] == "m"]
            arrs = [p for p in nodes if K[p] == "arr" and any(q[-1][0] == "i" for q in kids[p])]
            for th in itertools.product((False, True), repeat=len(mem)):
                for hs in itertools.product(*[range(len([q for q in kids[p] if q[-1][0] == "i"]) + 1) for p in arrs]):
                    L = {}
                    for p, h in zip(arrs, hs):
                        ix = sorted(q[-1][1] for q in kids[p] if q[-1][0] == "i")
                        L[p] = (h, ix)
                    yield JCase(K, dict(zip(mem, th)), L)

    def rs_cases(self, d):
        """(R1, R2) per task: the order of its refusing recordings (the kernel reads a set in sort order: per region the
        order of its kinds, then the regions' order; one refusing kind: one order), and each region's state: no
        recordings ("e", with participants.tsv), none answering ("z"), answering ones ("p"); with no aggregate, any ("f")."""
        q, agg = self.rsq.get(d, ("tr",))[0], d in self.rsq
        sts = (("e", "z", "p") if agg else ("e", "f")) if self.kind[d] == "pt" else ("z", "p") if agg else ("f",)
        if d in self.rsm:   # (3.9a, 3.9b) the order is the events file's kinds (trials: two); a state per events-file class (volumes: N = 0 gives Y = 0)
            q = "trials" if "trials" in self.rsqs(d) else "tr"
            sts = (("e",) if self.kind[d] == "pt" else ()) + tuple(itertools.product(("z", "p"), repeat=len(self.rs_evc(d))))
        per, memo, ts = [], {}, sorted(self.rs[d])

        def firsts(t, st, S=None):   # (3.9d) a region with no recordings ("e") holds no pair
            R = range(len(self.rsreg[(d, t)]))
            E = tuple(r for r in R if st[r] == "e")
            if (t, E, S) not in memo:
                os = [tuple(zip(P, ks)) for P in itertools.permutations(R) for ks in itertools.product(itertools.permutations(RSBAD[q]), repeat=len(R))] if len(RSBAD[q]) > 1 else [tuple((r, RSBAD[q]) for r in R)]
                memo[(t, E, S)] = self.rs_firsts(d, t, [tuple((r, ks) for r, ks in o if r not in E) for o in os], S)
            return memo[(t, E, S)]
        for t in ts if d not in self.rs8 else ():
            R = range(len(self.rsreg[(d, t)]))
            per.append([(t, o, st, ch, sp) for st in itertools.product(sts, repeat=len(R)) for o, ch, _ in firsts(t, st) for sp in self.rs_sp(d, t, st)])
        if d not in self.rs8:
            for c in itertools.product(*per):
                yield {t: (o, st, ch, None, sp) for t, o, st, ch, sp in c}
            return
        R = range(len(self.rsreg[(d, ts[0])]))   # (3.9d) one partition for both tasks of an rs8 dataset
        for sx, sy in itertools.product(itertools.product(sts, repeat=len(R)), repeat=2):   # (3.9d) where both tasks have recordings: one
            both = [r for r in R if sx[r] != "e" and sy[r] != "e"]   # participant row there (one order of these for both tasks) or two or more
            for fb in itertools.product((1, 2), repeat=len(both)):
                fl = tuple(dict(zip(both, fb)).get(r, 0) for r in R)
                S = tuple(r for r in R if fl[r] == 1)
                ex, ey = firsts(ts[0], sx, S), firsts(ts[1], sy, S)
                for (o1, c1, p1), (o2, c2, p2) in itertools.product(ex, ey):
                    for s1, s2 in itertools.product(self.rs_sp(d, ts[0], sx), self.rs_sp(d, ts[1], sy)) if p1 == p2 else ():
                        yield {ts[0]: (o1, sx, c1, fl, s1), ts[1]: (o2, sy, c2, fl, s2)}

    def rs_sp(self, d, t, st):
        """(3.9e) a sum beside a max of counts of events or trials: per answering region its max 0 (sum 0) or >= 1 (sum >= max);
        beside a min: one recording (sum = min) or two or more (sum >= 2 min); else no split (None)."""
        if self.rs7.get((d, t)) is None or self.rsq[d][0] == "volumes":
            return [None]
        return list(itertools.product(*[(0, 1) if x == "p" else (0,) for x in st]))

    def rs_views(self, d, t):
        """(3.9c) the sets of task t whose first refusing recording an aggregate reads: per sum/mean/min/max its regions and
        (3.9a) the quantity's index (the kinds it reads), each once; with its parts' sets (the filter dropped, or one of its
        conditions: SPEC-EXACT 3.9, R2)."""
        out = set()
        for x in self.rsagg:
            b = x.args[0]
            if b.args[0].args[0].id != d or b.args[1].v.decode("ascii", "replace") != t:
                continue
            i, C = self.rsm[d].index((x.args[1].v.decode(), x.args[2].v if len(x.args) == 3 else None)) if d in self.rsm else None, rconds(b)
            out |= {(tuple(self.rsin[(d, t, v)]), i) for v in [None, C] + [C[:j] + C[j + 1:] for j in range(len(C or ()))]}
        return sorted(out, key=repr)

    def rs_seq(self, d, o, v):
        """(3.9c) a view's (region, kind) pairs in the order o: the regions in o's order, in each its refusing kinds
        (3.9a: those of the view's quantity) in o's order for that region."""
        regs, i = v
        if i is not None:
            qi = self.rsm[d][i][0]
            return [(r, k) for r, ks in o if r in regs for k in (ks if len(RSBAD[qi]) > 1 else RSBAD[qi])]
        return [(r, k) for r, ks in o if r in regs for k in ks]

    def rs_firsts(self, d, t, os, S=None):
        """(3.9c; the smaller order model) the kernel reads a set in sort order, so an aggregate refuses with its first
        refusing recording's code: for an order o, each view's branch is a choice j (its pair j there, the pairs before
        it in the view none) or none there at all. The pairs (o, choices) are R1's cases with their branches, one branch
        per view; two with the same codes and one's pairs there and pairs none within the other's give the same
        outcomes on a larger region, so only the least (by inclusion) are kept, each with an order o that realises it.
        Their union is R1's (no input is lost, none is added); with no view one order is enough. (3.9d) With S, the
        regions of one participant row: kept per order of S's regions too (pi), so that two tasks can agree on it."""
        vs = self.rs_views(d, t)
        if not vs and S is None:
            return [(os[0], (), ())]
        best = {}
        for o in os:
            seqs, pi = [self.rs_seq(d, o, v) for v in vs], tuple(r for r, _ in o if r in (S or ()))
            for js in itertools.product(*[range(len(sq) + 1) for sq in seqs]):
                self.steps += 1
                there, none = set(), set()
                for sq, j in zip(seqs, js):
                    none |= set(sq[:j])
                    there |= {sq[j]} if j < len(sq) else set()
                if there & none:
                    continue
                codes = (pi,) + tuple(RSCODE[sq[j][1]] if j < len(sq) else None for sq, j in zip(seqs, js))
                ks = best.setdefault(codes, [])
                self.steps += len(ks)
                if any(a <= there and b <= none for a, b, _, _ in ks):
                    continue
                ks[:] = [e for e in ks if not (there <= e[0] and none <= e[1])] + [(there, none, o, tuple(zip(vs, js)))]
        return [(o, ch, codes[0]) for codes in sorted(best, key=repr) for _, _, o, ch in best[codes]]

    def rec_cases(self, s):
        """(2c, item 3) per named recording: absent, or its dim[0], events file and trial_type cases."""
        Es, per = sorted(self.recs[s]), []
        for E in Es:
            F, I = self.rread.get((s, E), set()), self.rrows(s, E)
            evs = [None] + list(range(len(I) + 1)) if F & {"onset", "duration", "events", "trials"} else [0]
            per.append([None] + [(d4, ev, tt) for d4 in ((True, False) if "volumes" in F else (True,)) for ev in evs for tt in ((True, False) if "trials" in F and ev is not None else (True,))])
        for c in itertools.product(*per):
            yield RCase(zip(Es, c))

    def rc(self, s, case):
        """(3.8b) slot s's named recordings' case: its own (kind rec), or beside its participants table's (kind pt)."""
        return case[("rec", s)] if self.kind[s] == "pt" else case[s]

    def jbr(self, s, path, case):
        """The outcome of a member()/item() chain in a JSON case (SPEC-EXACT 3.6), as kernel.c_member/c_item
        and json_value give it."""
        c = case[s]
        for i, (st, v) in enumerate(path):
            pk = c.kind[path[:i]]
            if i and pk == "word":
                return ("X", "J004")   # the inner value is true, false or null
            if i and pk in ("num", "str"):
                return ("X", "S007")   # member()/item() of a number or a string
            if st == "m" and (pk != "obj" or not c.there.get(path[:i + 1])):
                return ("V", "V002")
            if st == "i":
                h, ix = c.length.get(path[:i], (0, []))
                if pk != "arr" or (ix[h - 1] if h else 0) < v:
                    return ("V", "V002")
        k = c.kind[path]
        return {"num": ("lin", {("z", "j", s, path): 1}), "str": ("bytes", (s, "json", path)), "word": ("X", "J004")}.get(k, ("jtree", s, path))

    def slot_list(self, s, es, held):
        """Slot s's cases (at most MAX_CASES + 1 of them), held in held."""
        nm = self.named(es)
        return take(self.slot_cases(s, *nm[s]) if s in nm else self.file_cases(s, es), held)

    def cases(self, es, held):
        per = [[self.only[s]] if s in self.only else self.slot_list(s, es, held) for s in self.names]   # only: R3's copy slot, one case at a time
        pr = sorted(d for d in self.recs if self.kind[d] == "pt")   # (3.8b) a participants table's dataset's named recordings
        keys = self.names + [("rs", d) for d in sorted(self.rs)] + [("rec", d) for d in pr]   # (R2) a recording-set dataset's cases
        per += [take(self.rs_cases(d), held) for d in sorted(self.rs)] + [take(self.rec_cases(d), held) for d in pr]
        per.append(take(self.agg_cases(es), held))
        n = 1
        for p in per:
            n *= len(p)
        if n > MAX_CASES:
            raise Big(f"deciding it needs more than {MAX_CASES} cases of the rows it names (SPEC-EXACT 3.4)")
        out = []
        for c in itertools.product(*per):   # item 6 (d): each named row of an interval class in a region with order
            case, X = dict(zip(keys + [None], c)), c[-1]   # statistics lies in one of its pieces (SPEC-EXACT 3.5)
            ks = [(s, i, k, 2 * X.nw[(s, k, r)] + 1) for s in self.tabs for i, t in enumerate(case[s].types) for k in self.cols[s]
                  for r in [self.rindex(s, k, self.cls(s, t, k))] if (s, k, r) in X.nw]
            for ps in itertools.product(*[range(m) for *_, m in ks]):
                hold(held, held[0] * STEP_BYTES + 576 + 64 * (len(case) + len(ks)))   # the case's dict, its Extra and npc
                out.append({**case, None: Extra(X.sums, X.pres, X.ordv, X.nw, X.sel, {q[:3]: p for q, p in zip(ks, ps)})})
                if len(out) > MAX_CASES:
                    raise Big(f"deciding it needs more than {MAX_CASES} cases of the rows it names (SPEC-EXACT 3.4)")
        self.steps += len(out)
        return out

    def size(self, s, case, types):
        """The number of rows of these types: the unnamed ones (variables) and the named ones."""
        ts = set(types)
        return lin((1, {("n", s, t): 1 for t in ts}), (1, const(sum(t in ts for t in case[s].types))))

    def rlb(self, s, case):
        """(F02; G04, Opus 5.5 max review 04) Table s's least text in a case, exactly: ([(bytes, {n_t: 1})], constant).
        A row of type t is at least its least line (Model.lline) and a line feed; the header W one-byte names and W - 1
        separators (header classes are other text or a decimal: one byte each); the case's named rows their least lines;
        the last line feed may be dropped. Each is reached by a readable table, so this is the read limit's exact bound."""
        lf = {t: self.lline(s, t) + 1 for t in self.types[s]}
        return [(lf[t], {("n", s, t): 1}) for t in self.types[s]], 2 * self.width[s] - 1 + sum(lf[t] for t in case[s].types)

    def mlb(self, s, case):
        """(G05) Table s's least accounted memory in a case (readers.Store: its text, len + 64; kernel._table_size: 64,
        and per row 64 + 80 a cell + the cell's characters, the header's W one-character names), at its least text:
        ([(bytes, {n_t: 1})], constant). The least table (build.least_table) reaches it."""
        w, (L, c) = self.width[s], self.rlb(s, case)
        row = {t: 64 + 80 * w + self.lchars(s, t) for t in self.types[s]}
        return [(a + row[t], {("n", s, t): 1}) for (a, _), t in zip(L, self.types[s])], c + 64 + 64 + 64 + 81 * w + sum(row[t] for t in case[s].types)

    def lchars(self, s, t):
        """(G05) The characters of the cells of t's least line (Model.lline's cells, unquoted); (B09, Argon review 2 09) a lower
        bound for other text: a cell of b bytes may hold 4-byte UTF-8 characters, so ceil(b / 4) (a literal or a decimal is exact)."""
        key = ("lchars", s, t)
        if key not in self.lmemo:
            w, csv = self.width[s], self.kind[s] == "csv"
            q = lambda c: len(c.encode("utf-8")) + (2 + c.count('"') if csv and any(x in c for x in ',";\t') else 0)   # noqa: E731
            n = 0
            for k in range(1, w + 1):
                c = self.cls(s, t, k) if k in self.cols[s] else ("oth", None, None)
                b, x = self.cmin(s, k if k in self.cols[s] else None, c, w == 1, q)
                if w == 1 and csv and self.cmin(s, k if k in self.cols[s] else None, c, False, q, quoted=True)[0] < b:
                    x = ""
                n += -(-len((x or "").encode("utf-8")) // 4) if c[0] == "oth" else len(x or "")
            self.lmemo[key] = n
        return self.lmemo[key]

    def lline(self, s, t):
        """(G04) The bytes of the least line of a row of type t in table s: each column's least cell (a column not read: the
        empty text, but one byte in a one-column TSV, T003), csv quoting as the writer needs, W - 1 separators."""
        key = ("lline", s, t)
        if key not in self.lmemo:
            w, csv = self.width[s], self.kind[s] == "csv"
            q = lambda c: len(c.encode("utf-8")) + (2 + c.count('"') if csv and any(x in c for x in ',";\t') else 0)   # noqa: E731
            cells = []
            for k in range(1, w + 1):
                c = self.cls(s, t, k) if k in self.cols[s] else ("oth", None, None)
                one = w == 1
                n = self.cmin(s, k if k in self.cols[s] else None, c, one, q)[0]
                if one and csv:   # (3.12b) a one-column CSV's empty cell is '""'
                    n = min(n, self.cmin(s, k if k in self.cols[s] else None, c, False, q, quoted=True)[0])
                cells.append(n)
            self.lmemo[key] = sum(cells) + w - 1
        return self.lmemo[key]

    def cmin(self, s, k, c, one, q, quoted=False):
        """(G04) (bytes, text) of the least cell of class c in column k (None: not read) as written (q: with csv quoting);
        one: at least one byte (a one-column TSV, T003); quoted: the empty cell as '""'. A literal is its bytes; other
        text the least text that is no literal, looks like none (skeleton) and is no decimal where the column is read as a
        number; a decimal class the least spelling (readers.decimal) of a number in it that is no literal and looks like
        none (a point: its value; an interval: any readable number strictly inside, found by scale)."""
        key = ("cmin", s, k, c, one, quoted)   # q is the table's own quoting: one per s
        if key not in self.lmemo:
            self.lmemo[key] = self.cmin1(s, k, c, one, q, quoted)
        return self.lmemo[key]

    def cmin1(self, s, k, c, one, q, quoted):
        """(G04) cmin, computed."""
        if quoted:   # the empty cell, if the class holds it
            return (2, "") if c[0] == "lit" and c[1] == b"" or c[0] == "oth" and (k is None or b"" not in self.lits.get((s, k), ())) else (10 ** 9, None)
        if c[0] not in ("lit", "oth", "pt", "iv"):
            return 0, None   # not reached: column() makes only these classes; 0 is a bound, never past one
        if c[0] == "lit":
            return (q(c[1].decode("utf-8")), c[1].decode("utf-8")) if not (one and c[1] == b"") else (10 ** 9, None)
        strs = {b.decode("utf-8") for b in self.lits.get((s, k), ())} if k is not None else set()
        sks = {skeleton(x) for x in strs}
        num = k is not None and any(cl[0] in ("pt", "iv") for cl in self.classes[(s, k)])
        ok = lambda w: w not in strs and skeleton(w) not in sks and invisible(w) is None   # noqa: E731
        if c[0] == "oth":   # (H02) any ASCII text the reader keeps in a cell, by length; csv quoting costs its bytes
            bad = set("\n\r") | (set() if self.kind[s] == "csv" else set('"\t'))
            best = None
            for L in itertools.count(1 if one else 0):
                if best is not None and best[0] <= L:
                    return best   # every longer text costs more than L
                found = False
                for t in itertools.product(OTHC, repeat=L):
                    w = "".join(t)
                    self.pay[0] += 1
                    if not bad & set(w) and ok(w) and not (num and dec_or_none(w) is not False):
                        found, best = True, best if best is not None and best[0] <= q(w) else (q(w), w)
                if not found and L >= 2:
                    return (L, None) if best is None or best[0] > L else best   # not reached: every ASCII text of L bytes a literal; a lower bound
        if c[0] == "pt":
            vals = lambda: iter([c[1]])   # noqa: E731
        else:
            lo, hi = c[1]
            vals = lambda: self.in_iv(lo, hi, len(strs) + 1)   # noqa: E731
        ell = min((dec_len(v) for v in vals()), default=None)
        while ell is not None:
            for v in vals():
                self.pay[0] += 1
                if dec_len(v) <= ell:
                    w = next((w for w in dec_spells(v, ell) if ok(w)), None)
                    if w is not None:
                        return ell, w
            ell += 1
            if ell > 2 * DIG + 16:
                return 10 ** 9, None   # not reached: every class the model keeps has a readable member
        return 10 ** 9, None

    def in_iv(self, lo, hi, K):
        """(G04) Readable numbers strictly between lo and hi (None: unbounded): 0 if inside, and on each side of it, at
        each scale 10^E, the K least multiples past the near end; among them a shortest spelling of every length is."""
        if (lo is None or lo < 0) and (hi is None or hi > 0):
            yield Fraction(0)
        for sg, a, b in ((1, lo, hi), (-1, None if hi is None else -hi, None if lo is None else -lo)):
            if b is not None and b <= 0:
                continue
            a = Fraction(0) if a is None or a < 0 else Fraction(a)
            top = (len(str(b.numerator)) - len(str(b.denominator)) + 2) if b is not None else None
            w = (b - a) if b is not None else None
            E0 = max(LOW, (len(str(w.numerator)) - len(str(w.denominator)) - 3) if w is not None else LOW)
            if b is None:   # above a: from a's scale (or 1's), the shortest are the least multiples
                E0 = max(LOW, len(str(a.numerator)) - len(str(a.denominator)) - 3 if a > 0 else -K - 6)
            E1 = min(HIGH + DIG, top if top is not None else (len(str(a.numerator)) - len(str(a.denominator)) + K + 6 if a > 0 else K + 6))
            got = []
            for E in itertools.chain(range(E0, E1 + 1), [None]):
                if E is None:   # (H02) then the finer scales near a's end, down to where every multiple is longer than the
                    ell = min((dec_len(v) for v in got), default=0)   # shortest found: past a > 0, at least lead(a) - E digits
                    F = len(str(a.numerator)) - len(str(a.denominator)) - ell - 1
                    if a == 0:   # past 0, 10^E: "0.0..1" (|E| + 2 bytes) or "1e-N" (3 + digits(N))
                        F = -1
                        while F > LOW and min(2 - F, 3 + len(str(-F))) <= ell:
                            F -= 1
                    got = None
                    for E2 in range(max(LOW, F), E0):
                        yield from self.iv_scale(sg, a, b, E2, K, None)
                    continue
                for v in self.iv_scale(sg, a, b, E, K, got):
                    yield v

    def iv_scale(self, sg, a, b, E, K, got):
        """(G04) The K least readable multiples of 10^E past a and below b, signed sg (got: kept, unsigned)."""
        u = Fraction(10) ** E
        m0 = floor(a / u) + 1
        for j in range(K):
            self.pay[0] += 1
            v = (m0 + j) * u
            if b is not None and v >= b:
                break
            if in_r(v):
                if got is not None:
                    got.append(v)
                yield sg * v

    def smin(self, s, case, w=None):
        """(3.12) a table's least size in a case: the linear part (each type's n_t rows at its least line) and the constant
        (W one-byte header names, W - 1 separators, the case's named rows, the last LF dropped). (3.12b) A one-column
        table with an empty literal (self.lay): w = 1 or 2, its rows in that many columns; None: the lesser per row."""
        if s in self.tw:   # (3.13h) the case's csv width W0: W0 one-byte header names (the tsv header their joined text), its types' least lines
            wc = case[s].wc
            if s in self.lay and wc == "o":   # from width 1 (w = 1), from the next width the case has (w = 2), or the lesser per row (None)
                Ws = [1, self.wo2[s]] if w is None else [1] if w == 1 else [self.wo2[s]]
                ln = {t: min((self.st_len[(s, t, W0)] for W0 in Ws if self.st_len[(s, t, W0)] is not None), default=None) for t in sorted(self.tok[(s, wc)])}
                return [(ln[t], {("n", s, t): 1}) for t in ln if ln[t] is not None], 2 * min(Ws) - 1 + sum(ln[t] or 0 for t in case[s].types)
            W0 = wc if wc != "o" else self.wo[s]
            return [(self.st_len[(s, t, W0)], {("n", s, t): 1}) for t in sorted(self.tok[(s, wc)])], 2 * W0 - 1 + sum(self.st_len[(s, t, W0)] for t in case[s].types)
        if s in self.lay:
            ln = {t: self.st_len2[(s, t)] if w == 2 else self.st_len[(s, t)] if w == 1 else min(x for x in (self.st_len[(s, t)], self.st_len2[(s, t)]) if x is not None)
                  for t in self.types[s]}
            return [(ln[t], {("n", s, t): 1}) for t in self.types[s] if ln[t] is not None], (3 if w == 2 else 1) + sum(ln[t] or 0 for t in case[s].types)
        return [(self.st_len[(s, t)], {("n", s, t): 1}) for t in self.types[s]], 2 * self.width[s] - 1 + sum(self.st_len[(s, t)] for t in case[s].types)

    def lay_cases(self, s, case):
        """(3.12b) A one-column table with an empty literal is read from one column (a TSV: then no row holds the empty
        text, T003) or from two or more (one more header name, a separator per row): its size is at least the least of
        one of them. The two cases, each with its least (RAtoms of ("lay", s), so a split knows it is made)."""
        S, out = {("n", s, "size"): 1}, []
        if s in self.tw and case[s].wc != "o":   # (3.13h) a numbered width case: its one least
            L, m = self.smin(s, case)
            return [[RAtom(ge(lin((1, S), *[(-a, v) for a, v in L], (1, const(-m)))), ("lay", s), 1)]]
        for w in (1, 2):
            L, m = self.smin(s, case, w)
            A = [ge(lin((1, S), *[(-a, v) for a, v in L], (1, const(-m))))]
            if w == 1:
                none = [t for t in self.types[s] if self.st_len[(s, t)] is None] if s not in self.tw else [t for t in sorted(self.tok[(s, "o")]) if self.st_len[(s, t, 1)] is None]
                if any(t in none for t in case[s].types):
                    continue
                A += [ge(lin(*[(-1, {("n", s, t): 1}) for t in none]))] if none else []
            out.append([RAtom(a, ("lay", s), w) for a in A])
        return out

    def case_atoms(self, case):
        out = []
        for (s, E) in sorted(self.rread, key=repr):   # (G06) a trial type no events file holds: no rows of it
            out += [ge(lin((-1, {v: 1}))) for v in self.rtt(s, E) if not tt_holds(v[4])]
        for d in sorted(self.rs):
            no = [(i, lit) for i, (q, lit) in enumerate(self.rsm[d]) if q == "trials" and not tt_holds(lit)] if d in self.rsm else []
            one = d in self.rsq and self.rsq[d][0] == "trials" and not tt_holds(self.rsq[d][1])
            for t, (o, sts, *_) in sorted(case[("rs", d)].items()) if no or one else ():
                for r in range(len(sts)):
                    out += [ge(lin((-1, {self.rs_var(d, t, w, r): 1}))) for w in ("y", "m")] if one else []
                    out += [ge(lin((-1, {self.rs_var(d, t, "y", r, (i, c)): 1}))) for i, _ in no for c in self.rs_evc(d)]
        for s in sorted(self.tw):   # (shape 1, 3.13) in a csv width Wc, the types that cannot be have no rows
            bad = [t for t in self.types[s] if t not in self.tok[(s, case[s].wc)]]
            out += [ge(lin((-1, self.size(s, case, bad))))] if bad else []
        for s in self.rl if self.rb else ():   # (F02; G04) a table's text is at most MAX_TEXT_FILE: its least text exactly (rlb)
            L, m = self.rlb(s, case)
            out.append(ge(lin(*[(-a, v) for a, v in L], (1, const(R.MAX_TEXT_FILE - m)))))
        for ts, ws, ks in self.rm if self.rb else ():   # (G05; H03) the program's accounted memory (readers.Store.account) at the statement: at most MAX_ACCOUNTED
            T, m = [], R.MAX_ACCOUNTED - HELD[0]
            for s in sorted(ts):
                L, c = self.mlb(s, case)
                T += [(-a, v) for a, v in L]
                m -= c
            F, c = self.evmem(ks, case)   # (H07) and its events files'
            T += [(-a, {v: 1}) for v, a in sorted(F.items(), key=repr)]
            m -= c
            for w in ws:
                sh = self.shape(w)
                T.append((-72, self.size(sh[1], case, self.selected(sh[1], sh[2]))))
                m -= 64
            out.append(ge(lin(*T, (1, const(m)))))
        for s, E in sorted({k[1:] for C in self.ek for k in C if k[0] == "rec"}, key=repr) if self.rb else ():   # (G04c) a named recording's events file: at most MAX_TEXT_FILE
            L = self.evlb(s, E, case)
            out += [ge(lin(*[(-a, {v: 1}) for v, a in sorted(L[0].items(), key=repr)], (1, const(R.MAX_TEXT_FILE - L[1]))))] if L else []
        for d, t, c in sorted({k[1:] for C in self.ek for k in C if k[0] == "rs"}, key=repr) if self.rb else ():   # each answering recording's: rows split evenly (W_split_int)
            if d in self.rsm and (d, t) not in self.rs7 and t in case[("rs", d)]:
                out += self.rs_evm(d, t, c, case)[1]
                continue
            k = self.rs_evok(d, t, case)
            for r in self.rsin[(d, t, c)] if k else ():   # a sum's or mean's y <= F N (F a file's most rows), a min's or max's m <= F
                F, Y = (R.MAX_TEXT_FILE - k[0]) // k[1], {self.rs_var(d, t, "y" if k[2] & {"sum", "mean"} else "m", r): 1}
                out += [ge(lin((F, self.rs_n(d, t, "ok", r)) if k[2] & {"sum", "mean"} else (1, const(F)), (-1, Y)))] if case[("rs", d)][t][1][r] == "p" else []
        for C in self.ek if self.rb else ():   # (G04c) the statement's text: each call charges the events files it reads (kernel.events_table)
            T, m = [], R.MAX_TEXT_TOTAL
            for k, n in sorted(C.items(), key=repr):
                L = self.evlb(k[1], k[2], case) if k[0] == "rec" else self.rs_evlb(k[1], k[2], k[3], case)
                T += [(-n * a, {v: 1}) for v, a in sorted(L[0].items(), key=repr)] if L else []
                m -= n * L[1] if L else 0
            out += [ge(lin(*T, (1, const(m))))] if T or m < 0 else []
        for ks in self.rk if self.rb else ():   # (F02; G04) the statement's text: each tsv()/csv() call charges its table's (3.12a), at most MAX_TEXT_TOTAL
            lm = {s: self.rlb(s, case) for s in ks}
            out.append(ge(lin(*[(-k * a, v) for s, k in sorted(ks.items()) for a, v in lm[s][0]], (1, const(R.MAX_TEXT_TOTAL - sum(k * lm[s][1] for s, k in ks.items()))))))
        for ks in self.sk if self.rb else ():   # (3.12a) the statement's text total: each tsv()/csv() call of a slot charges its size (R003 past it)
            T, m = [], R.MAX_TEXT_TOTAL
            for s, k in sorted(ks.items()):
                if s in self.st:
                    T.append((-k, {("n", s, "size"): 1}))
                else:
                    L, c = self.smin(s, case)
                    T += [(-k * a, v) for a, v in L]
                    m -= k * c
            out.append(ge(lin(*T, (1, const(m)))))
        for s in self.names:
            if s in self.sl:   # (shape 2, 3.12) least header, each row's least line, the last LF optional; at most MAX_TEXT_FILE (R003)
                L, m = self.smin(s, case)   # a table beside one (not its size read): at least its least is at most MAX_TEXT_FILE
                if s in self.st:
                    S = {("n", s, "size"): 1}
                    out += [ge(lin((1, S), *[(-a, v) for a, v in L], (1, const(-m))))] + ([ge(lin((-1, S), (1, const(R.MAX_TEXT_FILE))))] if self.rb else [])
                elif self.rb:   # (F02) the read limit only when modelled
                    out.append(ge(lin(*[(-a, v) for a, v in L], (1, const(R.MAX_TEXT_FILE - m)))))
            if self.kind[s] == "nifti":   # each dim named within dim[0]: 1 to 2^63 - 1 (SPEC 7.6)
                for k in range(1, case[s] + 1):
                    D = {("n", s, "dim", k): 1}
                    out += [ge(lin((1, D), (1, const(-1)))), ge(lin((-1, D), (1, const(MAX_DIM))))]
                if s in self.nr:   # (3.10) the file's size by the case: at least its header, or 19 bytes gzipped (RFC 1952: 10 + 8 + a deflate byte)
                    S, z = {("n", s, "size"): 1}, case[s].z
                    out += [ge(lin((1, S), (1, const(-{"n2": 544, "n1": 352, "gz": 19}[z])))), ge(lin((-1, S), (1, const(MAX_DIM if z == "n2" else 543))))]
                    out += [ge(lin((-1, {("n", s, "dim", k): 1}), (1, const(32767)))) for k in range(1, case[s] + 1)] if z == "n1" else []
                if getattr(case[s], "unit", None):   # (f) pixdim[4] a finite float
                    u = {("z", "pix", s): 1}
                    out += [ge(lin((1, u), (1, const(FMAX)))), ge(lin((-1, u), (1, const(FMAX))))]
            if self.kind[s] == "raw":   # a file's size is an off_t: at most 2^63 - 1 bytes (item 7: no MAX_ROWS bound)
                out.append(ge(lin((-1, {("n", s, "size"): 1}), (1, const(MAX_DIM)))))
                for (o, n), cl in zip(self.rreg.get(s, []), case[s] or ()):   # (shape 3) a number of n bytes: between the least and the greatest
                    if cl == "num":
                        z = {("z", "raw", s, o, n): 1}
                        out += [ge(lin((1, z), (-rnext(n, None), const(1)))), ge(lin((-1, z), (rprev(n, None), const(1))))]
            if s in self.recs:   # (2c) TRLO < tr < TRHI; 1 <= volumes <= 2^63 - 1; onset < volumes x tr, so < (2^63 - 1) TRHI
                for E, st in self.rc(s, case).items():   # only the values read have variables (the others: free, chosen in rec_dataset)
                    F, I = self.rread.get((s, E), set()), self.rrows(s, E)
                    if st is None:
                        continue
                    T, V, N = {("z", "tr", s, E): 1}, {("n", s, "vol", E): 1}, {("n", s, "ev", E): 1}
                    out += [gt(lin((1, T), (1, const(-TRLO)))), gt(lin((-1, T), (1, const(TRHI))))] if "tr" in F else []
                    out += [ge(lin((1, V), (1, const(-1)))), ge(lin((-1, V), (1, const(MAX_DIM))))] if "volumes" in F else []
                    for y in self.rval:   # item 3: duration > 0 (B06)
                        if y.fn in ("onset", "duration") and (y.args[0].args[0].args[0].id, rent(y.args[0])) == (s, E):
                            Z = {("z", y.fn[:2], s, E, y.args[1].v): 1}
                            out.append(gt(lin((1, Z))) if y.fn == "duration" else gt(lin((-1, Z), (MAX_DIM, T))) if "tr" in F else gt(lin((-1, Z), (TRHI, V))) if "volumes" in F and st[0]
                                       else gt(lin((-1, Z), (1, const(TRHI)))) if "volumes" in F else gt(lin((-1, Z), (1, const(MAX_DIM * TRHI)))))   # onset < volumes x tr (B30; a 3-D image: 1 x tr)
                    if F & {"events", "trials"} and st[1] is not None:   # item 3: the events file's rows, as many as the case says
                        out += [ge(lin((1, N), (1, const(-(I[st[1] - 1] if st[1] else 0)))))] + ([ge(lin((-1, N), (1, const(I[st[1]] - 1))))] if st[1] < len(I) else [])
                        K = {v: 1 for v in self.rtt(s, E)}
                        out += [ge(lin((1, {v: 1}))) for v in K] + ([ge(lin((1, N), (-1, K)))] if K and st[2] else [])
        for s in sorted(d for d in self.recs if self.kind[d] == "pt"):   # (3.8b) each named recording there: its subject's row (B11)
            P, j0, cl = sorted({dict(E)["sub"] for E, st in self.rc(s, case).items() if st is not None}), (self.cols[s].index(1) if 1 in self.cols[s] else None), self.classes.get((s, 1), [])
            lit = [L for L in P if j0 is not None and ("sub-" + L).encode() in self.lits.get((s, 1), ())]
            for L in lit:   # a literal label: its class's row (at most one, B11); no class (no readable row): no input
                j = next((i for i, c in enumerate(cl) if c[0] == "lit" and c[1] == ("sub-" + L).encode()), None)
                out.append(ge(lin((1, const(-1)))) if j is None else ge(lin((1, self.size(s, case, [t for t in self.types[s] if t[j0] == j])), (1, const(-1)))))
            if len(P) > len(lit):   # the others: as many rows whose label is no literal (any row when participant_id is not read)
                out.append(ge(lin((1, self.size(s, case, [t for t in self.types[s] if j0 is None or cl[t[j0]][0] == "oth"])), (1, const(len(lit) - len(P))))))
        for d in sorted(self.rs8):   # (3.9d) a region's participant rows: at most one (one order for both tasks) or two or more
            t0 = min(self.rs[d])
            out += [ge(lin((-1, self.size(d, case, g)), (1, const(1)))) if f == 1 else ge(lin((1, self.size(d, case, g)), (1, const(-2)))) for g, f in zip(self.rsreg[(d, t0)], case[("rs", d)][t0][3]) if f]
        for d in sorted(self.rs):   # (R1, R2) a region's state; a sum (a mean: S/N) of N values in one range lies in N times it
            q, fs = self.rsq.get(d, ("tr",))[0], {x.fn for x in self.rsagg if x.args[0].args[0].args[0].id == d}
            if d in self.rsm:   # (3.9a) per quantity i: no recording answering it ("z") or some, their sum within N_i times its range
                for t, (o, sts, *_) in sorted(case[("rs", d)].items()):
                    for r, st in enumerate(sts):
                        if st == "e":
                            out += [ge(lin((-1, self.rs_n(d, t, k, r)))) for k in self.rs_jk(d)]
                            continue
                        if self.kind[d] == "pt":
                            out.append(ge(lin((1, self.size(d, case, self.rsreg[(d, t)][r])), (1, const(-1)))))
                        for ci, c in enumerate(self.rs_evc(d)):   # each events-file class: none ("z") or some ("p")
                            N = lin(*[(1, self.rs_n(d, t, J, r)) for J in self.rs_jk(d) if self.rs_cls(d, J) == c])
                            out.append(ge(lin((-1, N))) if st[ci] == "z" else ge(lin((1, N), (1, const(-1)))))
                        for i, (qi, _) in enumerate(self.rsm[d]):
                            if qi == "volumes":   # N <= y <= (2^63 - 1) N over the 4-D images
                                N, Y = self.rs_nq(d, t, i, "ok", r), {self.rs_var(d, t, "y", r, i): 1}
                                out += [ge(lin((1, Y), (-1, N))), ge(lin((-1, Y), (MAX_DIM, N)))]
                        out += self.rs_couple(d, t, r) if st[0] == "p" else []
                continue
            lo, hi, op = (TRLO, TRHI, gt) if q == "tr" else (1, MAX_DIM, ge) if q == "volumes" else (0, None, ge)
            for t, (o, sts, *_) in sorted(case[("rs", d)].items()):
                for r, st in enumerate(sts):
                    N, Y, M = self.rs_n(d, t, "ok", r), {self.rs_var(d, t, "y", r): 1} if fs else {}, {self.rs_var(d, t, "m", r): 1} if fs else {}
                    if st == "e":
                        out += [ge(lin((-1, self.rs_n(d, t, k, r)))) for k in ("ok",) + RSBAD[q]]
                        continue
                    if self.kind[d] == "pt":   # its recordings' participants: rows of its types
                        out.append(ge(lin((1, self.size(d, case, self.rsreg[(d, t)][r])), (1, const(-1)))))
                    out += [ge(lin((-1, N)))] if st == "z" else [ge(lin((1, N), (1, const(-1))))] if st == "p" else []
                    if st == "p" and fs & {"sum", "mean"}:
                        out += [op(lin((1, Y), (-lo, N)))] + ([op(lin((-1, Y), (hi, N)))] if hi is not None else [])
                    if st == "p" and fs & {"min", "max"}:
                        out += [op(lin((1, M), (1, const(-lo))))] + ([op(lin((-1, M), (1, const(hi))))] if hi is not None else [])
                    if st == "p" and (d, t) in self.rs7:   # (3.9e) the sum and the max or min of one region's recordings (N read nowhere else)
                        f7, sp = self.rs7[(d, t)], case[("rs", d)][t][4]
                        if f7 == "max" and q == "volumes":   # some N >= 1 with m + N - 1 <= y <= N m exactly when y >= m
                            out += [ge(lin((1, Y), (-1, M)))]
                        elif f7 == "max":   # max 0: all 0; max >= 1: any y >= m (N = ceil(y / m))
                            out += [ge(lin((-1, M))), ge(lin((-1, Y)))] if sp[r] == 0 else [ge(lin((1, M), (1, const(-1)))), ge(lin((1, Y), (-1, M)))]
                        else:   # min, counts with no upper end: N = 1 gives y = m, N >= 2 any y >= 2m
                            out += [ge(lin((1, Y), (-1, M))), ge(lin((-1, Y), (1, M)))] if sp[r] == 0 else [ge(lin((1, Y), (-2, M)))]
        for s in self.tabs:
            c, N = case[s], {("n", s, t): 1 for t in self.types[s]}
            extra = len(c.types) - c.h
            for kp, sv in zip(c.kp, c.keys):
                Kf = self.size(s, case, [t for t in self.types[s] if self.keyed(s, t, kp)])
                out.append(ge(lin((1, Kf), (1, const(-2)))) if sv == "many" else ge(lin((-1, Kf), (1, const(sum(self.keyed(s, t, kp) for t in c.types))))))
            if c.h:
                out.append(ge(lin((1, N), (1, const(extra - c.pos[c.h - 1] + c.h)))))
            if c.h < len(c.pos):
                out.append(ge(lin((-1, N), (1, const(c.pos[c.h] - 1 - len(c.types))))))
            if not self.empty_ok[s]:
                out.append(ge(lin((1, N), (1, const(len(c.types) - 1)))))
            if self.kind[s] == "pt" and 1 in self.cols[s]:   # item 4: labels are distinct (B11): a literal's at most one row
                j0 = self.cols[s].index(1)
                for j, cl in enumerate(self.classes[(s, 1)]):
                    out += [ge(lin((-1, self.size(s, case, [t for t in self.types[s] if t[j0] == j])), (1, const(1))))] if cl[0] == "lit" else []
        X = case[None]
        for s, t in X.sums:   # a summed type of an interval class: no rows, or rows whose sum y lies in (n lo, n hi);
            n, b = {("n", s, t): 1}, X.pres.get((s, t))   # undecided (None): n lo <= y <= n hi, closed (item 8, solve)
            out += [ge(lin((-1, n)))] if b is False else [ge(lin((1, n), (1, const(-1))))] if b else []
            for k in self.cols[s]:
                c = self.cls(s, t, k)
                if self.agg.get((s, k)) in ("sum", "both") and c[0] == "iv":
                    y, (lo, hi), a = {("z", "y", s, t, k): 1}, c[1], gt if b else ge
                    if b is False:   # the forms of an undecided case may hold y: here it is 0
                        out += [ge(y), ge(lin((-1, y)))]
                        continue
                    out += ([a(lin((1, y), (-lo, n)))] if lo is not None else []) + ([a(lin((hi, n), (-1, y)))] if hi is not None else [])
        for s in self.tabs:   # item 6 (d): a named row's value in an aggregated column lies in its class, and in its piece
            for i, t in enumerate(case[s].types):
                for k in (k for k in self.cols[s] if (s, k) in self.agg and self.cls(s, t, k)[0] == "iv"):
                    z, (lo, hi) = {("z", "cell", s, i, k): 1}, self.cls(s, t, k)[1]
                    out += ([gt(lin((1, z), (1, const(-lo))))] if lo is not None else []) + ([gt(lin((-1, z), (1, const(hi))))] if hi is not None else [])
                    if (s, i, k) in X.npc:
                        r, p = self.rindex(s, k, self.cls(s, t, k)), X.npc[(s, i, k)]
                        ws = [{("z", "w", s, k, r, j): 1} for j in range(X.nw[(s, k, r)])]
                        if p % 2:
                            out += [ge(lin((1, z), (-1, ws[p // 2]))), ge(lin((-1, z), (1, ws[p // 2])))]
                        else:
                            out += ([gt(lin((1, z), (-1, ws[p // 2 - 1])))] if p else []) + ([gt(lin((1, ws[p // 2]), (-1, z)))] if p // 2 < len(ws) else [])
        for (s, k, r), m in X.nw.items():   # order statistics' values w_0 < ... < w_m-1 in an interval; its rows counted by piece
            lo, hi = self.regs[(s, k)][r][1:]
            ws = [{("z", "w", s, k, r, i): 1} for i in range(m)]
            out += ([gt(lin((1, ws[0]), (1, const(-lo))))] if lo is not None else []) + ([gt(lin((-1, ws[-1]), (1, const(hi))))] if hi is not None else [])
            out += [gt(lin((1, b), (-1, a))) for a, b in zip(ws, ws[1:])]
            for t in X.sel[(s, k)]:   # rows no order statistic of this column selects need no pieces
                if self.rindex(s, k, self.cls(s, t, k)) == r:
                    P, n = {("p", s, t, k, r, i): 1 for i in range(2 * m + 1)}, {("n", s, t): 1}
                    out += [ge(lin((1, P), (-1, n))), ge(lin((-1, P), (1, n)))]
        for (s, t, k, r, m), y, sig, vs in self.pieces(case):   # (e2) a summed type's sum is its pieces' sums; a piece between
            out += [ge(lin((1, y), (-1, sig))), ge(lin((-1, y), (1, sig)))]   # two ends has its mean strictly between them
            ws = [None] + [{("z", "w", s, k, r, j): 1} for j in range(m)] + [None]
            lo, hi = self.regs[(s, k)][r][1:]
            for j, v in enumerate(vs):
                a, b = ws[j] or (const(lo) if lo is not None else None), ws[j + 1] or (const(hi) if hi is not None else None)
                out += ([gt(lin((1, v), (-1, a)))] if a is not None else []) + ([gt(lin((1, b), (-1, v)))] if b is not None else [])
        return out

    def pieces(self, case):
        """(e2) The summed types of an ordered region of a column both summed and ordered, with order statistics in it:
        ((s, t, k, r, m), y, the sum of its pieces' sums, the means of its pieces between two ends) (SPEC-EXACT 3.5)."""
        X, out = case[None], []
        for (s, k, r), m in sorted(X.nw.items(), key=repr):
            if self.agg.get((s, k)) != "both":
                continue
            for t in sorted(X.sel.get((s, k), ()), key=repr):
                if self.rindex(s, k, self.cls(s, t, k)) == r and (s, t) in X.sums and X.pres.get((s, t)) is not False:
                    sig = {("z", "ps", s, t, k, r, i): 1 for i in range(2 * m + 1)}
                    out.append(((s, t, k, r, m), {("z", "y", s, t, k): 1}, sig, [{("z", "pv", s, t, k, r, j): 1} for j in range(m + 1)]))
        return out

    def piece_facts(self, case):
        """(H08, Opus 5.5 max2 review 08) Each piece PAtom's facts by content (mu, S, N, lo, hi, a0, key): a piece at w_j
        or between two ends sums to its mu times its rows, mu within its region's ends (3.5 e2); cert.prange_split
        trusts a PAtom not among the option's atoms only when it is one of these (search.piece_atoms builds them)."""
        out = set()
        for (s, t, k, r, m), _, _, _ in self.pieces(case):
            lo, hi = self.regs[(s, k)][r][1:]
            self.pay[0] += 2 * m + 1
            for i in range(2 * m + 1):
                mu = ("z", "w", s, k, r, i // 2) if i % 2 else ("z", "pv", s, t, k, r, i // 2)
                out.add((mu, ((("z", "ps", s, t, k, r, i), 1),), ((("p", s, t, k, r, i), 1),), lo, hi, 0, ("pk", s, t, k, r, i)))
        return out

    def total(self, s, case, types, k):
        """A sum over rows of these types (SPEC-EXACT 3.5): y for a type of an interval class with rows,
        n times the value for a point."""
        F = {}
        for t in types:
            c = self.cls(s, t, k)
            if c[0] != "iv":
                F = lin((1, F), (c[2], {("n", s, t): 1}))
            elif case[None].pres.get((s, t)) is not False:
                F = lin((1, F), (1, {("z", "y", s, t, k): 1}))
        for i, t in enumerate(case[s].types if s in self.tabs else ()):   # the named rows (item 6 (d))
            if t in types:
                c = self.cls(s, t, k)
                F = lin((1, F), (1, {("z", "cell", s, i, k): 1} if c[0] == "iv" else const(c[2])))
        return F

    def order_atoms(self, e, s, k, good, case):
        """The k-th smallest of the rows of these types is the statistic's value u (L4): fewer than k
        rows below u and at least k at or below it; max: none above; min: none below; median of 2m + 1
        rows: at most m below and at least m + 1 at or below."""
        _, _, r, q = case[None].ordv[id(e)]
        m = case[None].nw.get((s, k, r), 0)
        below, equal, above = {}, {}, {}
        for t in good:
            rt, n = self.rindex(s, k, self.cls(s, t, k)), ("n", s, t)
            if rt != r:
                (below if rt < r else above)[n] = 1
            elif m == 0:
                equal[n] = 1
            else:
                for i in range(2 * m + 1):
                    (below if i < 2 * q + 1 else equal if i == 2 * q + 1 else above)[("p", s, t, k, r, i)] = 1
        for i, t in enumerate(case[s].types):   # the named rows of these types (item 6 (d)): constants by region and piece
            if t in good:
                rt = self.rindex(s, k, self.cls(s, t, k))
                p = case[None].npc.get((s, i, k))
                side = (below if rt < r else above) if rt != r else equal if m == 0 else below if p < 2 * q + 1 else equal if p == 2 * q + 1 else above
                side[ONE] = side.get(ONE, 0) + 1
        one = ge(lin((1, equal), (1, const(-1))))
        if e.fn == "max":
            return [ge(lin((-1, above))), one]
        if e.fn == "min":
            return [ge(lin((-1, below))), one]
        j, mm = (const(e.args[2].v - 1), {}) if e.fn == "order" else ({}, {("m", id(e)): 1})
        return [ge(lin((-1, below), (1, j), (1, mm))), ge(lin((1, below), (1, equal), (-1, j), (-1, mm), (1, const(-1))))]

    def ustat(self, e, case):
        s, k, r, q = case[None].ordv[id(e)]
        reg = self.regs[(s, k)][r]
        return const(reg[1]) if reg[0] == "pt" else {("z", "w", s, k, r, q): 1}

    def ident(self, e, case):
        """e's value identity (SPEC 5.1) as a key; a row set as (slot, its types)."""
        f, a = e.fn, e.args
        if (f in AGG or f == "count") and a and isinstance(a[0], Call) and a[0].fn == "recordings":   # (R1) one set per task
            return ("RS", AGG.get(f, "Count"), a[0].args[0].args[0].id, a[0].args[1].v, rconds(a[0])) + tuple(x.v for x in a[1:])
        if f in AGG or f in VARF or f in ("rows", "count"):
            sh = self.shape(a[0])
            return (AGG.get(f, f if f in VARF else "Count"), sh[1], frozenset(self.selected(sh[1], sh[2]))) + tuple(x.v for x in a[1:])
        if f in RECF:   # (item 3) a recording's value: its dataset, recording and what it reads (kernel bids_id)
            return ("Rec", f, a[0].args[0].args[0].id, rent(a[0])) + tuple(x.v for x in a[1:])
        if f == "difference":
            return ("Difference", self.ident(a[0], case), self.ident(a[1], case))
        if f == "widen":
            return ("Widened", self.ident(a[0], case), cutoff(e, "tolerance"))
        if f in ("member", "item"):
            return ("JSON",) + jpath(e)
        if f in ("size", "dim", "pixdim"):
            return (f, a[0].id if f == "size" else a[0].args[0].id) + tuple(x.v for x in a[1:])
        c = a[0]
        if c.fn == "bytes":   # (shape 3) a byte range's number: its file and range (kernel: the Bytes sort)
            return ("Decimal", "raw", c.args[0].id, c.args[1].v, c.args[2].v)
        if c.fn == "header":
            return ("Header", table_slot(c.args[0]), c.args[1].v)
        if c.fn == "extra":   # item 4: the row and column it reads
            d, L = plab(c.args[0])
            return ("Decimal", d, case[d].keys[case[d].kp.index(((1, b"sub-" + L),))], c.args[1].v)
        sc = case[table_slot(c.args[0])]
        return ("Decimal", table_slot(c.args[0]), sc.pos.index(c.args[1].v) if isinstance(c.args[1], Int) else sc.keys[sc.kp.index(self.tkey(c))], c.args[2].v)

    def merge(self, case, T1, T2):
        """The terms of T1 - T2 as branches [(atoms, terms)]: two widened values are one symbol exactly
        when their identities are one, which for row sets is a count (SPEC 5.2, SPEC-EXACT 3.3)."""
        out = [([], dict(T1))]
        for b, cb in T2.items():
            nxt = []
            for A, T in out:
                cands = [(a, id_cond(a, b)) for a in T]
                cands = [(a, c) for a, c in cands if c is not None]
                for a, c in cands:
                    U = dict(T)
                    U[a] -= cb
                    nxt.append((A + [ge(lin((-1, self.idsize(case, x, p, q)))) for x, p, q in c], U))
                alts = [[]]
                for a, c in cands:
                    alts = [z + [ge(lin((1, self.idsize(case, x, p, q)), (1, const(-1))))] for z in alts for x, p, q in c]
                for z in alts:
                    U = dict(T)
                    U[b] = U.get(b, 0) - cb
                    nxt.append((A + z, U))
            out = nxt
        return [(A, {k: v for k, v in T.items() if v}) for A, T in out]

    def idsize(self, case, x, p, q):
        """(id_cond) What must be 0 for two identities to be one: the rows of the types only one of two selections holds;
        (G01, Opus 5.5 max review 01) for two recordings() sets of one dataset, the recordings only one holds (one task:
        those of the regions only one set takes; two tasks: every recording of both, so both empty)."""
        if x[0] != "rs":
            return self.size(x, case, set(p) ^ set(q))
        d, ta, tb = x[1], x[2].decode("ascii", "replace"), x[3].decode("ascii", "replace")   # ident keeps the task's bytes
        A, B = set(self.rsin[(d, ta, p)]), set(self.rsin[(d, tb, q)])
        regs = [(ta, g) for g in sorted(A ^ B)] if ta == tb else [(ta, g) for g in sorted(A)] + [(tb, g) for g in sorted(B)]
        return lin(*[(1, self.rs_n(d, t, k, g)) for t, g in regs for k in self.rs_jk(d)])

    # ---- values as branches (SPEC-EXACT 3.3) ---------------------------------------------------------

    def shape(self, e):
        """The kind of a part-T value ('table', 'sel', 'count', 'num', 'share', 'bytes', 'bool') and,
        for tables and selections, (slot, conditions); NotT when e is not one (SPEC-EXACT 2)."""
        if not isinstance(e, Call):
            raise NotT("leaf")
        f, a = e.fn, e.args
        if f in ("tsv", "csv"):
            return ("table", a[0].id, ())
        if f == "participants":
            return ("table", a[0].args[0].id, ())
        if f == "recordings":   # (R1)
            return ("rset", a[0].args[0].id, a[1].v.decode("ascii", "replace"), rconds(e))
        if f in AGG and a and isinstance(a[0], Call) and a[0].fn == "recordings":
            return ("num",)   # (R1) a mean too: one value (the statement's one set)
        if f == "count" and len(a) == 1 and not e.params and isinstance(a[0], Call) and a[0].fn == "recordings":
            return ("count",)
        if f in ("size", "dim", "volumes", "events", "trials"):
            return ("count",)
        if f in ("tr", "onset", "duration"):
            return ("num",)
        if f == "pixdim":
            return ("num",)
        if f == "bytes":
            return ("bytes",)
        if f in ("member", "item"):
            return ("jval",) + jpath(e)
        if f == "where":
            b = self.shape(a[0])
            if b[0] not in ("table", "sel") or len(a) < 2 or e.params:
                raise NotT("where")
            return ("sel", b[1], b[2] + self.wconds(e))
        if f in ("rows", "count") and len(a) == 1 and not e.params:
            b = self.shape(a[0])
            if b[0] != "table" and (f == "rows" or b[0] != "sel"):
                raise NotT(f)
            return ("count",)
        if f == "share" and len(a) in (1, 2) and not e.params:
            x = self.shape(a[0])
            y = self.shape(a[1]) if len(a) == 2 else ("table", x[1], ())
            if x[0] != "sel" or y[0] not in ("table", "sel") or y[1] != x[1] or any(c not in x[2] for c in y[2]):
                raise NotT("share")   # S003 / S006 on the real bytes
            return ("share",)
        if f == "difference" and any(isinstance(z, Call) and z.fn == "mean" and z.args and isinstance(z.args[0], Call) and z.args[0].fn == "recordings" for z in W.walk(e)):
            raise NotT("a mean of recordings inside a difference")
        if f == "difference" and len(a) == 2 and not e.params:
            x, y = (("num",) if z[0] in ("jval", "rnum") else z for z in (self.shape(a[0]), self.shape(a[1])))   # (e) a mean too
            if x[0] == y[0] == "vnum":
                return x   # two variances (item 5b; their units agree, else U001 on the real bytes, which confirmation meets)
            if x[0] != y[0] or x[0] not in ("count", "num"):
                raise NotT("difference")   # U001 on the real bytes
            return ("num",)
        if f in AGG or f in VARF:
            x = self.shape(a[0])
            if x[0] not in ("table", "sel"):
                raise NotT(f)
            return ("rnum",) if f == "mean" else ("vnum",) if f in VARF else ("num",)
        if f == "widen" and len(a) == 1:
            x = self.shape(a[0])
            x = ("num",) if x[0] == "jval" else x
            if x[0] not in ("num", "rnum", "vnum"):
                raise NotT(f)   # S007 on the real bytes
            return x
        if f in CMP and len(a) == 1:
            if self.shape(a[0])[0] not in ("count", "num", "rnum", "share", "jval", "vnum"):
                raise NotT("comparison")
            cutoff(e)
            return ("bool",)
        if f == "cell" and len(a) == 3 and not e.params and isinstance(a[2], Int) and a[2].v >= 1 and (isinstance(a[1], Call) or (isinstance(a[1], Int) and a[1].v >= 1)):
            table_slot(a[0])
            if isinstance(a[1], Call) and (a[1].fn != "key" or not key_of(a[1])):
                raise NotT("cell")
            return ("bytes",)
        if f == "header" and len(a) == 2 and not e.params and isinstance(a[1], Int) and a[1].v >= 1:
            table_slot(a[0])
            return ("bytes",)
        if f == "number" and len(a) == 1 and not e.params and self.shape(a[0])[0] == "bytes":
            return ("num",)
        if f == "extra":   # item 4 (checked in Model)
            return ("bytes",)
        raise NotT(f)

    def mu(self, r):
        """(e) A mean's result inside a difference as ("lin", mu), with its PAtom and the bounds its rows' classes give
        mu (a weighted mean of values in them: above the least lower end, strictly unless a point is at it; below
        the greatest upper end likewise; none past an unbounded end)."""
        if r[0] != "ratio":
            return r, []
        z = ("z", "mu", fz(r[1]), fz(r[2]))
        (k, ty), out = self.mcut[(z[2], z[3])], []
        lh, P = cends(list(ty.values())), PAtom(z, r[1], r[2], None, None, ty)
        P.k = k
        P.lo, P.hi, P.ends = lh[0][0], lh[1][0], []
        for sg, (L, o) in zip((1, -1), lh):   # above the lower end, below the upper one (mirrored)
            if L is not None:
                F = lin((sg, {z: 1}), (-sg * L, const(1)))
                out.append((gt if o else ge)(F))
                off = [v for v, c in ty.items() if c[0] == "iv" or c[2] != L]
                if not o and off:   # at a point class's end: strictly inside, or there with no rows of the others
                    P.ends.append(((z, sg), [[gt(F)], [ge(lin((-1, F)))] + [ge(lin((-1, {v: 1}))) for v in off]]))
        return ("lin", {z: 1}), [P] + out

    def br(self, e, case):
        """e's value in a case as branches [(atoms, result)]: the atoms (a conjunction over the row
        counts and named cell values) say when the result is e's outcome; results are ('V', code),
        ('sel', slot, conditions), ('lin', form), ('share', S, B), ('bytes', cell) and ('bool', b).
        The branches of one case exclude each other and cover it; a refusal comes from the first
        sub-value that refuses, in the evaluator's order (SPEC-EXACT 3.3)."""
        f, a = e.fn, e.args
        if f in ("tsv", "csv"):
            return [([], ("sel", a[0].id, ()))]
        if f == "participants":
            return [([], ("sel", a[0].args[0].id, ()))]
        if f == "size":
            return [([], ("lin", {("n", a[0].id, "size"): 1}))]
        if f == "recordings":   # (G07) K003 first (kernel.bold_labels), then its filter's refusals (R2)
            ok = [(A, r if r and r[0] in ("V", "X") else ("rset", a[0].args[0].id, a[1].v.decode("ascii", "replace"), rconds(e))) for A, r in (self.br(a[2], case) if len(a) == 3 else [([], None)])]
            return self.alike_br(a[0].args[0].id, a[1].v.decode("ascii", "replace"), case, ok)
        if (f in AGG or f == "count") and a and isinstance(a[0], Call) and a[0].fn == "recordings":
            return self.rs_br(f, e, case)
        if f in RECF:   # (2c, item 3) V004, then V008 (volumes) or V007, V002 (a row past the file's, no trial_type column)
            s, E = a[0].args[0].args[0].id, rent(a[0])
            st, I = self.rc(s, case)[E], self.rrows(s, E)
            r = (("V", "V004") if st is None else ("lin", {("z", "tr", s, E): 1}) if f == "tr" else (("V", "V008") if not st[0] else ("lin", {("n", s, "vol", E): 1})) if f == "volumes"
                 else ("V", "V007") if st[1] is None else ("lin", {("n", s, "ev", E): 1}) if f == "events" else (("V", "V002") if not st[2] else ("lin", {("n", s, "tt", E, a[1].v): 1})) if f == "trials"
                 else ("V", "V002") if st[1] <= I.index(a[1].v) else ("lin", {("z", f[:2], s, E, a[1].v): 1}))
            return [([], r)]
        if f == "bytes":   # V002 when the file is shorter than offset + length; else its own bytes there
            z = lin((1, {("n", a[0].id, "size"): 1}), (1, const(-a[1].v - a[2].v)))
            return [([gt(lin((-1, z)))], ("V", "V002")), ([ge(z)], ("bytes", (a[0].id, "raw", (a[1].v, a[2].v))))]
        if f == "dim":
            s, k = a[0].args[0].id, a[1].v
            return [([], ("V", "V008") if k > case[s] else ("lin", {("n", s, "dim", k): 1}))]
        if f == "pixdim":   # V008 below 4 dimensions; I005 without a time unit (or NaN, the same answer); else f·pixdim[4]
            c = case[a[0].args[0].id]
            return [([], ("V", "V008") if c < 4 else ("V", "I005") if not c.unit else ("lin", {("z", "pix", a[0].args[0].id): R.TIME_UNITS[c.unit]}))]
        if f in ("member", "item"):
            s, path = jpath(e)
            return [([], self.jbr(s, path, case))]
        out = []
        if f == "where":
            for A, r in self.br(a[0], case):
                if r[0] in ("V", "X"):
                    out.append((A, r))
                    continue
                s, conds = r[1], r[2] + self.wconds(e)
                G = self.size(s, case, self.undecided(s, conds))
                ks = sorted({c[1] for c in conds if c[0] in ("eq", "ne")})
                for B, bad in self.scope(s, case, [(k, {c[2] for c in conds if c[0] in ("eq", "ne") and c[1] == k}) for k in ks]):
                    out += [(A + B, ("X", "K002"))] if bad else [(A + B + [ge(lin((1, G), (1, const(-1))))], ("V", "V005")), (A + B + [ge(lin((-1, G)))], ("sel", s, conds))]
            return prune(out)
        if f in ("rows", "count"):
            return [(A, r if r[0] in ("V", "X") else ("lin", self.size(r[1], case, self.selected(r[1], r[2])))) for A, r in self.br(a[0], case)]
        if f == "share":
            for A, x in self.br(a[0], case):
                for A2, y in (self.br(a[1], case) if len(a) == 2 else [([], ("sel", x[1], ()))]) if x[0] not in ("V", "X") else [([], x)]:
                    if y[0] in ("V", "X"):
                        out.append((A + A2, y))
                        continue
                    S, B = (self.size(z[1], case, self.selected(z[1], z[2])) for z in (x, y))
                    out += [(A + A2 + [ge(lin((-1, B)))], ("V", "V003")), (A + A2 + [ge(lin((1, B), (1, const(-1))))], ("ratio", S, B))]
            return prune(out)
        if f == "difference":
            for A, x in self.br(a[0], case):
                x = nonnum(x)
                for A2, y in self.br(a[1], case) if x[0] not in ("V", "X") else [([], x)]:
                    y = nonnum(y)
                    if y[0] in ("V", "X"):
                        out.append((A + A2, y))
                        continue
                    if x[0] == y[0] == "vans":   # item 5b: its value is decided in Decide.d_hit
                        out.append((A + A2, ("dvans", x, y)))
                        continue
                    if {unaff(x)[0][0], unaff(y)[0][0]} & {"vans", "dvans", "nvans"}:   # the variance shape: Decide.n_hit
                        out.append((A + A2, ("nvans",)))
                        continue
                    (bx, Tx), (by, Ty) = unaff(x), unaff(y)
                    (bx, P1), (by, P2) = self.mu(bx), self.mu(by)
                    F, A2 = ("lin", lin((1, bx[1]), (-1, by[1]))), A2 + P1 + P2
                    out += [(A + A2 + A3, ("aff", F, T)) for A3, T in self.merge(case, Tx, Ty)] if Tx or Ty else [(A + A2, F)]
            return prune(out)
        if f == "widen":
            q, key = cutoff(e, "tolerance"), None
            for A, x in self.br(a[0], case):
                x = nonnum(x)
                if x[0] in ("V", "X"):
                    out.append((A, x))
                    continue
                key = key or self.ident(a[0], case)
                b, T = unaff(x)
                out.append((A, ("aff", b, {**T, key: T.get(key, 0) + q})))
            return out
        if f in CMP and (vchain(a[0]) or dchain(a[0]) or nchain(a[0])):
            return self.br(a[0], case)   # its answers: 3.7 (holds and fails decided in Decide.w1_var)
        if f in CMP:
            c = cutoff(e)
            for A, x in self.br(a[0], case):
                x = nonnum(x)
                if x[0] in ("V", "X"):
                    out.append((A, x))
                    continue
                b, T = unaff(x)
                w = sum(abs(v) for v in T.values())
                lo, hi = (lin((1, b[1]), (-(c + o), const(1) if b[0] == "lin" else b[2])) for o in (w, -w))   # sign of lo - c, hi - c
                yes, no = {"exceeds": (gt(lo), natom(gt(hi))), "below": (natom(ge(hi)), ge(lo)),
                           "atleast": (ge(lo), natom(ge(hi))), "atmost": (natom(gt(hi)), gt(lo))}[f]
                out += [(A + [yes], ("bool", True)), (A + [no], ("bool", False))] + ([(A + [natom(yes), natom(no)], ("V", "V006"))] if w else [])
            return prune(out)
        if f in VARF:   # V005, then V003 below 1 + ddof rows, else an answer whose value 3.7 decides
            k, d = a[1].v, VARF[f]
            for A, x in self.br(a[0], case):
                if x[0] in ("V", "X"):
                    out.append((A, x))
                    continue
                s = x[1]
                sel = self.selected(s, x[2])
                good = [t for t in sel if self.cls(s, t, k)[2] is not None and (s not in self.tn or case[s].wc == 1 or not tsvof(a[0]))]   # (3.13g) as 3.13c
                G, N = self.size(s, case, [t for t in sel if t not in good]), self.size(s, case, good)
                out += [(A + [ge(lin((1, G), (1, const(-1))))], ("V", "V005")), (A + [ge(lin((-1, G))), ge(lin((-1, N), (1, const(d))))], ("V", "V003")),
                        (A + [ge(lin((-1, G))), ge(lin((1, N), (1, const(-d - 1))))], ("vans", s, k, tuple(good), d, tuple(sel)))]
            return prune(out)
        if f in AGG:
            k = a[1].v
            for A, x in self.br(a[0], case):
                if x[0] in ("V", "X"):
                    out.append((A, x))
                    continue
                s = x[1]
                sel = self.selected(s, x[2])
                good = [t for t in sel if self.cls(s, t, k)[2] is not None and (s not in self.tn or case[s].wc == 1 or not tsvof(a[0]))]   # (3.13c) a tsv() line of Wc >= 2 cells: no decimal
                G = self.size(s, case, [t for t in sel if t not in good])   # a selected cell that is not a decimal: V005 (SPEC 6.3)
                out.append((A + [ge(lin((1, G), (1, const(-1))))], ("V", "V005")))
                A, N = A + [ge(lin((-1, G)))], self.size(s, case, good)
                if f == "sum":
                    out.append((A, ("lin", self.total(s, case, good, k))))
                    continue
                low = a[2].v - 1 if f == "order" else 0
                out.append((A + [ge(lin((-1, N), (1, const(low))))], ("V", "V003")))
                A = A + [ge(lin((1, N), (1, const(-low - 1))))]
                if f == "mean":
                    S = self.total(s, case, good, k)
                    self.mcut[(fz(S), fz(N))] = ((s, k), {("n", s, t): self.cls(s, t, k) for t in good})   # (e) its rows' classes bound mu
                    out.append((A, ("ratio", S, N)))
                    continue
                if f == "median":
                    m = {("m", id(e)): 1}
                    out.append((A + [ge(lin((1, N), (-2, m))), ge(lin((-1, N), (2, m)))], ("V", "V009")))
                    A = A + [ge(lin((1, N), (-2, m), (1, const(-1)))), ge(lin((-1, N), (2, m), (1, const(1))))]
                out.append((A + self.order_atoms(e, s, k, good, case), ("lin", self.ustat(e, case))))
            return prune(out)
        if f == "cell":
            s, c = table_slot(a[0]), case[table_slot(a[0])]
            if isinstance(a[1], Int):
                j = c.pos.index(a[1].v)
                k = (1 if c.wc == 1 else 0) if s in self.tn and isinstance(a[0], Call) and a[0].fn == "tsv" else a[2].v   # (3.13b) the tsv() cell: in Wc = 1 csv column 1's cell, else the line (column 0)
                return [([], ("V", "V002") if j >= c.h else ("bytes", (s, j, k)))]
            sv, kc = c.keys[c.kp.index(self.tkey(e))], ((1 if c.wc == 1 else 0) if s in self.tn and a[0].fn == "tsv" else a[2].v)   # (3.13e) as 3.13b
            return [(B, ("X", "K002") if bad else ("V", "V004") if sv in ("none", "many") else ("bytes", (s, sv, kc))) for B, bad in self.scope(s, case, [(k, {b}) for k, b in self.tkey(e)])]
        if f == "header":   # (3.13d) tsv(f)'s one name: in Wc = 1 csv name 1, else the names joined (k = 0)
            s = table_slot(a[0])
            return [([], ("bytes", (s, "h", (1 if case[s].wc == 1 else 0) if s in self.tn and isinstance(a[0], Call) and a[0].fn == "tsv" else a[1].v)))]
        if f == "extra":   # item 4: V004 when no row is labelled sub-L (labels are distinct, B11), else its cell
            d, L = plab(a[0])
            sv = case[d].keys[case[d].kp.index(((1, b"sub-" + L),))]
            return [([], ("V", "V004") if sv in ("none", "many") else ("bytes", (d, sv, a[1].v)))]
        if f == "number":
            for A, x in self.br(a[0], case):
                if x[0] in ("V", "X"):
                    out.append((A, x))
                    continue
                s, i, k = x[1]
                if i == "raw":   # (shape 3) its class in the case: V005, or the number z of its n bytes (3.11)
                    cl = case[s][self.rreg[s].index(k)]
                    out.append((A, ("V", "V005") if cl == "nan" else ("lin", {("z", "raw", s) + k: 1})))
                    continue
                if k == 0 and s in self.tn:   # (3.13b, d) a line or header of Wc >= 2 cells holds a comma: no decimal
                    out.append((A, ("V", "V005")))
                    continue
                cl = case[s].hdr[k] if i == "h" else self.cls(s, case[s].types[i], k)
                if cl[0] == "oth" or (cl[0] == "lit" and cl[2] is None):
                    out.append((A, ("V", "V005")))
                elif cl[0] != "iv":
                    out.append((A, ("lin", const(cl[2]))))
                else:
                    z = ("z", "cell", s, i, k)
                    lo, hi = cl[1]
                    out.append((A + ([gt(lin((1, {z: 1}), (-lo, const(1))))] if lo is not None else []) + ([gt(lin((-1, {z: 1}), (1, const(hi))))] if hi is not None else []), ("lin", {z: 1})))
            return out
        raise NotT(f)

    def rrows(self, s, E):
        """(item 3) the events rows a recording's onset() and duration() name, sorted."""
        return sorted({y.args[1].v for y in self.rval if y.fn in ("onset", "duration") and (y.args[0].args[0].args[0].id, rent(y.args[0])) == (s, E)})

    def rtt(self, s, E):
        """(item 3) a recording's trials() counts, one per trial type."""
        return sorted({("n", s, "tt", E, y.args[1].v) for y in self.rval if y.fn == "trials" and (y.args[0].args[0].args[0].id, rent(y.args[0])) == (s, E)})

    def evlb(self, s, E, case, role=None):
        """(G04c, Opus 5.5 max review 04 c) slot s's named recording E: its events file's least text as (form, constant),
        or None without one (V007). The read-limit pass's certificate writes exactly it (build.rec_dataset): the header
        (with a trial_type column 26 bytes, else 15) and per row "0<TAB>1" and a line feed, with the column a TAB and the
        read type's bytes (5 + them) or a one-letter type (6), the last line feed dropped. Without events() read, the
        rows are at least the read types' (else the last named row): a lower bound, so only a sound refusal rests on it."""
        st = self.rc(s, case).get(E)
        if st is None or st[1] is None:
            return None
        T, ev = self.rtt(s, E) if st[2] else [], "events" in self.rread.get((s, E), ())
        w = 6 if T else 4
        L = {v: 5 + len(v[4]) - (w if ev else 0) for v in T}
        if ev:
            L[("n", s, "ev", E)] = w
        I = self.rrows(s, E)
        if role is not None:   # (H07) evmem: what each variable counts, with the file's columns
            role.update({v: ("delta" if ev else "row", 3 if T else 2) for v in T})
            role[("n", s, "ev", E)] = ("row", 3 if T else 2)
            role[None] = [("file", 3 if T else 2, 1)] + ([("row", 2, I[st[1] - 1])] if not ev and not T and st[1] else [])
        return L, (25 if T else 14) + (w * I[st[1] - 1] if not ev and not T and st[1] else 0)

    def evmem(self, ks, case):
        """(H07, Opus 5.5 max2 review 07) the accounted memory of the events files a statement reads (kernel.bids_tsv keeps
        each parsed once a program: its text + 64 and kernel._table_size) at the least text the certificate writes (evlb,
        rs_evlb): 2 x the text, and 193 + 79 c a file and 64 + 79 c a row of c columns (a cell 80 and its characters, a
        row's bytes less c); a read type beside events() only its bytes. Regions shared by two filters once. (form, const)."""
        F, m = {}, 0
        for k in ks:
            role = {}
            L = self.evlb(k[1], k[2], case, role) if k[0] == "rec" else self.rs_evlb(k[1], k[2], k[3], case, role)
            if not L:
                continue
            m += 2 * L[1] + sum(n * (193 + 79 * c if r == "file" else 64 + 79 * c) for r, c, n in role.get(None, []))
            for v, a in L[0].items():
                r, c = role.get(v, ("delta", 2))
                F[v] = 2 * a + (193 + 79 * c if r == "file" else 64 + 79 * c if r == "row" else 0)
        return F, m

    def rs_evok(self, d, t, case):
        """(G04c) recordings(d, t)'s events files as the read-limit pass's certificate writes them (build.rs_dataset, the
        last line feed dropped), for one quantity, events or trials of one type, read by sums and means (each region's
        rows split evenly over its answering recordings), a max (one at m rows, the others none) or a min (all at m);
        a sum beside a max or min (3.9e) by its sum, a necessary bound (the files' rows are the region's, unevenly):
        (header less one, a row's bytes, the aggregates); else None (two quantities: Model.rs_evm)."""
        q, fs = self.rsq.get(d, (None,))[0], {x.fn for x in self.rsagg if x.args[0].args[0].args[0].id == d}
        if q not in ("events", "trials") or t not in case[("rs", d)]:
            return None
        return (25, 5 + len(self.rsq[d][1]), fs) if q == "trials" else (14, 4, fs)

    def rs_evlb(self, d, t, c, case, role=None):
        """(G04c) the events files an aggregate of recordings(d, t) with filter c reads (rs_evok): per answering
        recording the header and its rows, per recording without the type's column (trials: "nocol") its 14-byte header;
        (form, constant), or None. A min's N files of m rows are N * (h + w m), not linear: h N + w m, a lower bound."""
        if d in self.rsm and (d, t) not in self.rs7 and t in case[("rs", d)]:
            return self.rs_evm(d, t, c, case, role)[0]
        k = self.rs_evok(d, t, case)
        if k is None:
            return None
        (h, w, fs), sts, L = k, case[("rs", d)][t][1], {}
        cc = 3 if self.rsq[d][0] == "trials" else 2
        role = {} if role is None else role
        for r in self.rsin[(d, t, c)]:
            if sts[r] != "e":
                L[("n", d, "rs", t, "ok", r)], role[("n", d, "rs", t, "ok", r)] = h, ("file", cc)
                if self.rsq[d][0] == "trials":
                    L[("n", d, "rs", t, "nocol", r)], role[("n", d, "rs", t, "nocol", r)] = 14, ("file", 2)
            if sts[r] == "p":
                v = self.rs_var(d, t, "y" if fs & {"sum", "mean"} else "m", r)
                L[v], role[v] = w, ("row", cc)
        return L, 0

    def rs_evm(self, d, t, c, case, role=None):
        """(G04c) two or more quantities of recordings(d, t) with filter c (sums, 3.9a, 3.9b): per region and events-file
        class, the files' headers and rows (a read type's 5 + its bytes, the others' 6 with the trial_type column, 4
        without; the last line feed dropped) as (form, constant), a lower bound of the text the statement reads, and
        per region and class the files' rows within MAX_TEXT_FILE each in all (rows <= (MAX_TEXT_FILE - h) N). Only
        necessary: the rows are split over the files in whole rows of unequal sizes, so near the limit R013 stays."""
        sts, L, A = case[("rs", d)][t][1], {}, []
        ie = next((i for i, (q, _) in enumerate(self.rsm[d]) if q == "events"), None)
        lits = [(i, lit) for i, (q, lit) in enumerate(self.rsm[d]) if q == "trials"]
        for r in self.rsin[(d, t, c)]:
            if sts[r] == "e":
                continue
            for ci, cl in enumerate(self.rs_evc(d)):
                h = 25 if cl == "ok" and lits else 14
                N = {v: 1 for J in self.rs_jk(d) if self.rs_cls(d, J) == cl for v in self.rs_n(d, t, J, r)}
                R1 = {}
                if sts[r][ci] == "p" and cl == "ok" and lits:
                    R1 = {self.rs_var(d, t, "y", r, (i, "ok")): 5 + len(lit) - (6 if ie is not None else 0) for i, lit in lits}
                    R1.update({self.rs_var(d, t, "y", r, (ie, "ok")): 6} if ie is not None else {})
                elif sts[r][ci] == "p" and ie is not None:
                    R1 = {self.rs_var(d, t, "y", r, (ie, cl)): 4}
                L.update({v: h for v in N})
                L.update(R1)
                if role is not None:   # (H07) evmem: files, rows (a read type beside events(): its own bytes only)
                    role.update({v: ("file", 3 if h == 25 else 2) for v in N})
                    role.update({v: ("delta" if ie is not None and v[5][0] != ie else "row", 3 if h == 25 else 2) for v in R1})
                A += [ge(lin(*[(R.MAX_TEXT_FILE - h, {v: 1}) for v in N], *[(-a, {v: 1}) for v, a in sorted(R1.items(), key=repr)]))] if R1 else []
        return (L, 0), A

    def rs_n(self, s, t, k, r=0):
        return {("n", s, "rs", t, k, r): 1}

    def rsqs(self, s):
        """The quantities read of rs slot s's recordings."""
        return {q for q, _ in self.rsm[s]} if s in self.rsm else {self.rsq.get(s, ("tr",))[0]}

    def rs_jk(self, s):
        """(R1) a recording's kinds: answering ("ok") or one refusing kind per quantity; (3.9a, 3.9b) with two or more
        quantities, a kind per pair (image: ok/3d) x (events file: ok/noev, with trials also nocol), written as each
        quantity's kind (events: ok unless noev; trials: the events file's; volumes: the image's)."""
        if s not in self.rsm:
            return ("ok",) + RSBAD[self.rsq.get(s, ("tr",))[0]]
        qs = self.rsqs(s)
        img, ev = ("ok", "3d") if "volumes" in qs else ("ok",), ("ok", "noev", "nocol") if "trials" in qs else ("ok", "noev")
        kq = {"volumes": lambda a, b: a, "events": lambda a, b: "noev" if b == "noev" else "ok", "trials": lambda a, b: b}
        return tuple(tuple(kq[q](a, b) for q, _ in self.rsm[s]) for a in img for b in ev)

    def rs_evc(self, s):
        """(3.9b) the events-file classes of answering recordings that hold values: with a trial_type column ("ok") and,
        when events and trials are both read, without one ("nocol": events answers, trials refuses)."""
        return ("ok", "nocol") if {"events", "trials"} <= self.rsqs(s) else ("ok",)

    def rs_cls(self, s, J):
        """(3.9b) a kind's events-file value: a trials position's kind, else the events position's."""
        return next((J[i] for i, (q, _) in enumerate(self.rsm[s]) if q == "trials"), None) or next(J[i] for i, (q, _) in enumerate(self.rsm[s]) if q == "events")

    def rs_couple(self, d, t, r):
        """(3.9b) on the recordings whose events file has a trial_type column: events >= the read types' trials."""
        E = [i for i, (q, _) in enumerate(self.rsm[d]) if q == "events"]
        if not E or "trials" not in self.rsqs(d):
            return []
        return [ge(lin((1, {self.rs_var(d, t, "y", r, (E[0], "ok")): 1}), *[(-1, {self.rs_var(d, t, "y", r, (i, "ok")): 1}) for i, (q, _) in enumerate(self.rsm[d]) if q == "trials"]))]

    def rs_ny(self, s, t, i, r, st):
        """(3.9b) quantity i's sum in region r: its variables over the classes answering it whose state is p (volumes: one)."""
        q = self.rsm[s][i][0]
        if q == "volumes":
            return {self.rs_var(s, t, "y", r, i): 1}
        return {self.rs_var(s, t, "y", r, (i, c)): 1 for ci, c in enumerate(self.rs_evc(s)) if st[ci] == "p" and (q == "events" or c == "ok")}

    def rs_nq(self, s, t, i, k, r):
        """(3.9a) the recordings of region r whose value of quantity i is of kind k: the sum over the pairs."""
        return lin(*[(1, self.rs_n(s, t, J, r)) for J in self.rs_jk(s) if J[i] == k])

    def alike_br(self, d, t, case, ok):
        """(G07, Opus 5.5 max review 07) recordings(d, t)'s branches: when the statement reads tasks of d that look like
        t, a dataset holding recordings of two of them refuses K003 (each pair i < j of the group first present: those
        before absent); else (none or one present) the branches ok."""
        G = [u for u in sorted(self.rs[d]) if skeleton(u) == skeleton(t)]
        if len(G) < 2:
            return ok
        N = {u: lin(*[(1, self.rs_n(d, u, k, r)) for r in range(len(case[("rs", d)][u][1])) for k in self.rs_jk(d)]) for u in G}
        no = lambda u: ge(lin((-1, N[u])))   # noqa: E731
        yes = lambda u: ge(lin((1, N[u]), (1, const(-1))))   # noqa: E731
        out = [([no(u) for u in G[:i]] + [yes(G[i])] + [no(u) for u in G[i + 1:j]] + [yes(G[j])], ("X", "K003")) for i in range(len(G)) for j in range(i + 1, len(G))]
        for B in [[no(u) for u in G]] + [[no(u) for u in G if u != v] + [yes(v)] for v in G]:
            out += [(B + A, r) for A, r in ok]
        return prune(out)

    def rs_br(self, f, e, case):
        """(R1) count(rs): its regions' recordings; sum/mean/min/max(rs, q): the kernel reads each recording's value in sort
        order, so the first recording whose value refuses gives the refusal (3.9c: the case's choice in its order), then V003 for an empty set
        (not sum); else the answering regions' sum (0 with none), their mean S/N, or the min or max of their one values
        (the region holding it: ties to the first) (SPEC-EXACT 3.9)."""
        out = []
        for A, x in self.br(e.args[0], case):
            if x[0] in ("V", "X"):
                out.append((A, x))
                continue
            d, t, regs, q = x[1], x[2], self.rsin[x[1:]], self.rsq.get(x[1], ("tr",))[0]
            if f == "count":
                out.append((A, ("lin", lin(*[(1, self.rs_n(d, t, k, r)) for r in regs for k in self.rs_jk(d)]))))
                continue
            o, sts, ch, *_ = case[("rs", d)][t]
            if d in self.rsm:   # (3.9a) a sum of quantity i: the first recording (the case's order) whose kind i refuses, else the answering regions' sum
                i = self.rsm[d].index((e.args[1].v.decode(), e.args[2].v if len(e.args) == 3 else None))
                sq, prev = self.rs_seq(d, o, (tuple(regs), i)), A
                j = dict(ch)[(tuple(regs), i)]   # (3.9c) the case's branch: pair j there, those before it none
                prev = prev + [ge(lin((-1, self.rs_nq(d, t, i, k, r)))) for r, k in sq[:j]]
                if j < len(sq):
                    out.append((prev + [ge(lin((1, self.rs_nq(d, t, i, sq[j][1], sq[j][0])), (1, const(-1))))], ("V", RSCODE[sq[j][1]])))
                else:
                    out.append((prev, ("lin", lin(*[(1, self.rs_ny(d, t, i, r, sts[r])) for r in regs if sts[r] != "e"]))))
                continue
            sq = self.rs_seq(d, o, (tuple(regs), None))
            j = dict(ch)[(tuple(regs), None)]   # (3.9c) as above
            prev = A + [ge(lin((-1, self.rs_n(d, t, k, r)))) for r, k in sq[:j]]
            if j < len(sq):
                out.append((prev + [ge(lin((1, self.rs_n(d, t, sq[j][1], sq[j][0])), (1, const(-1))))], ("V", RSCODE[sq[j][1]])))
                continue
            P = [r for r in regs if sts[r] == "p"]
            Y, M = {self.rs_var(d, t, "y", r): 1 for r in P}, [self.rs_var(d, t, "m", r) for r in P]
            if not P or f == "sum":
                out.append((prev, ("lin", Y) if f == "sum" else ("V", "V003")))
            elif f == "mean":
                out.append((prev, ("ratio", Y, lin(*[(1, self.rs_n(d, t, "ok", r)) for r in P]))))
            else:
                g = (lambda u, v: lin((1, {v: 1}), (-1, {u: 1}))) if f == "min" else (lambda u, v: lin((1, {u: 1}), (-1, {v: 1})))   # noqa: E731
                out += [(prev + [(gt if j < i else ge)(g(m, M[j])) for j in range(len(P)) if j != i], ("lin", {m: 1})) for i, m in enumerate(M)]
        return out

    def recd(self, e, case):
        """(R1) whether e's number is recorded (read from a BIDS value; kernel Num.recorded) in this case: a recording's
        tr or onset, a mean, min or max of tr over recordings (an answer has one), a sum of tr when its set's recordings
        answer (case: else 0, not recorded); a difference is recorded when either part is."""
        for x in W.walk(e):
            if isinstance(x, Call) and x.fn in ("tr", "onset", "duration") and x.args and isinstance(x.args[0], Call) and x.args[0].fn == "recording":
                return True
            if isinstance(x, Call) and x.fn in AGG and x.args and isinstance(x.args[0], Call) and x.args[0].fn == "recordings" and len(x.args) > 1 and x.args[1] == Str(b"tr"):
                d, t = x.args[0].args[0].args[0].id, x.args[0].args[1].v.decode("ascii", "replace")
                if x.fn != "sum" or any(case[("rs", d)][t][1][r] == "p" for r in self.rsin[(d, t, rconds(x.args[0]))]):
                    return True
        return False

    def rs_var(self, s, t, w, r=0, i=None):
        """(R1) a region's sum (w = "y") or its one value (w = "m"): a whole number ("n") or a rational ("z"); (3.9a) of
        quantity i (counts only: tr is not read beside another quantity)."""
        if i is not None:
            return ("n", s, "rs" + w, t, r, i)
        return ("n", s, "rs" + w, t, r) if self.rsq[s][0] != "tr" else ("z", "rs", s, w, t, r)

    def scope(self, s, case, groups):
        """(K002, principle 10.3; kernel.key_column_scope) where() and key() refuse, no answer, when two distinct strings
        among a column's literals there and its cells look alike: for each (column, literals), a literal class that looks
        like one of them and is not one refuses when it has a row; other literal classes of one skeleton refuse when two
        of them have rows. Cases [(atoms, refuses)] that exclude each other and cover the case."""
        sk = lambda b: skeleton(b.decode("utf-8"))   # noqa: E731
        out = [([], False)]
        for k, L in groups:
            SL, j0 = {sk(b) for b in L}, self.cix(s, k)
            cl = [(j, c[1]) for j, c in enumerate(self.classes[(s, k)]) if c[0] == "lit" and c[1] not in L]
            n = lambda js: self.size(s, case, [t for t in self.types[s] if t[j0] in js])   # noqa: E731
            bad, gs = [j for j, b in cl if sk(b) in SL], {}
            for j, b in cl:
                gs.setdefault(sk(b), []).append(j) if sk(b) not in SL else None
            for js in [bad] + [js for js in gs.values() if len(js) > 1]:
                pats = [(1,)] if js is bad else itertools.product((0, 1), repeat=len(js))
                pats = [[(js, 1)]] if js is bad else [list(zip(([j] for j in js), p)) for p in pats]
                nxt = [(A, r) for A, r in out if r]
                for A, r in (x for x in out if not x[1]):
                    if js is bad:
                        nxt += [(A + [ge(lin((1, n(js)), (1, const(-1))))], True), (A + [ge(lin((-1, n(js))))], False)] if js else [(A, False)]
                        continue
                    for p in pats:
                        nxt.append((A + [ge(lin((1, n(q)), (1, const(-1)))) if on else ge(lin((-1, n(q)))) for q, on in p], sum(on for _, on in p) >= 2))
                self.steps += len(nxt)
                out = nxt
        return out

    def literal(self, case, cell):
        """The cell's bytes when its class is a literal, else None (its bytes are its own spelling; a file's
        bytes and a JSON string are free too)."""
        s, i, k = cell
        if i in ("raw", "json"):
            return None
        if k == 0 and i == "h" and s in self.tn:   # (3.13d) a header of Wc >= 2 names: name 2 is never read, so free
            return None
        if k == 0 and i != "h" and s in self.tn:   # (3.13b) a line of Wc >= 2 cells: its literal, or the read literals of all its cells joined
            t, W0 = case[s].types[i], case[s].wc if case[s].wc != "o" else self.wo[s]
            if self.cls(s, t, 0)[0] == "lit":
                return self.cls(s, t, 0)[1]
            ok = all(k2 in self.cols[s] and self.cls(s, t, k2)[0] == "lit" for k2 in range(1, W0 + 1))
            return b",".join(self.cls(s, t, k2)[1] for k2 in range(1, W0 + 1)) if ok else None
        cl = case[s].hdr[k] if i == "h" else self.cls(s, case[s].types[i], k)
        return cl[1] if cl[0] == "lit" else None

    # ---- systems ------------------------------------------------------------------------------------

    # ---- the model's disjunctions (cert.py): cases that hold together on every input, stated by the model -------------

    def base(self, case):
        """(cert.py) The model's atoms of a case: what every system of it starts with (one_solve1)."""
        return self.case_atoms(case) + self.part_atoms(case)

    def tail(self, case, atoms, more):
        """(cert.py) The model's facts a leaf's system ends with: equal means of the same rows (same_means)."""
        return self.same_means(case, [A for A in atoms if isinstance(A, PAtom)], atoms + more, [0])

    def past_limit(self, case, atoms, x):
        """(G02b) Whether x is a point of the option (case, atoms) past the read limit, by the model alone (no input past
        the limit can be built and read): every atom of its system without the limit (the case's, the option's, the
        model's facts) holds at x, each natural variable a natural, each mean's S = mu·N; and an atom the limit adds fails."""
        rb = self.rb
        try:
            self.rb = False
            sys0 = self.base(case) + list(atoms) + self.tail(case, atoms, [])
            self.rb = True
            ks = {C.key([A]) for A in sys0}
            lim = [A for A in self.base(case) if C.key([A]) not in ks]
        finally:
            self.rb = rb
        pay(sum(len(F) + 1 for F, _ in sys0 + lim))
        nat = all(v == ONE or v[0] == "z" or Fraction(x.get(v, 0)).denominator == 1 and x.get(v, 0) >= 0 for F, _ in sys0 for v in F)
        means = all(value(P.S, x) == x.get(P.mu, 0) * value(P.N, x) for P in atoms if isinstance(P, PAtom))
        return nat and means and all(holds(A, x) for A in sys0) and any(not holds(A, x) for A in lim)

    def same_case(self, a, b):
        """(cert.py) Two cases the same: each slot's case the same object, the aggregates' part equal field by field."""
        if a is b:
            return True
        if a.keys() != b.keys() or any(a[k] is not b[k] for k in a if k is not None):
            return False
        X, Y = a.get(None), b.get(None)
        return X is Y or X is not None and Y is not None and all(getattr(X, f) == getattr(Y, f) for f in ("sums", "pres", "ordv", "nw", "sel", "npc"))

    def nests(self, Ps):
        """(e) Each mean against another whose rows hold its rows (nest), and each mean at a point class's end (mu)."""
        return [(("nest", P.mu, Q.mu), b) for P in Ps for Q in Ps for b in [nest(P, Q)] if b] + [e for P in Ps for e in P.ends]

    def presence(self, c, bad):
        """(item 8) A summed type of undecided presence: the case where it has rows, and the one where it has none."""
        X = c[None]
        return [{**c, None: Extra(X.sums, {**X.pres, bad: b}, X.ordv, X.nw, X.sel, X.npc)} for b in (True, False)]

    def band_cases(self, z, lo):
        """(call 2; SPEC-EXACT 3.1) A readable number z: in the band of R holding the number after lo (a multiple g·J of
        its step, J from a to b), or at or below the number before the band, or at or above the one after it (no
        readable number lies between)."""
        p = nxt(lo) if lo is not None else -RMAX
        g, a, b = band(RMAX if p is None else p)
        J = ("j",) + z
        return [[ge({z: 1, J: -g, ONE: -g * a}), ge({z: -1, J: g, ONE: g * a}), ge({J: -1, ONE: b - a})]] + \
            [[A] for A in ([ge({z: -1, ONE: prv(g * a)})] if g * a > -RMAX else []) + ([ge({z: 1, ONE: -nxt(g * b)})] if g * b < RMAX else [])]

    def step_cases(self, z, lo):
        """(call 2; 3.1) A sum, a multiple of R's finest step 10^LOW: at or below the multiple at or under lo, or above it."""
        G = floor(lo * 10 ** -LOW) * Fraction(10) ** LOW
        return [[ge({z: -1, ONE: G})], [ge({z: 1, ONE: -G - Fraction(10) ** LOW})]]

    def half_need(self, case, atoms, cut):
        """(3.5a; cert.py) A half cut's condition and the system that must have no point for the cut to hold on every
        solution: the case's count atoms and its condition >= 0 (implied: count_ints' atoms). None: no such cut."""
        Ms = [A for A in atoms if isinstance(A, PAtom)]
        cond = next((cd for cu, cd in self.half_cands(case, Ms) if cu[1] == cut[1] and C.same(cu[0], cut[0])), None)
        if cond is None:
            return None
        return [A for A in self.case_atoms(case) + atoms if all(v == ONE or v[0] in ("n", "p", "m") for v in A[0])] + [ge(cond)]

    def disjunction(self, name, args, case, atoms, more):
        """(cert.py) The model's disjunction a split of this kind rests on, recomputed here from the model's own data:
        ([(case, atoms)], obligations), the cases holding together on every input of the parent (atoms: the option's;
        more: the parent's). Raises cert.Bad when the model states no such disjunction."""
        if name == "nest":
            Ms = [A for A in atoms if isinstance(A, PAtom)]
            B = dict(self.nests(Ms) + self.pcuts(case, Ms)).get(args)
            if B is None:
                raise C.Bad(f"no nest {args!r} in the model")
            return [(case, [RAtom(A, args, i) for A in Bi]) for i, Bi in enumerate(B)], []
        if name == "cap":
            g = dict(caps([A for A in atoms if isinstance(A, PAtom)])).get(args[1])
            if not g or g[0][0] != args or any(args[1] in F for F, _ in atoms + more):
                raise C.Bad("no cap of the model, or its mean is not free in the parent")
            return [(case, [RAtom(a, k, i) for (k, _), (i, A) in zip(g, ch) for a in A]) for ch in itertools.product(*[list(enumerate(B)) for _, B in g])], []
        if name == "presence":
            X = case[None]
            if args not in X.sums or args in X.pres:
                raise C.Bad("a presence split of a type that is not summed, or decided")
            return [(d, []) for d in self.presence(case, args)], []
        if name == "refine":
            return [(case, [])], []
        if name in ("band", "step", "binade"):
            z, lo = args
            if name == "binade":   # (A01) a float's, and a range of two binades or more (one binade is never split)
                r = frange_in(z, more)   # (D01, review 4 01) the range the parent's atoms state, by their forms
                if not isinstance(z, tuple) or z[:2] != ("z", "pix") or lo is not None and not isinstance(lo, (int, Fraction)) or r is not None and r[1] >= r[2]:
                    raise C.Bad("a binade split of a value that is not a float, or of one binade")
                return [(case, fr) for fr in frange_split(z, r, lo)], []
            if not (zkind(z) == "read" if name == "band" else zkind(z) == "sum" and lo is not None):   # (A04) by the model's kinds
                raise C.Bad(f"a {name} split of a variable that is not a readable number's")
            return [(case, A) for A in (self.band_cases(z, lo) if name == "band" else self.step_cases(z, lo))], []
        if name == "gap":
            p, (va, la), (vb, lb) = args
            s, t, k, r, i = p[1:]
            c, m = self.cls(s, t, k), case[None].nw.get((s, k, r), 0)
            ws = [(None, c[1][0])] + [(("z", "w", s, k, r, j), None) for j in range(m)] + [(None, c[1][1])]
            if p[0] != "p" or i % 2 or not 0 <= i // 2 < len(ws) - 1 or (va, vb) != (ws[i // 2][0], ws[i // 2 + 1][0]) \
                    or va is None and la != ws[i // 2][1] or vb is None and lb != ws[i // 2 + 1][1]:
                raise C.Bad("a gap split whose ends are not its piece's")
            return [(case, A) for A in self.gap_cases(*args)], []
        if name == "layout":   # (3.12b) a one-column table with an empty literal: read from one column or from more
            if args not in self.lay:
                raise C.Bad("a layout split of a table that has no empty literal in one column")
            return [(case, A) for A in self.lay_cases(args, case)], []
        if name == "spell":   # (shape 3) a number of n bytes is at most the greatest below v, at least the least above v, or v
            z, v = args   # (A01) one of the model's number()-read ranges, holding a number in this case (else no n-byte number need exist)
            k = z[3:5] if isinstance(z, tuple) and len(z) == 5 else None
            if not (k is not None and z[:2] == ("z", "raw") and isinstance(v, (int, Fraction)) and k in self.rreg.get(z[2], []) and (case.get(z[2]) or ())[self.rreg[z[2]].index(k)] == "num"):
                raise C.Bad("a spelling split of a value that is not a byte range's number")
            return [(case, A) for A in self.spell_cases(z, v)], []
        if name == "fwin":   # (L5; 3.6) no pair of floats in the window: the model's own enumeration (fwin, fpair), trusted
            if fwin(self.base(case) + atoms + more, [0]) != []:
                raise C.Bad("a float window the model does not find empty")
            return [], []
        if name == "half":
            need = self.half_need(case, atoms, args)
            if need is None:
                raise C.Bad("a half cut the model does not state")
            return [(case, [args])], [need]
        raise C.Bad(f"no disjunction {name} in the model")

    def spell_cases(self, z, v):
        """(shape 3, 3.11) The numbers of n = z[4] bytes split at v: at or below the greatest below v, at or above the least
        above v, or v itself when v is one: every such number is in one (rprev, rnext: the model's, by layout)."""
        n, p, q = z[4], rprev(z[4], v), rnext(z[4], v)
        return ([[ge(lin((-1, {z: 1}), (p, const(1))))]] if p is not None else []) + ([[ge(lin((1, {z: 1}), (-q, const(1))))]] if q is not None else []) \
            + ([[ge(lin((1, {z: 1}), (-v, const(1)))), ge(lin((-1, {z: 1}), (v, const(1))))]] if rin(n, Fraction(v)) else [])

    def pcuts(self, case, Ms):
        """(e2) Cases for a mean with rows in the pieces of an ordered region (no named rows): which pieces are the
        lowest and highest holding its rows (i <= j; or none), whether its other types have rows (their classes'
        ends l, h), and which of the ends is the outer one; the mean lies between the lower and the upper (closed: a
        relaxation that holds on every input)."""
        out, X = [], case[None]
        for M in Ms:
            ks = {v[4] for v in M.S if v != ONE and v[:2] == ("z", "y")}
            if ONE in M.N or len(ks) != 1 or not M.ty:
                continue
            k, s = ks.pop(), next(iter(M.ty))[1]
            inp = lambda v, r: (s, v[2]) in X.sums and v[2] in X.sel.get((s, k), ()) and self.rindex(s, k, self.cls(s, v[2], k)) == r   # noqa: E731
            r = next((r for (s2, k2, r), _ in sorted(X.nw.items(), key=repr) if (s2, k2) == (s, k) and any(inp(v, r) for v in M.ty)), None)
            if r is None or self.agg.get((s, k)) != "both":
                continue
            m, lo, hi = X.nw[(s, k, r)], *self.regs[(s, k)][r][1:]
            ins, oth = [v for v in M.ty if inp(v, r)], [v for v in M.ty if not inp(v, r)]
            (l, _), (h, _) = cends([M.ty[v] for v in oth]) if oth else ((None, 0), (None, 0))
            w = [{("z", "w", s, k, r, j): 1} for j in range(m)]
            low = lambda i: w[i // 2] if i % 2 else w[i // 2 - 1] if i else (const(lo) if lo is not None else None)   # noqa: E731
            up = lambda i: w[i // 2] if i // 2 < m else (const(hi) if hi is not None else None)   # noqa: E731
            Z = lambda i: {("p", s, v[2], k, r, i): 1 for v in ins}   # noqa: E731
            mu, On, B = {M.mu: 1}, {v: 1 for v in oth}, []
            for po in [None] + [(i, j) for i in range(2 * m + 1) for j in range(i, 2 * m + 1)]:
                for oo in (False, True) if oth else (False,):
                    if po is None and not oo:
                        continue
                    i, j = po or (None, None)
                    A = [ge(lin((-1, Z(q)))) for q in range(2 * m + 1) if po is None or q < i or q > j] + [ge(lin((1, Z(q)), (1, const(-1)))) for q in ({i, j} if po else ())]
                    A += [ge(lin((1, On), (1, const(-1))))] if oo else [ge(lin((-1, On)))] if oth else []
                    ups = ([up(j)] if po else []) + ([const(h) if h is not None else None] if oo else [])
                    lows = ([low(i)] if po else []) + ([const(l) if l is not None else None] if oo else [])
                    for U in ([None] if None in ups else ups):
                        for L in ([None] if None in lows else lows):
                            C = [ge(lin((1, U), (-1, V))) for V in ups if U is not None and V is not U] + [ge(lin((1, V), (-1, L))) for V in lows if L is not None and V is not L]
                            C += ([ge(lin((1, U), (-1, mu)))] if U is not None else []) + ([ge(lin((1, mu), (-1, L)))] if L is not None else [])
                            B.append(A + C)
            out.append((("pcut", M.mu, (s, k, r)), B))
        return out

    def same_means(self, case, Ps, atoms, budget):
        """(e) mu = mu' for two means of the same rows: their S and N agree once the types the system gives no rows
        (an atom -n - n' - ... >= 0) are dropped, with their sums (a type with no rows sums to 0)."""
        if len(Ps) < 2:
            return []
        As = self.case_atoms(case) + atoms
        budget[0] += len(As) + len(Ps)
        Z = {v for F, _ in As if ONE not in F and all(c < 0 and v[0] == "n" for v, c in F.items()) for v in F}
        Z |= {v for v in (u for P in Ps for u in P.S) if v != ONE and v[:2] == ("z", "y") and ("n",) + v[2:4] in Z}
        key = lambda F: fz({v: c for v, c in F.items() if v not in Z})
        first, out = {}, []
        for P in Ps:
            Q = first.setdefault((key(P.S), key(P.N)), P)
            out += [] if Q is P else [ge(lin((1, {P.mu: 1}), (-1, {Q.mu: 1}))), ge(lin((-1, {P.mu: 1}), (1, {Q.mu: 1})))]
        return out

    def half_cands(self, case, Ms):
        """The half cuts' candidates (cut, condition): the cut holds on every solution when condition >= 0 has no point
        with the case's counts."""
        X = case[None]
        for M in Ms:
            if M.k is None or ONE in M.N or any(c != 1 or v[0] != "n" for v, c in M.N.items()):
                continue
            for i, (s, k, r, q) in sorted(X.ordv.items(), key=repr):
                if (s, k) != M.k:
                    continue
                reg = self.regs[(s, k)][r]
                u = const(reg[1]) if reg[0] == "pt" else {("z", "w", s, k, r, q): 1}
                m, sel = X.nw.get((s, k, r), 0), X.sel.get((s, k), ())
                hi, lo = {}, {}
                for v in M.N:
                    t = v[2]
                    rt = self.rindex(s, k, self.cls(s, t, k))
                    if rt is None:
                        hi = lo = None
                        break
                    if rt != r:
                        (hi if rt > r else lo)[v] = 1
                    elif m and t in sel:
                        for j in range(2 * m + 1):
                            if j != 2 * q + 1:
                                (hi if j > 2 * q + 1 else lo)[("p", s, t, k, r, j)] = 1
                    elif m:
                        hi[v] = lo[v] = 1
                if hi is None:
                    continue
                for a, end, sg in ((hi, M.hi, 1), (lo, M.lo, -1)):
                    yield ge(lin((sg, u), (-sg, {M.mu: 1}))), lin((1, a), (1, const(-1)))   # no row past u: mu <= u (mirrored)
                    if end is not None:
                        yield (ge(lin((sg * Fraction(1, 2), u), (sg * Fraction(end) / 2, const(1)), (-sg, {M.mu: 1}))),
                               lin((2, a), (-1, M.N), (1, const(-1))))

    def gap_cases(self, p, a, b):
        """The cases of a thin piece (thin), together all its solutions with a readable number between its ends: no
        rows; or rows and the lower end a constant with b above the readable number after it; or a variable in a band
        of R (bands) below its last number (the next is a + step) or at it, or below or above the band."""
        (va, la), (vb, lb) = a, b
        some, out = ge({p: 1, ONE: -1}), [[ge({p: -1})]]
        above = lambda F: [] if vb is None and lb is None else [gt(lin((1, {vb: 1} if vb else const(lb)), (-1, F)))]   # b > F
        if va is None:
            n = nxt(la)
            return out + ([[some] + above(const(n))] if n is not None else [])
        g, i, j = band(la)
        J = ("jw",) + va
        if i < j:
            out.append([some, ge({va: 1, J: -g, ONE: -g * i}), ge({va: -1, J: g, ONE: g * i}), ge({J: -1, ONE: j - i - 1})] + above({va: 1, ONE: g}))
        if nxt(g * j) is not None:
            out.append([some, ge({va: 1, ONE: -g * j}), ge({va: -1, ONE: g * j})] + above(const(nxt(g * j))))
        if g * i > -RMAX:
            out.append([some, ge({va: -1, ONE: prv(g * i)})])
        if g * j < RMAX:
            out.append([some, ge({va: 1, ONE: -nxt(g * j)})])
        return out

    def cbands(self, key):
        """The bands of R meeting a summed interval class, each cut to the class (item 2)."""
        if key not in self.cb:
            (lo, hi), out = self.cls(*key)[1], []
            for g, a, b in bands():
                self.pay[0] += 1
                a, b = max(a, floor(lo / g) + 1) if lo is not None else a, min(b, -floor(-hi / g) - 1) if hi is not None else b
                out += [(g, a, b)] if a <= b else []
            self.cb[key] = out
        return self.cb[key]

    def part_atoms(self, case):
        """Item 2: a summed column whose sum the readable numbers did not reach is cut into parts by bands (refine). A
        part of one band holds q rows summing to g·(a q + K), 0 <= K <= (b - a) q: each sum of q of its numbers, and only
        these. The parts of more bands hold together a sum r between their q times their least and greatest numbers."""
        out = []
        for (s, t, k), ps in self.parts.items():
            if (s, t) not in case[None].sums:
                continue
            B, r = self.cbands((s, t, k)), ("z", "yp", s, t, k)
            if not ps or ps[0][0] != 0 or ps[-1][1] != len(B) - 1 or any(i > j for i, j in ps) or any(a[1] + 1 != b[0] for a, b in zip(ps, ps[1:])):
                from .kernel import fail   # (F01) refine (search.py) chose the parts: they must cut the class's bands into runs, each band in one
                fail("X001", "bug", "a summed column's parts that do not partition its bands: nothing formed (a checker fault, please report; SPEC-EXACT 3.1, 6.1)")
            Y, Q, lo, hi = {("z", "y", s, t, k): -1, r: 1}, {("n", s, t): -1}, {r: 1}, {r: -1}
            for p, (i, j) in enumerate(ps):
                q = ("q", s, t, k, p)
                Q[q] = 1
                if i == j:
                    g, a, b = B[i]
                    Y[q], Y[("k", s, t, k, p)] = g * a, g
                    out.append(ge({q: b - a, ("k", s, t, k, p): -1}))
                else:
                    lo[q], hi[q] = -B[i][0] * B[i][1], B[j][0] * B[j][2]
            out += [ge(Y), ge(lin((-1, Y))), ge(Q), ge(lin((-1, Q))), ge(lo), ge(hi)]
        return out

    def find(self, options, budget, what):
        """(F03; Opus 5.5 review 03) The search's answer for options [(case, atoms)] (search.py's find_options:
        (index, point), None for "none", or Big). Trusted: every "none" a question gets is kept here for its check
        (Decide.certify replays each: a refusal rests on no unchecked "none"), never by the search. A point is not
        checked here: what a question concludes from one is confirmed on bytes (differ_on) or only stops a refusal."""
        f0 = C.fp(options)   # (G02) the options as asked: the search may not change them (Opus 5.5 max review 02)
        s0 = {k: v for k, v in vars(self).items() if k not in SEARCH_SETS}   # (B07, Argon review 2 07) nor the model's own state
        got = self.find_options(options, budget, what)
        if C.fp(options) != f0 or vars(self).keys() - SEARCH_SETS != s0.keys() or any(vars(self)[k] is not v for k, v in s0.items()):
            from .kernel import fail
            fail("X001", "bug", f"{what}: the search changed the question's options or the model's own state: nothing formed (a checker fault, please report; SPEC-EXACT 6.1)")
        if got is not None:
            try:   # (C01, review 3 01) the point as one exact copy: the checker never reads the search's own objects
                got = C.exact(got)
            except C.Bad:
                got = None
            if not (type(got) is tuple and len(got) == 2 and type(got[0]) is int and 0 <= got[0] < len(options) and type(got[1]) is dict):
                from .kernel import fail
                fail("X001", "bug", f"{what}: the search answered with no option of its own: nothing formed (a checker fault, please report; SPEC-EXACT 6.1)")
            return got
        if not self.cert:   # (C4) kept for the question: checked only if its verdict is a refusal (Decide.certify)
            nb = -(-kept_bytes(options) // STEP_BYTES)
            if MEM[0] + PM[0] + nb > MEM_STEPS:
                PEND[:], PM[0], CHK[1] = [], 0, True   # cannot be held beside the decision: a refusal now is not checked (R013)
            else:
                PEND.append(("find", options, what, self, f0))
                PM[0] += nb
        return None

    def row(self, s, t, v, x, i):
        r = ["p"] * (self.width[s] + 1)   # one more column, so that no row is a blank line (an empty cell)
        for k, j in zip(self.cols[s], t):
            r[k - 1] = self.text(s, k, self.classes[(s, k)][j], v, None if i is None else x.get(("z", "cell", s, i, k)))
        return r



SEARCH_SETS = frozenset(("tree", "trees", "leaf_at", "checked", "steps"))   # (B07) the Model attributes search.py sets (memo, parts by entry); steps: the model's work count, an int its calls add to

LETS = {}   # (G03) id(judged node) -> (node, key): the nodes that are a let's expression, each read in its own statement


def let_marks(checker, written, expr):
    """(G03, Opus 5.5 max review 03) Mark the judged statement's nodes that are a let's expression. The kernel reads a let
    once, in its own statement with its own text total (kernel._check: store.begin() per line), and a claim using it
    reads nothing for it; inline() puts the one let object at each use, and _as_judged keeps the tree's shape."""
    LETS.clear()
    own = {id(v): v for v in (getattr(checker, "exprs", None) or {}).values()}
    LETS.update((i, (w, i)) for i, w in own.items())   # (B0304) a let's own node, as an earlier statement holds it (prefix)
    def pair(w, j):
        if not isinstance(w, Call) or not isinstance(j, Call) or len(w.args) != len(j.args):
            return
        if own.get(id(w)) is w:
            LETS[id(j)] = (j, id(w))
        for a, b in zip(w.args, j.args):
            pair(a, b)
    pair(written, expr)


def let_key(x):
    """(G03) The let x's node is the expression of, or None."""
    k = LETS.get(id(x))
    return k[1] if k is not None and k[0] is x else None


def rename(e, a, b):
    """e with the file name a read as b (Decide.slot_bears); a let's node stays one (G03)."""
    if isinstance(e, Name):
        return Name(b) if e.id == a else e
    if not isinstance(e, Call):
        return e
    y = Call(e.fn, tuple(rename(x, a, b) for x in e.args), e.params)
    if let_key(e) is not None:
        LETS[id(y)] = (y, let_key(e))
    return y


def subst(e, node, mod):
    """W._subst (e with node replaced by mod) keeping the let marks (G03): a let's copy is that let's, read once; one
    holding the change is a let of its own (its statement read once, apart)."""
    def scopy(e):   # (the copy, whether node is in it)
        if e is node:
            return mod, True
        if not isinstance(e, Call):
            return e, False
        xs = [scopy(a) for a in e.args]
        y, k, ch = Call(e.fn, tuple(x for x, _ in xs), e.params), let_key(e), any(c for _, c in xs)
        if k is not None:   # W._subst copies every call: a let's copy is changed only if node is in it
            LETS[id(y)] = (y, ("mod", k, id(node)) if ch else k)
        return y, ch
    return scopy(e)[0]


def letwalk(top):
    """(G03, G05, G04c; WLK) top's calls as the kernel evaluates them, each let's once (it reads a let once; witness.evaluate
    keeps its value), with the statement each is charged in (SPEC-EXACT 1): 0 top's own, then each let's, in order;
    the number of statements; the names top reads."""
    out, names, seen, n = [], set(), set(), [1]
    def walk(x, i):
        if not isinstance(x, Call):
            if isinstance(x, Name):
                names.add(x.id)
            return
        k = let_key(x)
        if k is not None:
            if k in seen:
                return
            seen.add(k)
            i, n[0] = n[0], n[0] + 1
        out.append((x, i))
        for a in x.args:
            walk(a, i)
    walk(top, 0)
    return out, n[0], names


def charged(top, slot):
    """Per statement (letwalk), a Counter of slot(call) over its calls (a let's use reads nothing; None: no read)."""
    calls, n, _ = letwalk(top)
    out = [collections.Counter() for _ in range(n)]
    for x, i in calls:
        k = slot(x)
        if k is not None:
            out[i][k] += 1
    return out


def wheres(top):
    """(G05) The file names top reads and its where() calls as evaluated (letwalk)."""
    calls, _, names = letwalk(top)
    return names, [x for x, _ in calls if x.fn == "where"]


def stmts(top):
    """(G03) Per statement, the table slots each tsv()/csv() call written in it reads."""
    return charged(top, lambda x: x.args[0].id if x.fn in ("tsv", "csv") and x.args and isinstance(x.args[0], Name) else None)


def evreads(top):
    """(G04c) Per statement, the events files each call written in it reads (kernel.events_table reads the file each
    call): a named recording's ("rec", slot, labels) by events(), trials(), onset(), duration(); a recordings() set's
    ("rs", slot, task, filter) by an aggregate of events or trials."""
    def slot(x):
        a = x.args[0] if x.args and isinstance(x.args[0], Call) else None
        if a is not None and a.fn == "recording" and x.fn in ("events", "trials", "onset", "duration"):
            return ("rec", a.args[0].args[0].id, rent(a))
        if a is not None and a.fn == "recordings" and x.fn in AGG and len(x.args) > 1 and x.args[1] in (Str(b"events"), Str(b"trials")):
            return ("rs", a.args[0].args[0].id, a.args[1].v.decode("ascii", "replace"), rconds(a))
    return charged(top, slot)


def plus(x, v, n=1):
    y = dict(x)
    y[v] = y.get(v, 0) + n
    return y


class Store(dict):
    """(B02, Argon review 2 02) A certificate input as plain() rebuilt it from exact types: build.py holds no reference to
    it, and nothing in it answers a comparison or a read with its own methods."""


def plain(v, h=None):
    """(BLD; B02) A copy of a certificate input from build.py (untrusted) made of exact types only, or None: bytes whose
    sha256 is their key, a trusted Periodic class rebuilt from exact arguments (the rebuilt one is used: its bytes and sha
    are its constructor's), or a dataset (blobs by their keys, manifest hash) whose every blob is so and whose manifest
    is one of them. A subclass of any of these (whose own __eq__ or items() could show two stores) is None."""
    if type(v) is tuple and len(v) == 2 and type(v[0]) is dict and type(v[1]) is str and h is None:
        bl = {k: plain(u, k) if type(k) is str else None for k, u in v[0].items()}
        return (bl, v[1]) if v[1] in bl and None not in bl.values() else None
    if type(v) in (W.Periodic, RawFile, NiiFile):
        a = v.args   # exact ints and bytes, and RawFile's ov: a list of exact (int, bytes) pairs, copied (build.py keeps the old one)
        if type(a) is not tuple or not all(type(u) in (int, bytes) or type(u) is list and all(type(p) is tuple and len(p) == 2 and type(p[0]) is int and type(p[1]) is bytes for p in u) for u in a):
            return None
        u = type(v)(*[list(u) if type(u) is list else u for u in a])
        return u if h is None or u.sha == h else None
    return v if type(v) is bytes and (h is None or hashlib.sha256(v).hexdigest() == h) else None


class Decide:
    """SPEC-EXACT 5 for one statement: each question is decided, and each "yes" is confirmed on its
    certificate inputs by the real code; the first "no" refuses as SPEC 4.4 item 11 says."""

    def __init__(self, checker, expr, written, names, kinds=None):
        from .kernel import Checker
        self.ck, self.expr, self.written, self.names = Checker, expr, written, names
        self.m = Model(expr, names, kinds or {n: checker.env.get(n, ("",))[0] for n in names})
        self.budget = [self.m.steps + self.m.pay[0]]
        self.vshort = False   # (3.7a) a variance's part was told apart from its whole only by the V003/V005 it makes
        self.m.pay = self.budget   # P2: the model's search steps (inside, split) are the decision's steps
        self.memo, self.bh = {}, [0]   # bh: what this call's cases and branches hold (scoped)

    def run(self, e, case, x, seed=0, b=None):
        """The real answers of e's parts on the certificate input (b: built for an earlier side of a pair), or None (witness.evaluate)."""
        b = self.input(case, x, seed) if b is None else b
        if type(b) is not Store:   # (B02) only input() makes one
            from .kernel import fail
            fail("X001", "bug", "a certificate input that is not the store its hashes name: nothing formed (a checker fault, please report; SPEC-EXACT 6)")
        key = (id(e), tuple(sorted((n, v.sha if isinstance(v, W.Periodic) else v[1] if isinstance(v, tuple) else v) for n, v in b.items())))
        if key not in self.memo:
            self.memo[key] = W.evaluate(self.ck, e, self.names, b, self.budget, LETS, HELD[0], PRE[0])
            if self.budget[0] > W.MAX_WITNESS_STEPS:
                raise Big(f"checking its certificates needs more than {W.MAX_WITNESS_STEPS} counted steps (SPEC-EXACT 8)")
        g = self.memo[key]   # (F02) the reader's read limit (R003; a file past MAX_TEXT_FILE stops witness.MemStore): no readable input
        if g is not None and g.get("refused") in ("R003", "R012") or g is None and any(not isinstance(v, tuple) and len(v) > R.MAX_TEXT_FILE for v in b.values()):
            raise OverRead(f"{e.fn}() needs a certificate input past the read limit (each table at most {R.MAX_TEXT_FILE} bytes, {R.MAX_TEXT_TOTAL} in all, {R.MAX_ACCOUNTED} accounted bytes in memory; SPEC-EXACT 1, D3)")
        return self.memo[key]

    def input(self, case, x, seed=0):
        """(BLD; B02, Argon review 2 02) The certificate input build.py (untrusted) makes for (case, x), as a Store of exact
        types (plain), or X001: an exact dict of exact str names holding every name of the statement."""
        b, out = self.m.bytes_of(case, x, seed), Store()
        if type(b) is dict and all(type(k) is str for k in b) and set(self.names) <= set(b):
            out.update((k, plain(v)) for k, v in b.items())
        if not out or None in out.values():
            from .kernel import fail
            fail("X001", "bug", "a certificate input that is not the store its hashes name: nothing formed (a checker fault, please report; SPEC-EXACT 6)")
        return out

    def outcome(self, e, case, x, seed=0, b=None):
        g = self.run(e, case, x, seed, b)
        if g is None:
            return None
        return g.get(id(e), ("V", g.get("refused")))

    def fault(self, what):
        from .kernel import fail
        fail("X001", "bug", f"{what}: the exact decision found inputs on which it differs, and the real readers and evaluator do not confirm it on their bytes; nothing formed (a checker fault, please report; SPEC-EXACT 6)")

    def branches(self, es):
        """[(case, [branches of each e])] over every case of the rows es name."""
        out = []
        for case in self.m.cases(es, self.bh):
            out.append((case, [self.m.br(e, case) for e in es]))
            hold(self.bh, self.bh[0] * STEP_BYTES + size_of(out[-1][1]) + 128)
            self.budget[0] += sum(len(b) for b in out[-1][1])
        return out

    @scoped
    def w1(self, e):
        """None when e has two answers (confirmed); else (code, what is never so)."""
        if nchain(e) or (e.fn in CMP and nchain(e.args[0])):
            return self.w1_nvar(e)
        if dchain(e) or (e.fn in CMP and dchain(e.args[0])):
            return self.w1_dvar(e)
        if vchain(e) or (e.fn in CMP and vchain(e.args[0])):
            return self.w1_var(e)
        m, kind, what = self.m, self.m.shape(e)[0], f"{e.fn}()"
        opts = [(case, A, r) for case, (bs,) in self.branches([e]) for A, r in bs if r[0] not in ("V", "X")]
        if kind == "bool":
            hold = [[(c, A) for c, A, r in opts if r[1] is b] for b in (True, False)]
            yes, no = (m.find(o, self.budget, what) for o in hold)
            if yes is None:
                return ("S011", "it holds")
            if no is None:
                return ("S008", None)
            pairs = [(hold[0][yes[0]][0], yes[1], 0, hold[1][no[0]][0], no[1], 0)]
        else:
            first = m.find([(c, A) for c, A, r in opts], self.budget, what)
            if first is None:
                return ("S008", None)
            case0, _, r0 = opts[first[0]]
            x0 = first[1]
            if r0[0] == "jtree" or (r0[0] == "bytes" and m.literal(case0, r0[1]) is None):
                pairs = [(case0, x0, 0, case0, x0, 1)]   # its spelling is free: two spellings (H2)
                rg = (r0[1][0], r0[1][2]) if r0[0] == "bytes" and r0[1][1] == "raw" else (None, None)
                if rg[0] is not None and rg[1] in m.rreg.get(rg[0], []) and case0[rg[0]][m.rreg[rg[0]].index(rg[1])] == "num":
                    i = m.rreg[rg[0]].index(rg[1])   # (shape 3) a number()-read range holding a number: the same input with it not a number
                    pairs = [(case0, x0, 0, {**case0, rg[0]: case0[rg[0]][:i] + ("nan",) + case0[rg[0]][i + 1:]}, x0, 0)]
            else:
                rc0 = m.recd(e, case0)   # (R1) a number's answer carries whether it is recorded (kernel Num.recorded)
                other = [(c, A + D) for c, A, r in opts for D in ([[]] if r[0] not in ("V", "X") and m.recd(e, c) != rc0 else self.differ(case0, r0, x0, c, r))]
                got = m.find(other, self.budget, what)
                if got is None:
                    return ("S011", "the selection has a row") if kind == "sel" else ("S008", None)
                pairs = [(case0, x0, 0, other[got[0]][0], got[1], 0)]
        for ca, xa, sa, cb, xb, sb in pairs:
            a, b = self.outcome(e, ca, xa, sa), self.outcome(e, cb, xb, sb)
            if a is None or b is None or a[0] == "V" or b[0] == "V" or a == b:
                self.fault(what)
        return None

    def w1_var(self, e):
        """SPEC-EXACT 3.7: a variance (or SD) has two answers exactly when some answering case can hold rows of an
        interval class or of two distinct points; its values reach 0 (equal rows) and approach, or reach when both
        ends are points, (U − L)²/2 (sample) or /4 (population) over the classes that can hold rows [Var], or have no
        bound when one is unbounded. A comparison holds or fails on some input as those two ends say."""
        v = vchain(e) or vchain(e.args[0])
        cands = self.var_cands(v)
        if e.fn not in CMP:
            for s, k, d, free in cands:
                (lo, tl), (hi, th) = self.ends(s, k, free)
                if hi > lo:   # two readable values: equal rows, and the two ends
                    return self.d_confirm(e, [{s: [(k, tl, lo), (k, tl, lo)]}, {s: [(k, tl, lo), (k, th, hi)]}], None)
            return self.rest("model", "a variance with one readable value in every answering case (3.7)", ("S008", None))
        if not cands:
            return self.rest("model", "a variance with no answering case that can hold rows (3.7)", ("S011", "it holds"))
        f, c, w = e.fn, cutoff(e), width(e.args[0])
        sd = v.fn.endswith("_sd")
        best = None   # (sup, slot, column, ddof, free types): the sup is reached, by the two readable ends (P1)
        for s, k, d, free in cands:
            (lo, _), (hi, _) = self.ends(s, k, free)
            sup = (hi - lo) ** 2 / (2 if d else 4)
            if best is None or sup > best[0]:
                best = (sup, s, k, d, free)
        sup, s, k, d, free = best
        # item 5a: holds and fails are rays in the value (c ± w, SPEC-EXACT 3.7); a ray meets the values iff it holds
        # 0 or the sup, both reached; an SD's sup is the square root of the variance's
        above = lambda a, strict: (a < 0 or sup > a * a or not strict and sup == a * a) if sd else (sup > a or not strict and sup == a)
        below = lambda a, strict: 0 < a or not strict and a == 0
        ray = {"exceeds": ((True, c + w, True), (False, c - w, False)), "atleast": ((True, c + w, False), (False, c - w, True)),
               "below": ((False, c - w, True), (True, c + w, False)), "atmost": ((False, c - w, False), (True, c + w, True))}[f]
        can = [above(a, st) if up else below(a, st) for up, a, st in ray]
        if not can[0]:
            return self.rest("var", (f, c, w, sd, sup), ("S011", "it holds"))
        if not can[1]:
            return self.rest("var", (f, c, w, sd, sup), ("S008", None))
        rows = [self.var_rows(s, k, d, free, "big" if up else "small", None, f) for up, _, _ in ray]
        return self.d_confirm(e, [{s: [(k,) + r for r in pr]} for pr in rows], True)

    @scoped
    def var_cands(self, v, sel=False):
        """(slot, column, ddof, free types) of each answering case of the variance v that can hold rows (3.7); with
        sel, also the types its selection holds (item 5b)."""
        m, what, cands = self.m, f"{v.fn}()", []
        for case, (bs,) in self.branches([v]):
            for A, r in bs:
                if r[0] != "vans" or m.find([(case, A)], self.budget, what) is None:
                    continue
                zero = {u for F, _ in A + m.case_atoms(case) if not F.get(ONE) and all(c < 0 for c in F.values()) for u in F}
                _, s, k, good, d, S = r
                free = [t for t in good if ("n", s, t) not in zero]
                if free:
                    cands.append((s, k, d, free) + ((S, {u[2] for u in zero if u[0] == "n" and u[1] == s}) if sel else ()))
        return cands

    def w2_widen(self, node):
        """Item 5a: W2 of a widen() above a variance. Without it the width is w' = w − q. A widened value's answer is its
        two ends, so at the top any answer differs; under a comparison the outcomes differ exactly when the value lies
        in the pieces K where the comparison's answer (holds, fails or V006) at w and at w' differ."""
        top, v = self.expr, vchain(node)
        whole, cands = subst(top, node, node.args[0]), self.var_cands(v)
        if top.fn not in CMP:
            for s, k, d, free in cands:
                (lo, tl), _ = self.ends(s, k, free)
                return self.differ_on(top, whole, {s: [(k, tl, lo), (k, tl, lo)]})
            return self.rest("model", "a widened variance with no answering case (5a, 3.7)", False)
        sd, K = v.fn.endswith("_sd"), []
        for lo, lc, hi, hc in self.wpieces(top, node):
            if hi is not None and hi < 0:
                continue
            if lo is None or lo < 0:
                lo, lc = Fraction(0), True
            K.append((lo * lo, lc, None if hi is None else hi * hi, hc) if sd else (lo, lc, hi, hc))
        self.budget[0] += len(cands)
        big, why = False, []
        for s, k, d, free in cands:
            try:
                rows = self.var_hit(s, k, d, free, K)
            except OverRows as e:
                big = big or e
                continue
            except Big:
                big = True
                continue
            if rows:
                return self.differ_on(top, whole, {s: [(k,) + r for r in rows]})
            why.append(self.vwhy)
        if isinstance(big, OverRows):
            raise big
        if big:
            raise Big("deciding whether a widened variance lies where the comparison's answer changes needs inputs of more than two rows or a value finer than the readable numbers two rows reach (item 5a, SPEC-EXACT 3.7)")
        if None in why:
            return self.rest("lemma", "a widened variance never where the answer changes (var_hit, 5a, 3.7)", False)
        for r in why:   # (L6) each candidate's range or values, checked by cert.py
            self.rest(*r, False)
        return False if why else self.rest("model", "a widened variance with no answering case that can hold rows (5a, 3.7)", False)

    def wpieces(self, top, node, w=None, w2=None):
        """The pieces of the value of top's operand (lo, lo closed, hi, hi closed; None: no bound) where the comparison
        top answers differently with and without the widen() node (item 5a; w, w2: the variance shape's widths with
        and without it, nwidth)."""
        f, c, w = top.fn, cutoff(top), width(top.args[0]) if w is None else w
        w2 = w - cutoff(node, "tolerance") if w2 is None else w2
        out = lambda y, w: {"exceeds": (y > c + w, y <= c - w), "atleast": (y >= c + w, y < c - w),
                            "below": (y < c - w, y >= c + w), "atmost": (y <= c - w, y > c + w)}[f]
        P = sorted({c + w, c - w, c + w2, c - w2})
        regs = [(None, False, P[0], False)] + [(p, True, p, True) for p in P] + [(a, False, b, False) for a, b in zip(P, P[1:])] + [(P[-1], False, None, False)]
        self.budget[0] += len(regs)
        # one value of each region decides it: the answers are constant on it
        mid = lambda lo, hi: lo if lo == hi else (lo + hi) / 2 if lo is not None and hi is not None else (hi - 1 if lo is None else lo + 1)
        return [r for r in regs if out(mid(r[0], r[2]), w) != out(mid(r[0], r[2]), w2)]

    def w1_dvar(self, e):
        """Item 5b: a difference of two variances V1 − V2 (or its comparison). Uncoupled (other tables, or one table
        whose two selections share no row type that can hold rows), V1 and V2 vary independently over [0, sup1] and
        [0, sup2] with both ends reached (3.7), so the difference takes values in [−sup2, sup1], both reached, and 0.
        Holds and fails are rays in that value (c ± w)."""
        dn = dchain(e) or dchain(e.args[0])
        return self.w1_hit(e, lambda ps: self.d_hit(dn, ps), None, ("d", dn))

    def w1_nvar(self, e):
        """The variance shape (3.7): a sum of signed variances of one table (at least three, or two with a widen() inside)
        under widen() of total width w, or its comparison, as w1_dvar with n_hit."""
        terms, w = nchain(e) or nchain(e.args[0])
        return self.w1_hit(e, lambda ps: self.n_hit(terms, ps), w, ("n", terms))

    def w1_hit(self, e, hit, w, vr):
        """W1 of w1_dvar and w1_nvar: hit(pieces) is an input whose value is in one of the pieces, or None."""
        if e.fn not in CMP:
            P0, P1 = [(Fraction(0), True, Fraction(0), True)], [(None, False, Fraction(0), False), (Fraction(0), False, None, False)]
            a, b = hit(P0), hit(P1)
            if a is None:
                return self.vnone(*vr, P0, "a difference or sum of variances never 0 (d_hit/n_hit, 5b, 3.7)", ("S011", "it has an answer"))
            if b is None:
                return self.vnone(*vr, P1, "a difference or sum of variances always 0 (d_hit/n_hit, 5b, 3.7)", ("S008", None))
            return self.d_confirm(e, [a, b], False)
        H, F = rays(e, w)
        a = hit([H])
        if a is None:
            return self.vnone(*vr, [H], "a difference or sum of variances never holds (d_hit/n_hit, 5b, 3.7)", ("S011", "it holds"))
        b = hit([F])
        if b is None:
            return self.vnone(*vr, [F], "a difference or sum of variances never fails (d_hit/n_hit, 5b, 3.7)", ("S008", None))
        return self.d_confirm(e, [a, b], True)

    def w2_nwiden(self, node):
        """W2 of a widen() in the variance shape: at the top any answering input (another width is another answer); under
        a comparison the pieces where the answers at w and w - q differ (wpieces), met by n_hit or by no input."""
        top = self.expr
        whole = subst(top, node, node.args[0])
        terms, w = nchain(top.args[0] if top.fn in CMP else top)
        w2 = nwidth(top.args[0] if top.fn in CMP else top, node)
        if w2 == w:   # its symbol's other uses give back the width it takes away: no answer changes
            return self.rest("model", "a widen() whose width its symbol's other uses give back (3.7)", False)
        K = self.wpieces(top, node, w, w2) if top.fn in CMP else [(None, False, None, False)]
        got = self.n_hit(terms, K) if K else None
        return self.vnone("n", terms, K, "a widened sum of variances never where the answer changes (n_hit, 3.7)", False) if got is None else self.differ_on(top, whole, got)

    def n_range(self, cs, co):
        """[lo, hi] holding the sum of signed variances (co: their signs by variance) of the candidates cs (3.7): per column
        the population variance's sup; a·Vs + b·Vp = Vp·(a·n/(n - 1) + b), n >= 2, lies in Vp's range times [min, max] of 0,
        a + b and 2a + b."""
        sup = {}
        for s, k, d, f, S, Z in cs:
            sup[k] = max(sup.get(k, 0), (self.ends(s, k, f)[1][0] - self.ends(s, k, f)[0][0]) ** 2 / 4)
        ab = {k: (co.get(("sample_variance", cs[0][0], k), 0), co.get(("population_variance", cs[0][0], k), 0)) for k in sup}
        return tuple(sum(sup[k] * op(0, a + b, 2 * a + b) for k, (a, b) in ab.items()) for op in (min, max))

    def vranges(self, kind, x):
        """(L6; cert.vrange_none) Closed intervals that together hold every value of the variance shape on every answering
        input, one per candidate (3.7: a variance lies in [0, sup]): kind "v" a variance (x: its candidates), "d" a
        difference of two (x: the chain), "n" a sum of signed ones (x: its terms). The model's own ranges."""
        if kind == "v":
            return [(Fraction(0), (self.ends(s, k, f)[1][0] - self.ends(s, k, f)[0][0]) ** 2 / (2 if d else 4)) for s, k, d, f in x]
        if kind == "d":
            v1, v2 = x.args
            c1, c2 = self.var_cands(v1, True), self.var_cands(v2, True)
            sup = lambda s, k, d, f: (self.ends(s, k, f)[1][0] - self.ends(s, k, f)[0][0]) ** 2 / (2 if d else 4)   # noqa: E731
            self.budget[0] += len(c1) * len(c2)
            # one selection, sample − population: n·Vp/(n − 1) − Vp = Vp/(n − 1) in [0, Vp's sup] (or its negation)
            # (3.13g) selections compared without the types either candidate's case gives no row (d_hit's Zs)
            one = lambda a, b: (a[0], a[1], set(a[4]) - a[5] - b[5], set(a[3]) - a[5] - b[5]) == (b[0], b[1], set(b[4]) - a[5] - b[5], set(b[3]) - a[5] - b[5]) and a[2] != b[2]   # noqa: E731
            return [(Fraction(0), Fraction(0)) if (a[0], a[1], a[2], set(a[4]) - a[5] - b[5]) == (b[0], b[1], b[2], set(b[4]) - a[5] - b[5]) and v1.fn == v2.fn
                    else ((Fraction(0), sup(*a[:2], 0, a[3])) if a[2] else (-sup(*b[:2], 0, b[3]), Fraction(0))) if one(a, b)
                    else (-sup(*b[:4]), sup(*a[:4])) for a, b in itertools.product(c1, c2)]
        co = {}
        for g, v in x:
            co[(v.fn, v.args[0].args[0].id, v.args[1].v)] = co.get((v.fn, v.args[0].args[0].id, v.args[1].v), 0) + g
        out = []
        for cs in itertools.product(*[self.var_cands(v, True) for _, v in x]):
            self.budget[0] += len(cs)
            # no row type every variance reads as a decimal (n_hit's items): a row of any other type makes one refuse
            none = not set.intersection(*(set(f) for _, _, _, f, _, _ in cs)) - set().union(*(set(Z) for *_, Z in cs))
            out.append(None if none else self.n_range(cs, co))
        return out

    def vnone(self, kind, x, K, text, verdict):
        """(L6) A variance shape's "no input in K": a "vrange" record when the model's ranges (vranges) miss every piece
        (checked by cert.vrange_none), else the named lemma text."""
        ivs = self.vranges(kind, x)
        if None in ivs:   # (n) candidates with no row every variance reads: the model's (3.7)
            self.rest("model", "a sum of variances with no row type every variance reads (n_hit, 3.7)", verdict)
            ivs = [iv for iv in ivs if iv is not None]
        try:
            C.vrange_none(ivs, K, lambda n: None)
        except C.Bad:
            return self.rest("lemma", text, verdict)
        return self.rest("vrange", (ivs, list(K)), verdict)

    def w2_dwiden(self, node):
        """Item 5b: W2 of a widen() above a difference of two variances, as for one variance (w2_widen) with the
        difference's values (w1_dvar)."""
        top, dn = self.expr, dchain(node)
        whole = subst(top, node, node.args[0])
        K = self.wpieces(top, node) if top.fn in CMP else [(None, False, None, False)]
        got = self.d_hit(dn, K) if K else None
        return self.vnone("d", dn, K, "a widened difference of variances never where the answer changes (d_hit, 5b, 3.7)", False) if got is None else self.differ_on(top, whole, got)

    def d_out(self, e, got, refusals=False):
        """e's answer by the real code on the rows got ({slot: [(column, type, value)]}; with refusals: a V-refusal as
        ("V", code)), or None (items 5a, 5b)."""
        m, b = self.m, {}
        for n in self.names:
            if n not in m.tabs:
                continue
            rows = []
            for k, t, val in got.get(n, []):
                r = m.row(n, t, 0, {}, None)
                for k, val in zip(k, val) if isinstance(k, tuple) else [(k, val)]:
                    r[k - 1] = m.text(n, k, m.cls(n, t, k), 0, val)
                rows.append(r)
            b[n] = m.table(n, [r[:1] for r in rows], None, True, 1) if n in m.tn and m.width[n] == 1 else m.table(n, rows)   # (3.13g) a tsv() line's variance answers only in Wc = 1
        g = W.evaluate(self.ck, e, self.names, b, self.budget, LETS, HELD[0], PRE[0])
        return None if g is None else g.get(id(e), ("V", g.get("refused")) if refusals and "refused" in g else None)

    def d_confirm(self, e, gots, cmp):
        """Each certificate's rows written as bytes and evaluated by the real code; the two answers must differ (a
        value), or the first hold and the second fail (a comparison); else X001."""
        outs = [self.d_out(e, x) for x in gots]
        if None in outs or outs[0] == outs[1] or (cmp and outs != [("bool", True), ("bool", False)]):
            self.fault(f"{e.fn}()")
        return None

    def var_hit(self, s, k, d, free, K, deep=True):
        """Two rows of the free classes whose variance is in a piece of K, or None when no value of the classes is (their
        values lie in [0, sup], 3.7); Big when a piece meets (0, sup) and no two rows reach it (item 5a)."""
        m, m2 = self.m, (2 if d else 4)
        (L, tl), (U, tu) = self.ends(s, k, free)
        sup, self.vwhy = (U - L) ** 2 / m2, None   # vwhy: (L6) what a None rests on, kept by the caller
        inK = lambda y, p: (y > p[0] or p[1] and y == p[0]) and (p[2] is None or y < p[2] or p[3] and y == p[2])
        inc = lambda c, x: (c[1][0] is None or x > c[1][0]) and (c[1][1] is None or x < c[1][1]) if c[0] == "iv" else x == c[2]
        miss = False
        for p in K:
            if inK(Fraction(0), p):
                return ((tl, L), (tl, L))
            if inK(sup, p):
                return ((tl, L), (tu, U))
            if p[0] > sup or p[2] is not None and (p[2] < 0 or p[2] == 0 and not p[3]):
                continue
            a, b = root(m2 * p[0], 1), (None if p[2] is None else root(m2 * p[2], 0))   # |v - u| strictly between, inward
            anchors = [(L, tl), (U, tu)] + [(m.cls(s, t, k)[2] if m.cls(s, t, k)[0] != "iv" else inside(*m.cls(s, t, k)[1], self.budget), t) for t in free]
            for (u, tu0), sg in itertools.product(anchors, (1, -1)):   # the ends, and a short readable number of each class
                for t in free:
                    self.budget[0] += 1
                    c = m.cls(s, t, k)
                    vs = [c[2]] if c[0] != "iv" else []
                    if c[0] == "iv":
                        lo, hi = (u + a, None if b is None else u + b) if sg > 0 else (None if b is None else u - b, u - a)
                        lo = c[1][0] if lo is None or c[1][0] is not None and c[1][0] > lo else lo
                        hi = c[1][1] if hi is None or c[1][1] is not None and c[1][1] < hi else hi
                        vs += [inside(lo, hi, self.budget)] + [u + sg * r for r in (root(m2 * p[0]), root(m2 * p[2]) if p[2] is not None else None) if r is not None]
                    for x in vs:
                        if x is not None and in_r(x) and inc(c, x) and inK((x - u) ** 2 / m2, p):
                            return ((tu0, u), (t, x))
            miss = True
        if not miss:
            self.vwhy = ("vrange", ([(Fraction(0), sup)], list(K)))
            return None
        if not deep:
            raise Big("no two rows")
        # item (h): a piece below g²/(2(N − d)) (g the finest step of the readable values the classes hold, N = MAX_ROWS)
        # is met only by inputs of more than N rows (a variance of rows not all equal is at least range²/(2(n − d)))
        g = band(Fraction(0) if L <= 0 <= U else min(abs(L), abs(U)))[0]   # every value is a multiple of g
        lb = g * g / (2 * (MAX_ROWS - d))
        live = [p for p in K if (p[2] is None or p[2] > lb or p[3] and p[2] == lb) and p[0] < sup]
        if not live:
            raise OverRows(f"deciding whether a widened variance lies where the comparison's answer changes needs a readable input with more than {MAX_ROWS} rows in one table: the pieces lie below {MAX_ROWS} rows' least positive variance (item (h), SPEC-EXACT 3.7; D3)")
        got = self.two_vals(s, k, d, free, live)
        if got:
            return got
        vals = {t: [c[2]] if c[0] != "iv" else self.few(*c[1]) for t in free for c in [m.cls(s, t, k)]}
        fin = all(vals.values())   # (5a) every readable value of the classes is in vals; else their two ends (item (h))
        vals = {t: v or [nxt(m.cls(s, t, k)[1][0]), prv(m.cls(s, t, k)[1][1])] for t, v in vals.items()}
        top = lambda n: max((n2 // 2) * (n2 - n2 // 2) * (U - L) ** 2 / (n2 * (n2 - d)) for n2 in (n + 1, n + 2))   # noqa: E731
        past = lambda n: all(p[0] > top(n) or p[0] == top(n) and not p[1] for p in K)   # noqa: E731
        ends = sorted({(v, t) for t in free for v in vals[t]}, key=lambda e: (e[0], repr(e[1])))
        ends = [e for i, e in enumerate(ends) if i == 0 or e[0] != ends[i - 1][0]]   # item (h): one row per value
        self.budget[0] += len(K)
        if fin and len(ends) <= 2 and past(self.two_cap(s, k, free)):
            self.vwhy = ("vdeep", (list(K), d, [e[0] for e in ends], self.two_cap(s, k, free)))
            return None   # (5a, no input) the only two values: two_vals tried every n up to its cap; more rows reach below K
        n, tried = 2, 0
        while True:   # BB's call 3 (14:00): multisets of the classes' readable ends, by size, at most MAX_CASES
            self.budget[0] += len(K) if fin else 0
            if fin and n > 2 and past(n - 1):
                self.vwhy = ("vdeep", (list(K), d, [e[0] for e in ends], n - 1))
                return None   # (5a, no input) the ends are every readable value; every multiset of n - 1 rows tried
            for ix in itertools.combinations_with_replacement(range(len(ends)), n):
                tried += 1
                if tried > MAX_CASES:
                    raise Big("no two rows")
                xs = [ends[i][0] for i in ix]
                mu = sum(xs) / n
                y = sum((x - mu) ** 2 for x in xs) / (n - d)
                self.budget[0] += n
                if any(inK(y, p) for p in K):
                    return tuple((ends[i][1], ends[i][0]) for i in ix)
            n += 1

    def few(self, lo, hi):
        """(5a) The readable numbers strictly between lo and hi when there are at most 64 (a class this narrow holds only
        these), else None; charged one step each."""
        xs, x = [], nxt(lo)
        while x is not None and (hi is None or x < hi) and len(xs) <= 64:
            xs.append(x)
            x = nxt(x)
        self.budget[0] += len(xs) + 1
        return xs if len(xs) <= 64 else None

    def two_cap(self, s, k, free):
        """two_vals' most rows: MAX_ROWS, or (the read limit modelled, F02) fewer when that many rows of the longer end
        pass MAX_TEXT_FILE."""
        if not self.m.rb:
            return MAX_ROWS
        m, ((L, ta), (U, tb)) = self.m, self.ends(s, k, free)
        rb = lambda t, x: len(m.table(s, [self.vrow(s, k, t, x)])) - len(m.table(s, []))   # noqa: E731 (one row's bytes)
        return min(MAX_ROWS, (R.MAX_TEXT_FILE - len(m.table(s, []))) // max(rb(ta, L), rb(tb, U)))

    def vrow(self, s, k, t, x):
        """The cells of a row of type t whose column k holds x (as d_out writes it)."""
        m = self.m
        r = m.row(s, t, 0, {}, None)
        r[k - 1] = m.text(s, k, m.cls(s, t, k), 0, x)
        return r

    def differ_on(self, top, whole, got):
        """The statement with and without the part, evaluated by the real code on the rows got: True when both answer
        and differ (else X001)."""
        a, b = (self.d_out(e, got, True) for e in (top, whole))
        if any(t is None or t[0] == "V" and not str(t[1] or "").startswith("V") for t in (a, b)) or a == b:
            self.fault(f"{top.fn}()")
        return True

    def ends(self, s, k, free):
        """((least, its type), (greatest, its type)) of the readable values the free types' classes of column k hold
        (P1: exact, and attained; an unbounded end is the greatest readable number, RMAX, so no placeholder, P4)."""
        m, lows, highs = self.m, [], []
        for t in free:
            c = m.cls(s, t, k)
            lows.append((nxt(c[1][0]) if c[0] == "iv" else c[2], t))
            highs.append((prv(c[1][1]) if c[0] == "iv" else c[2], t))
        self.budget[0] += 2 * len(free)
        return min(lows, key=lambda x: x[0]), max(highs, key=lambda x: x[0])

    def var_rows(self, s, k, d, free, which, C, f):
        """Two rows of the free classes: equal (variance 0), or at the two readable ends, whose variance is the
        sup (3.7; P1, P2: no search)."""
        if which == "small":
            (a, t0), _ = self.ends(s, k, free)
            return ((t0, a), (t0, a))
        (a, ta), (b, tb) = self.ends(s, k, free)
        return ((ta, a), (tb, b))

    def count(self, case, r):
        """A count, number or selection result as a form (a selection: its count)."""
        if r[0] == "rset":   # (R1) a recording set: its answer (the paths) differs when its count does, and the
            return lin(*[(1, self.m.rs_n(r[1], r[2], k, g)) for g in self.m.rsin[r[1:]] for k in self.m.rs_jk(r[1])])   # certificates' sets differ only so
        return self.m.size(r[1], case, self.m.selected(r[1], r[2])) if r[0] == "sel" else r[1]

    def differ(self, case0, r0, x0, case, r):
        """Atom lists, one of which holds exactly when r's answer differs from r0's answer at x0."""
        if r0[0] in ("bytes", "jtree") or r[0] != r0[0] and "aff" not in (r[0], r0[0]):
            if r0[0] != r[0] or r0[0] == "jtree":
                return [[]]   # another kind of answer, or a JSON tree (free: another member)
            b0, b = self.m.literal(case0, r0[1]), self.m.literal(case, r[1])
            return [] if b is not None and b == b0 else [[]]
        (b0, T0), (b, T) = unaff(r0), unaff(r)
        if sum(map(abs, T0.values())) != sum(map(abs, T.values())):
            return [[]]   # a widened value's answer is its two ends: another width is another answer
        if b0[0] == "ratio":
            if value(b0[2], x0) == 0:   # (F04) x0 is the search's (untrusted): a ratio's answer there needs rows, else G is 0 and "no other answer" would be vacuous
                from .kernel import fail
                fail("X001", "bug", "the search gave a point where the answer is a ratio over no rows: nothing formed (a checker fault, please report; SPEC-EXACT 6)")
            G = lin((value(b0[2], x0), b[1]), (-value(b0[1], x0), b[2]))
        else:
            G = lin((1, self.count(case, b)), (-value(self.count(case0, b0), x0), const(1)))
        return [[gt(G)], [gt(lin((-1, G)))]]

    def w2(self, node, mod):
        """True when the part bears on the answer at its judging level (confirmed), False when not."""
        if node.fn == "widen" and (nchain(self.expr) or self.expr.fn in CMP and nchain(self.expr.args[0])):
            return self.w2_nwiden(node)
        if node.fn == "widen" and vchain(node):
            return self.w2_widen(node)
        if node.fn == "widen" and dchain(node):
            return self.w2_dwiden(node)
        if node.fn == "recordings" and len(node.args) == 3 and self.w2_nopt(node, mod):
            return True
        self.vshort = False
        for top in W._path(self.expr, node):
            whole = subst(top, node, mod)
            try:
                self.m.shape(top)
                self.m.shape(whole)
            except NotT:
                continue   # without the part this value is not well formed: judge one level down
            got = self.w2_input(top, whole)
            if got is None and self.vshort:   # (3.7b) the same rows where both answer, else the joint witness search
                if self.same_rows(top, whole):
                    return self.rest("model", "each variance and its place without the part read the same rows wherever both answer (3.7b)", False)
                rows = _S.joint_rows(self, top, whole)
                if rows is None:
                    raise Big(f"deciding whether a part of a variance's selection beside another variance bears needs more than {MAX_CASES} multisets of rows of its classes' readable values (SPEC-EXACT 3.7b)")
                return self.differ_on(top, whole, rows)
            if got is None:
                return False
            case, x = got
            b = self.input(case, x, 0)   # (A07, Argon review 07; B02) one input for both sides: build.py is untrusted
            a1, a2 = self.outcome(top, case, x, 0, b), self.outcome(whole, case, x, 0, b)
            if not any(t is None or (t[0] == "V" and (t[1] or "")[:1] != "V") for t in (a1, a2)) and a1 != a2:
                return True
            self.fault(f"{top.fn}()")
        return self.rest("model", "no level where the statement without the part is well formed", False)

    def w2_nopt(self, node, mod):
        """(G08, Opus 5.5 max review 08) recordings()' participant filter on a dataset without participants.tsv: the
        statement refuses V007 there when it reaches the recordings() call (the kernel evaluates left to right and stops
        at the first refusal), so the filter bears when, on such a dataset, every value evaluated before the call
        answers and the statement without the filter does not refuse V007. Decided in the model of the statement
        without the filter (which reads no participants.tsv: kind rs, Model.rs_dataset writes none), confirmed on bytes.
        False when the statement without it still reads participants() (then V007 either way) or no such input is."""
        whole = subst(self.expr, node, mod)
        try:
            d2 = Decide(None, whole, self.written, self.names, self.m.k0)
            if d2.m.kind.get(node.args[0].args[0].id) != "rs":
                return False
            pre = []
            def before(e):
                for a in e.args if isinstance(e, Call) else ():
                    if any(x is mod for x in W.walk(a)):
                        return before(a)
                    try:
                        d2.m.shape(a)
                        pre.append(a)
                    except NotT:
                        continue   # not a value of its own (a condition, a literal): nothing to refuse
            before(whole)
        except NotT:
            return False
        d2.budget = d2.m.pay = self.budget
        opts = []
        for case, bs in d2.branches(pre + [whole]):
            for combo in itertools.product(*[[b for b in br if b[1][0] not in ("V", "X")] for br in bs[:-1]], [b for b in bs[-1] if b[1] != ("V", "V007") and b[1][0] != "X"]):
                opts.append((case, [A for c in combo for A in c[0]]))
        got = d2.m.find(opts, self.budget, "recordings()")
        if got is None:
            return False
        case, x = opts[got[0]][0], got[1]
        b = d2.input(case, x, 0)   # (A07; B02) one input for both sides
        a1, a2 = d2.outcome(self.expr, case, x, 0, b), d2.outcome(whole, case, x, 0, b)
        if a1 != a2 and not any(t is None or (t[0] == "V" and (t[1] or "")[:1] != "V") for t in (a1, a2)):
            return True
        self.fault("recordings()")

    def same_rows(self, top, whole):
        """(3.7b) True when each variance of top and its place in whole read the same rows wherever both answer: in each
        case, every pair of their answering results the case admits together (m.find; a pair where one refuses is
        outcomes_differ's V against an answer, which w2_input has searched) has the same slot, column and
        ddof and the same good types less those the case and their atoms give no row (a selected row of another type
        makes V005), so the two statements answer alike wherever both answer."""
        m = self.m
        vs = [[v for v in W.subexprs(e) if getattr(v, "fn", None) in VARF] for e in (top, whole)]
        self.budget[0] += len(vs[0]) + len(vs[1])
        if len(vs[0]) != len(vs[1]) or any(a.fn != b.fn for a, b in zip(*vs)):
            return False
        for v1, v2 in zip(*vs):
            for case, (b1, b2) in self.branches([v1, v2]):
                for (A1, r1), (A2, r2) in itertools.product(b1, b2):
                    self.budget[0] += len(A1) + len(A2) + 1
                    if r1[0] != "vans" or r2[0] != "vans" or m.find([(case, A1 + A2)], self.budget, f"{v1.fn}()") is None:
                        continue   # one refusing: told apart by outcomes_differ (V against an answer), searched already
                    zero = {u for F, _ in A1 + A2 + m.case_atoms(case) if not F.get(ONE) and all(c < 0 for c in F.values()) for u in F}
                    f1, f2 = ({t for t in r[3] if ("n", r[1], t) not in zero} for r in (r1, r2))
                    if (r1[1], r1[2], r1[4], f1) != (r2[1], r2[2], r2[4], f2):
                        return False
        return True

    @scoped
    def slot_bears(self, n):
        """W2 for file slot n (SPEC 4.3, fix pass R3), decided exactly: the statement and its copy reading a second
        file n' (not a name of the program) in n's place answer differently on some input, both answering."""
        top = self.expr
        dn = dchain(top) or (top.fn in CMP and dchain(top.args[0]))
        if dn:
            return self.slot_dvar(n, top, dn)
        n2 = n + "'"
        other = rename(self.expr, n, n2)
        d = Decide(None, [self.expr, other], self.written, self.names + [n2], {**self.m.k0, n2: self.m.k0[n]})
        cs = d.m.slot_list(n2, [other], self.bh)
        d.vshort = False
        if len(cs) > MAX_CASES:
            raise Big(f"deciding it needs more than {MAX_CASES} cases of the rows it names (SPEC-EXACT 3.4)")
        paid = 0
        for c in cs:   # the copy's cases one at a time, so the pair costs the sum over them, not a product bound
            d.m.only = {n2: c}
            got = d.w2_input(self.expr, other, True)
            self.budget[0], paid = self.budget[0] + d.budget[0] - paid, d.budget[0]
            if self.budget[0] > W.MAX_WITNESS_STEPS:
                raise Big(f"deciding it needs more than {W.MAX_WITNESS_STEPS} counted steps (SPEC-EXACT 8)")
            if got is not None:
                break
        else:
            if d.vshort:   # (3.7b) the joint witness search over both files' rows; none found is no proof: R013
                d.m.only = {}   # every case of the copy at once: the search's rows are confirmed on bytes
                rows = _S.joint_rows(d, self.expr, other)
                self.budget[0], paid = self.budget[0] + d.budget[0] - paid, d.budget[0]
                if rows is None:
                    raise Big(f"deciding whether a file read by variances bears needs more than {MAX_CASES} multisets of rows of its classes' readable values (SPEC-EXACT 3.7b)")
                return d.differ_on(self.expr, other, rows)
            return False if PEND else self.rest("model", "the copy reading another file has no case", False)
        b = d.input(*got, 0)   # (A07; B02) one input for both: the held slots as the varied one's
        a1, a2 = d.outcome(self.expr, *got, 0, b), d.outcome(other, *got, 0, b)
        if a1 is None or a2 is None or "V" in (a1[0], a2[0]) or a1 == a2:
            self.fault(f"the file in slot {n}")
        return True

    def slot_dvar(self, n, top, dn):
        """Slot n under a difference of two variances, each over its own file (item 5b). With the other at y, the
        variance x read from n sweeps a set within [0, sup] holding 0 and sup (3.7), and the value is ±(x − y): a
        value changes iff sup > 0; a comparison's answer (rays, monotone) changes iff at the two ends one holds and
        the other fails, i.e. y lies in one piece, which var_hit finds or proves empty."""
        groups, deep = [], False   # (L6) each pair's "y in no piece": the held variance's range [0, sup2] against q
        for vary, held, sg in ((dn.args[0], dn.args[1], 1), (dn.args[1], dn.args[0], -1)):
            for (s, k, d, f, S, Z), (s2, k2, d2, f2, S2, Z2) in itertools.product(self.var_cands(vary, True), self.var_cands(held, True)):
                self.budget[0] += 1
                (L, t), (U, u) = self.ends(s, k, f)
                sup, (L2, t2) = (U - L) ** 2 / (2 if d else 4), self.ends(s2, k2, f2)[0]
                if s != n or s2 == s or sup == 0:
                    continue
                rows = ((t2, L2), (t2, L2))
                if top.fn in CMP:
                    H, F = rays(top)
                    up, lo = (H, F) if top.fn in ("exceeds", "atleast") else (F, H)   # the upper ray and the lower
                    # sg·(x − y) at x = sup (sg > 0) or 0 in up, at the other end in lo, as pieces of y
                    q = pmeet(pclip(pneg(up, sup)), pclip(pneg(lo))) if sg > 0 else pmeet(pclip(up), pclip(lo, sup))
                    rows = q and self.var_hit(s2, k2, d2, f2, [q])
                    if not rows:
                        if q:
                            groups.append(self.vwhy)
                            deep = deep or self.vwhy is None
                        continue
                a1, a2 = (self.d_out(top, {s: x, s2: [(k2,) + r for r in rows]}) for x in ([(k, t, L)] * 2, [(k, t, L), (k, u, U)]))
                if a1 is None or a2 is None or "V" in (a1[0], a2[0]) or a1 == a2:
                    self.fault(f"the file in slot {n}")
                return True
        if deep:
            return self.rest("lemma", "a file under a difference of variances never changes the answer (slot_dvar, var_hit, 5b, 3.7)", False)
        for g in groups:
            self.rest(*g, False)
        return False if groups else self.rest("model", "no file under a difference of variances whose variance can change (slot_dvar, 5b, 3.7)", False)

    @scoped
    def w2_input(self, top, whole, answers=False):
        """(case, input) on which the two values have different outcomes, or None (SPEC-EXACT 5.2)."""
        m, opts, shares = self.m, [], []
        for case, (b1, b2) in self.branches([top, whole]):
            for A1, r1 in b1:
                for A2, r2 in b2:
                    (q1, T1), (q2, T2) = unaff(r1), unaff(r2)
                    if q1[0] == "ratio" and q2[0] == "ratio" and sum(map(abs, T1.values())) == sum(map(abs, T2.values())):
                        shares.append((case, A1 + A2, q1, q2))
                        continue
                    rd = "V" not in (r1[0], r2[0]) and "X" not in (r1[0], r2[0]) and m.shape(top)[0] != "bool" and m.recd(top, case) != m.recd(whole, case)
                    opts += [(case, A1 + A2 + D) for D in ([[]] if rd else self.outcomes_differ(case, r1, r2, answers))]
        got = m.find(opts, self.budget, f"{top.fn}()")
        if got is not None:
            return opts[got[0]][0], got[1]
        for case, A, (_, S1, B1), (_, S2, B2) in shares:
            got = m.find([(case, A)], self.budget, f"{top.fn}()")
            if got is None:
                continue
            x0 = got[1]
            zero = {v for F, _ in A + m.case_atoms(case) if not F.get(ONE) and all(c < 0 for c in F.values()) for v in F}   # rows ruled out
            vs = sorted({v for F in (S1, S2, B1, B2) for v in F if v != ONE and v[0] == "n"} - zero, key=repr)
            ys = any(v != ONE and v[0] == "z" for F in (S1, S2) for v in F)
            for x in itertools.chain([x0], (plus(x0, v, k) for v in vs for k in (1, 2)), (plus(plus(x0, v), w) for v, w in itertools.combinations(vs, 2))):
                self.budget[0] += len(vs) + 1   # one evaluation of four forms
                if not ys:
                    if value(S1, x) * value(B2, x) != value(S2, x) * value(B1, x):
                        return case, x   # SPEC-EXACT 5.4: a nonzero quadratic is nonzero at one of these points
                    continue
                # a mean's sums: with the counts fixed, S1·B2 − S2·B1 is affine in the sums, open boxes (SPEC-EXACT 5.4)
                fix = [a for v in sorted({v for F, _ in A + m.case_atoms(case) for v in F if v != ONE and v[0] != "z"} | set(vs), key=repr)
                       for a in (ge(lin((1, {v: 1}), (1, const(-x.get(v, 0))))), ge(lin((-1, {v: 1}), (1, const(x.get(v, 0))))))]
                P = lin((value(B2, x), S1), (-value(B1, x), S2))
                for D in ([gt(P)], [gt(lin((-1, P)))]):
                    got = m.find([(case, A + fix + D)], self.budget, f"{top.fn}()")
                    if got is not None:
                        return case, got[1]
            self.shares_cert(S1, B1, S2, B2, x0, A + m.case_atoms(case), ys, case, A)
        return None

    def shares_cert(self, S1, B1, S2, B2, x0, atoms, ys, case=None, A=None):
        """(cert.py) Equal shares on every solution, recomputed by the checker (5.4) if the verdict is a refusal (C4: kept
        for the question, certify); with sums (ys, L4), the case and branch kept: certify recomputes the points and the
        two systems at each that must have no point (sums_shown)."""
        rec = ("sums", (case, A, S1, B1, S2, B2, x0), self.m) if ys else ("shares", (S1, B1, S2, B2, x0, atoms))
        nb = -(-kept_bytes(rec[1]) // STEP_BYTES)   # (the model is held anyway)
        if MEM[0] + PM[0] + nb > MEM_STEPS:
            PEND[:], PM[0], CHK[1] = [], 0, True
        else:
            PEND.append(rec)   # (L4) with sums: the finds at each point are kept; certify checks they are the ones 5.4 needs (sums_shown)
            PM[0] += nb

    def rest(self, kind, what, verdict):
        """(cert.py) What a refusal (verdict) of this question rests on beside its finds, kept for its check: ("var",
        facts) recomputed by cert.var_verdict; ("model", text) the model alone (trusted, counted); ("lemma", text) a
        named lemma (trusted, counted: not certified yet). Returns verdict."""
        PEND.append((kind, what, verdict))
        return verdict

    def sums_shown(self, rec, m, shown):
        """(L4; 5.4 with sums) Two shares whose sums are free equal on every solution: with the counts fixed at x0, at
        x0 + 1 or 2 of one count, and at x0 + 1 of two, S1·B2 - S2·B1 is affine in the sums and must be 0 on every
        solution there: both its signs' systems (the case's branch, the counts fixed, P > 0 or P < 0) must be among the
        finds replayed and shown to have no input. The points and systems are recomputed here from the kept case,
        branch and forms (as w2_input builds them); a missing one is cert.Bad (X001)."""
        case, A, S1, B1, S2, B2, x0 = rec
        ca = m.case_atoms(case)
        zero = {v for F, _ in A + ca if not F.get(ONE) and all(c < 0 for c in F.values()) for v in F}
        vs = sorted({v for F in (S1, S2, B1, B2) for v in F if v != ONE and v[0] == "n"} - zero, key=repr)
        cnt = sorted({v for F, _ in A + ca for v in F if v != ONE and v[0] != "z"} | set(vs), key=repr)
        for x in itertools.chain([x0], (plus(x0, v, k) for v in vs for k in (1, 2)), (plus(plus(x0, v), w) for v, w in itertools.combinations(vs, 2))):
            pay(len(cnt) + len(A) + 4)
            fix = [a for v in cnt for a in (ge(lin((1, {v: 1}), (1, const(-x.get(v, 0))))), ge(lin((-1, {v: 1}), (1, const(x.get(v, 0))))))]
            P = lin((value(B2, x), S1), (-value(B1, x), S2))
            for D in ([gt(P)], [gt(lin((-1, P)))]):
                if (id(m), id(case), C.key(A + fix + D)) not in shown:
                    raise C.Bad("shares with sums: a point's system that was not shown to have no input")

    def limit_shown(self, pend, rb):
        """(F02; G02b, Opus 5.5 max review 02) Whether a find of a refusal decided with the read limit (Model.rb) has,
        replayed without the limit atoms, a point the trusted model confirms past the limit (Model.past_limit): then the
        refusal holds only by the limit. A point it does not confirm is the search's fault (X001); no point, or none
        within the bound, leaves the plain reason (every readable input gives one answer: true either way)."""
        for kind, *it in pend:
            if kind != "find":
                continue
            m = it[2]
            m.rb, m.trees, m.memo, m.big_ok = False, None, {}, True
            try:
                got = m.find(it[0], rb, it[1])
            except (Big, Unchecked):
                got = None
            finally:
                m.rb, m.memo, m.big_ok = True, {}, False
            if got is not None:
                if not m.past_limit(*it[0][got[0]], got[1]):
                    from .kernel import fail
                    fail("X001", "bug", f"{it[1]}: the search's point without the read limit is not one past it: nothing formed (a checker fault, please report; SPEC-EXACT 1, 6.1)")
                return True
        return False

    def certify(self):
        """(C4; BB's call 28 Oct 2026 18:05) The verdict is a refusal: the question's "none" finds are replayed with
        certificates (logs, trees, cert.py's checks) and its equal shares recomputed, after the decision and outside its
        budget: the replay's search steps and the checking steps each against the stated bound, memory in the one
        account. A certificate that does not check is X001; past a bound, Big (the refusal is R013: not checked, not
        exact). A form never comes here."""
        if CHK[1]:
            raise Big("its certificate could not be kept beside the decision within the memory bound (SPEC-EXACT 6.1, 8)")
        rb, pend, pm = [0], PEND[:], PM[0]
        ms = list({id(it[2]): it[2] for kind, *it in pend if kind == "find"}.values())   # each find's own model (slot_bears: the copy's)
        saved, MEM[0], PM[0] = [(m.memo, m.pay) for m in ms], MEM[0] + pm, 0
        for m in ms:
            m.cert, m.memo, m.pay = True, {}, rb
        try:
            shown, sums = set(), []   # (L4) the replayed one-option finds (shown to have no input), by model, case and atoms
            for kind, *it in pend:
                if kind == "find":
                    it[2].trees = None
                    if it[2].find(it[0], rb, it[1]) is not None:
                        from .kernel import fail
                        fail("X001", "bug", f"{it[1]}: a search that found no input finds one when replayed for its certificate: nothing formed (a checker fault, please report; SPEC-EXACT 6)")
                    trees = it[2].trees or {}
                    if type(trees) is not dict or any(type(t) is not C.Tree or t.model is not it[2] for t in dict.values(trees)):   # (C01)
                        raise C.Bad("an option's tree without its model")
                    C.options_closed(it[0], trees, it[3], pay)   # every option's splits end in checked leaves, the options as asked
                    if len(it[0]) == 1:
                        pay(sum(len(F) + 1 for F, _ in it[0][0][1]))
                        shown.add((id(it[2]), id(it[0][0][0]), C.key(it[0][0][1])))
                    for t in trees.values():
                        for k, n in t.splits.items():
                            CERTS["split: " + k] = CERTS.get("split: " + k, 0) + n
                    continue
                if kind == "var":
                    v = C.var_verdict(*it[0])
                    pay(1)
                    if v is None or v[0] != it[1][0]:
                        raise C.Bad(f"a variance's verdict {it[1][0]} that its values [0, sup] do not give")
                    CERTS["var: " + ("by sup (lemma 3.7)" if v[1] else "by its sign")] = CERTS.get("var: " + ("by sup (lemma 3.7)" if v[1] else "by its sign"), 0) + 1
                    continue
                if kind == "vdeep":   # (L6) every readable value tried, up to rows past which no variance reaches K
                    C.vdeep_none(*it[0], pay)
                    CERTS["var: by its values"] = CERTS.get("var: by its values", 0) + 1
                    continue
                if kind == "vrange":   # (L6) the model's ranges of the shape's values miss every piece
                    C.vrange_none(*it[0], pay)
                    CERTS["var: by its range"] = CERTS.get("var: by its range", 0) + 1
                    continue
                if kind == "lemma":   # (L6) a claim the search made with no certificate: none is left; one reached is a fault
                    raise C.Bad(f"a refusal that rests on a claim with no certificate ({it[0]})")
                if kind == "model":
                    CERTS[kind + ": " + it[0]] = CERTS.get(kind + ": " + it[0], 0) + 1
                    continue
                if kind == "sums":
                    sums.append(it)
                    continue
                try:
                    C.shares_zero(*it[0], pay)
                except C.Bad as e:
                    from .kernel import fail
                    fail("X001", "bug", f"a certificate of equal shares does not check ({e}): nothing formed (a checker fault, please report; SPEC-EXACT 6)")
                CERTS["shares"] = CERTS.get("shares", 0) + 1
            for rec, mod in sums:
                self.sums_shown(rec, mod, shown)
                CERTS["shares with sums"] = CERTS.get("shares with sums", 0) + 1
            return LIMIT if any(m.rb for m in ms) and self.limit_shown(pend, rb) else ""   # (H05) a vdeep record holds at any size: no reason of its own
        except (Big, Unchecked) as b:
            raise Big(f"checking the refusal's certificate exceeded the bound ({b}); a refusal not checked is not exact (SPEC-EXACT 6.1, 8)") from None
        except C.Bad as e:   # a split that is not the model's, or an obligation not shown
            from .kernel import fail
            fail("X001", "bug", f"a certificate of no input does not check ({e}): nothing formed (a checker fault, please report; SPEC-EXACT 6)")
        finally:
            for m, (mm, mp) in zip(ms, saved):
                m.cert, m.memo, m.pay = False, mm, mp
            MEM[0] -= pm
            CHK[2] += rb[0]
            C.CHECKED.clear()

    def outcomes_differ(self, case, r1, r2, answers=False):
        """Atom lists, one of which holds exactly when the two results differ (shares apart); with answers, both answer."""
        m = self.m
        if "X" in (r1[0], r2[0]) or answers and "V" in (r1[0], r2[0]):
            return []   # no answer on this input (a reader's or a sort refusal): no witness
        (q1, T1), (q2, T2) = unaff(r1), unaff(r2)
        if q1[0] in ("vans", "dvans", "nvans") and q2[0] in ("vans", "dvans", "nvans"):   # SPEC-EXACT 3.7: a part of a variance's selection bears through V003/V005
            if sum(map(abs, T1.values())) != sum(map(abs, T2.values())):   # or not at all; widths: 5a
                return [[]]
            g = lambda q: q[:5] if q[0] == "vans" else ("dvans", q[1][:5], q[2][:5]) if q[0] == "dvans" else q   # (3.7a) a selection's
            if g(q1) != g(q2) or q1[0] == "nvans":   # good types (Model.cls): equal ones answer alike wherever both answer; else not so
                self.vshort = True   # beside another value refusing on the same inputs (it hides the V003/V005 the part makes): not decided
            return []
        if r1[0] == "V" or r2[0] == "V":
            return [[]] if r1 != r2 else []
        if r1[0] != r2[0] and "aff" not in (r1[0], r2[0]) or r1[0] == "jtree":
            return [] if r1 == r2 else [[]]
        if r1[0] == "bool":
            return [[]] if r1 != r2 else []
        if r1[0] == "bytes":
            b1, b2 = m.literal(case, r1[1]), m.literal(case, r2[1])
            return [] if r1[1] == r2[1] or (b1 is not None and b1 == b2) else [[]]
        (q1, T1), (q2, T2) = unaff(r1), unaff(r2)
        if sum(map(abs, T1.values())) != sum(map(abs, T2.values())):
            return [[]]
        G = lin((1, self.count(case, q1)), (-1, self.count(case, q2)))
        return [[gt(G)], [gt(lin((-1, G)))]] if G else []


def check(checker, expr, written, names):
    """W1 and W2 for a part-T statement (SPEC-EXACT 5); raises NotT before any work outside it. (F02) Decided first
    over every input (no read limit: D3); a Past (more than MAX_ROWS rows, or a certificate past the read limit) decides
    it again over the readable inputs only (SPEC-EXACT 1: each table at most MAX_TEXT_FILE bytes, the statement's text
    at most MAX_TEXT_TOTAL). A refusal there whose certificates check without the limit too is the plain one; else
    it says it holds only by the read limit."""
    hs = checker.store.log | checker.store.gate | set().union(*checker.actual_reads())
    pre = {i for i, (_, rs) in enumerate(checker.prefix) if rs & hs}   # (C02) the statements prefix() runs again
    RB[0], HELD[0], PRE[0] = False, checker.store.held(hs, pre), prefix(checker, hs)   # (H03) the program's memory before it, less its files' (B0304)
    let_marks(checker, written, expr)
    try:
        return check1(checker, expr, written, names, None)
    except Past as p:
        RB[0] = True
        return check1(checker, expr, written, names, p)
    finally:
        RB[0] = True


def prefix(checker, hs):
    """(B0304, Argon review 2 03 and 04) The earlier lets and claims that read a file of hs, in program order. held()
    leaves out what they made from those files, so a certificate runs each again on its candidate (W.evaluate), with
    the program's other files, and what it holds made from them, as they are (their memo, sizes and charged keys).
    (D02, review 4 02) Every other let, which reads none of hs, is not run again: the kernel on the candidate evaluates
    it once, in its own statement, on the same files; its value is the program's (lets: id of its node -> (value,
    node)), as held() keeps its rows. So the re-run charges exactly what held() leaves out, by construction."""
    es = [e for e, rs in checker.prefix if rs & hs]
    if not es:
        return None
    s, keep = checker.store, lambda k: not (len(k) > 1 and k[1] in hs)
    env = {n: b for n, b in checker.env.items() if b[0] in ("file", "dataset")}
    own = {id(w): n for n, w in (getattr(checker, "exprs", None) or {}).items()}
    lets = {id(e): (checker.env[own[id(e)]][1], e) for e, rs in checker.prefix
            if not rs & hs and id(e) in own and checker.env.get(own[id(e)], ("",))[0] == "let"}
    return es, env, s, {k: v for k, v in s._memo.items() if keep(k)}, {k: v for k, v in s._sizes.items() if keep(k)}, {k for k in s.seen0 if keep(k)}, lets


LIMIT = "; it holds only by the read limit (each table at most %d bytes, %d bytes of text in all, %d accounted bytes in memory, SPEC-EXACT 1)" % (R.MAX_TEXT_FILE, R.MAX_TEXT_TOTAL, R.MAX_ACCOUNTED)


def check1(checker, expr, written, names, past):
    """One pass of check(): past None, without the read limit (a Past propagates); else with it (a Past is R013)."""
    from .kernel import fail
    d, MEM[0], CHK[:] = Decide(checker, expr, written, names), 0, [0, False, 0]
    C.CHECKED.clear()
    for e in W.subexprs(expr):
        d.m.shape(e)
    def q():   # (C4) a new question: what a refusal of it rests on is kept from here
        PEND[:], PM[0], CHK[1] = [], 0, False
    try:
        for e in W.subexprs(expr):
            q()
            r = d.w1(e)
            lim = (d.certify() or "") if r is not None else ""
            if r is not None and r[0] == "S011":
                fail("S011", "6", f"{e.fn}(): there is no readable input on which {r[1]} (decided exactly, SPEC-EXACT 5.1{lim}), so the claim's parts allow none (v4 SPEC 4.3)")
            if r is not None:
                fail("S008", "1", f"{e.fn}(): every readable input gives this value one answer (decided exactly, SPEC-EXACT 5.1{lim}), so the bytes do not bear on it (v4 SPEC 4.3, W1)")
        for (node, mod, desc), (wnode, _, _) in zip(W.parts(expr), W.parts(written)):
            q()
            if not d.w2(node, mod):
                lim = d.certify() or ""
                fail("S008", "1", f"{node.fn}(): on no readable input does {desc} change the answer (decided exactly, SPEC-EXACT 5.2{lim}), so it does not bear on it (v4 SPEC 4.3, W2)" + W._one_spelling(written, wnode))
        for n in names if len(names) > 1 else ():
            q()
            if not d.slot_bears(n):
                lim = d.certify() or ""
                fail("S008", "1", f"the file sha256:{checker.env[n][1]}: on no readable input with the other files held does it change the answer (decided exactly, SPEC-EXACT 5.2{lim}), so it is not shown to bear on it (v4 SPEC 4.3, W2)")
    except Big as b:
        if past is None and isinstance(b, Past):
            raise
        fail("R013", "bounds", f"showing that the bytes bear on the answer: {b} (Reality bounds, v4 SPEC 4.5)")
    finally:
        checker.store.steps.add(d.budget[0] + CHK[0] + CHK[2])   # the decision's steps and a refusal's check's
        C.CHECKED.clear()
        PEND[:], PM[0] = [], 0


# The search (untrusted: SPEC-EXACT 6.1; verify-opus-exact/partb/CERT/ITEM3.md): its "none" is replayed and checked by
# cert.py before any refusal, its solutions are confirmed on bytes, so it is not in the trusted base. Model's search
# methods live in search.py and are attached here; its functions are re-exported under their old names.
from . import search as _S  # noqa: E402
from .search import MSearch, presolve, tidy, empty_box, lp, lp1, fm, back  # noqa: E402,F401
for _n in ('solve', 'solve1', 'half_cut', 'count_ints', 'implied', 'one_solve', 'one_solve1', 'one_solve2', 'finish', 'find_options'):
    setattr(Model, _n, getattr(_S, _n))
# (SRH) the search's helpers that were left here (partb/SHRINK/AUDIT.md): the proof-log writer, the leaf check's driver
# (Model.no: cert.check, a tree takes only systems it registered) and the search's own cuts and picks
from .search import Log, cap_ok, fdown, fnext, form_bytes, fpick, fstep, fup, is_float, spent_all  # noqa: E402,F401
for _n in ('no', 'prove', 'rs_small', 'refine', 'thin', 'piece_atoms', 'psign', 'unrealized', 'rows_of'):
    setattr(Model, _n, getattr(_S, _n))
# (HIT) the variance shapes' witness pickers: an input they find is confirmed on bytes (differ_on, d_confirm); their
# None refuses only through vnone (a model's range certificate cert.vrange_none checks, else X001), or var_hit's own
from .search import var_of  # noqa: E402,F401
for _n in ('d_hit', 'n_hit', 'd_domain', 'd_scale', 'two_vals', 'dvals'):
    setattr(Decide, _n, getattr(_S, _n))

# The certificate inputs' bytes (untrusted, unit BLD; partb/SHRINK/AUDIT.md): each input is checked as a store by
# Decide.run and read by the real readers and evaluator, and a form needs their answers to differ. Model's builders
# live in build.py and are attached here; its functions are re-exported under their old names.
from . import build as _B  # noqa: E402
from .build import split, spell1, rspell, dec_ct, nii2, bold, merge_chains, W_split_int  # noqa: E402,F401
for _n in ('bytes_of', 'bytes_of1', 'file_bytes', 'type_rows', 'realize', 'rs_dataset', 'rs_recs2', 'rec_dataset', 'jtext', 'stext', 'least_table', 'vmin', 'tw_rows', 'lay_of', 'inside_sum'):
    setattr(Model, _n, getattr(_B, _n))
C.ATOMS.update({RAtom: ("z", "r"), PAtom: ("mu", "S", "N", "lo", "hi", "ty", "ends", "a0", "key", "k")})   # (C01) cert.exact copies these

"""A second implementation of Reality v3's plain-TSV fragment, written from v3/SPEC.md and the
principle spec, sharing no code with reality4 (tests/test_source.py checks the imports).

It reads PROGRAM TEXT, not query tuples: its own tokenizer and parser, its own TSV and decimal
readers, its own UTS #39 skeleton (it compiles the same pinned confusables.txt data file with
its own parser), its own computations and its own printing of values.

Fragment: file / let / claim [is ...]; tsv rows count share where eq ne cell key header number
sum mean max min widen difference exceeds below atleast atmost, slots c = and tolerance =.
widen and difference follow v4 SPEC 5.2 (affine forms, one symbol per value; O12, 27 Oct 2026),
written from that text, not from reality4.

run(program: bytes, files: {sha256: bytes}) -> [(line, "formed", value_text) | (line, "refused", code)]
value_text is what follows the sort on a formed line, e.g. '= 3 (Exact)', 'holds',
'lies within [1, 3] (Interval)', '= "A"', '= 1/2 (Exact)'.
"""

import hashlib
import os
import unicodedata
from fractions import Fraction

KEYS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
HEADER_CHARS = KEYS | {"_"}
CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reality4", "data", "confusables.txt")
CONF_SHA = "6ed3ee967c9dfdf6677d563c9985182fbc50a2efb7d6059cd57b2e2ce18f5b92"


class Refused(Exception):
    def __init__(self, code):
        self.code = code


def _load():
    with open(CONF, "rb") as f:
        raw = f.read()
    assert hashlib.sha256(raw).hexdigest() == CONF_SHA
    m = {}
    for row in raw.decode("utf-8").splitlines():
        body = row.partition("#")[0]
        if ";" not in body:
            continue
        a, b = body.split(";")[0:2]
        m[chr(int(a.strip(), 16))] = "".join(chr(int(x, 16)) for x in b.split())
    return m


PROTO = _load()


def skel(s):
    """UTS #39 skeleton (NFD, prototypes, NFD), then the spec's K rule: A-Z lowercased, o and 0
    one class, i, l and 1 one class, then rn read as m."""
    t = unicodedata.normalize("NFD", "".join(PROTO.get(c, c) for c in unicodedata.normalize("NFD", s)))
    out = []
    for c in t:
        if "A" <= c <= "Z":
            c = chr(ord(c) + 32)
        if c in "o0":
            c = "0"
        elif c in "il1":
            c = "1"
        out.append(c)
    return "".join(out).replace("rn", "m")


DEFAULT_IGNORABLE = [(0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0xFE00, 0xFE0F),
                     (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF)]
DEFAULT_IGNORABLE_1 = {0x00AD, 0x034F, 0x061C, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x3164, 0xFEFF, 0xFFA0}


def unseen(s):
    for c in s:
        o, cat = ord(c), unicodedata.category(c)
        if cat[0] == "C" or cat in ("Zl", "Zp") or (cat == "Zs" and c != " "):
            return True
        if o in DEFAULT_IGNORABLE_1 or any(a <= o <= b for a, b in DEFAULT_IGNORABLE):
            return True
    return s.startswith(" ") or s.endswith(" ")


def scope(strings):
    """Call 2: no unseen character, no two different strings with one skeleton."""
    by = {}
    for s in strings:
        if unseen(s):
            raise Refused("K004")
        k = skel(s)
        if k in by and by[k] != s:
            raise Refused("K002")
        by.setdefault(k, s)


# ---- readers ------------------------------------------------------------------------------

BREAKS = "\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029\ufeff\x00"


def tsv(b):
    if b"\r" in b.replace(b"\r\n", b""):
        raise Refused("T002")
    b = b.replace(b"\r\n", b"\n")
    if b.startswith(b"\xef\xbb\xbf"):
        raise Refused("T001")
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("T001")
    if not s:
        raise Refused("T003")
    if any(ch in s for ch in BREAKS):
        raise Refused("T006")
    if '"' in s:
        raise Refused("T005")
    lines = s.split("\n")
    if lines[-1] == "":
        lines = lines[:-1]
    if len(lines) >= 2 and lines[-1] == "" and len(lines[0].split("\t")) >= 2:
        lines = lines[:-1]
    if "" in lines:
        raise Refused("T003")
    if "" in lines[0].split("\t"):
        raise Refused("T007")
    table = [ln.split("\t") for ln in lines]
    if any(len(r) != len(table[0]) for r in table):
        raise Refused("T004")
    return table[0], table[1:]


def decimal(s):
    mant, e, ex = s.replace("E", "e").partition("e")
    if e:
        digs = ex[1:] if ex[:1] in "+-" and ex else ex
        if not digs or any(c not in "0123456789" for c in digs):
            return None
        if len(digs) > 6 or int(digs) > 1000:
            raise Refused("R007")
        v = decimal(mant)
        return None if v is None else v * Fraction(10) ** int(ex)
    neg = s.startswith("-")
    body = s[1:] if neg else s
    whole, dot, frac = body.partition(".")
    digits = "0123456789"
    if not whole or any(c not in digits for c in whole) or whole[:1] == "0" != whole:   # v4 SPEC 6.4: no leading zero
        return None
    if dot and (not frac or any(c not in digits for c in frac)):
        return None
    if len(whole) + len(frac) > 1000:
        raise Refused("R007")
    v = Fraction(int(whole)) + (Fraction(int(frac), 10 ** len(frac)) if frac else 0)
    return -v if neg else v


def show(q):
    """Exact decimal if the denominator has only 2s and 5s, else n/d."""
    d, k = q.denominator, 0
    while d % 10 == 0 or d % 2 == 0 or d % 5 == 0:
        if d % 2 == 0:
            d //= 2
        else:
            d //= 5
        k += 1
    if d != 1:
        return f"{q.numerator}/{q.denominator}"
    p = 0
    while (q * 10 ** p).denominator != 1:
        p += 1
    n = abs(q * 10 ** p).numerator
    s = str(n).rjust(p + 1, "0")
    if p:
        s = s[:-p] + "." + s[-p:]
    return ("-" if q < 0 else "") + s


# ---- tokens and parse ----------------------------------------------------------------------

def tokens(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == " ":
            i += 1
        elif c in "(),=/":
            out.append(("p", c))
            i += 1
        elif c == '"':
            j, buf = i + 1, bytearray()
            while s[j] != '"':
                if s[j] == "\\":
                    nx = s[j + 1]
                    if nx == "x":
                        buf.append(int(s[j + 2:j + 4], 16))
                        j += 4
                        continue
                    buf += nx.encode()
                    j += 2
                    continue
                buf += s[j].encode()
                j += 1
            out.append(("s", bytes(buf)))
            i = j + 1
        elif c.isdigit() or (c == "-" and s[i + 1:i + 2].isdigit()):
            j = i + 1
            while j < len(s) and (s[j].isdigit() or s[j] == "."):
                j += 1
            out.append(("n", s[i:j]))
            i = j
        else:
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                j += 1
            out.append(("w", s[i:j]))
            i = j
    return out


class P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        self.i += 1
        return self.t[self.i - 1]

    def expr(self):
        kind, v = self.take()
        if kind == "s":
            return ("str", v)
        if kind == "n":
            return ("num", v)
        if self.peek() != ("p", "("):
            return ("name", v)
        self.take()
        args, params = [], []
        while self.peek() != ("p", ")"):
            if self.peek()[0] == "w" and self.t[self.i + 1] == ("p", "="):
                slot = self.take()[1]
                self.take()
                n = self.take()[1]
                val = ("q", Fraction(n))
                if self.peek() == ("p", "/"):
                    self.take()
                    val = ("ratio", int(n), int(self.take()[1]))
                unit = self.take()[1] if self.peek()[0] == "w" else None
                params.append((slot, val, unit))
            else:
                args.append(self.expr())
            if self.peek() == ("p", ","):
                self.take()
        self.take()
        return ("call", v, args, params)


# ---- meanings ------------------------------------------------------------------------------
# ("file", h) ("table", (header, rows), h) ("sel", base, idx, conds) ("bytes", b, sortkey)
# ("count", n, sortkey) ("share", (k, n), sortkey) ("num", lo, hi, sortkey) ("bool",)

class Run:
    def __init__(self, files):
        self.files, self.env = files, {}
        self.forms = {}   # value key -> (a0, {symbol key: coefficient}), v4 SPEC 5.2

    def form(self, m):
        """The affine form of a number: recorded when it was widened or subtracted, else its point."""
        if m[-1] in self.forms:
            return self.forms[m[-1]]
        return (m[1], {}) if m[1] == m[2] else None

    def arity(self, args, n):
        if len(args) != n:
            raise Refused("S003")

    def params(self, fn, params, want):
        got = {}
        for slot, val, unit in params:
            if slot not in want or slot in got:
                raise Refused("S004")
            if unit is not None:
                raise Refused("U002")
            q = val[1] if val[0] == "q" else None
            if val[0] == "ratio":
                if val[2] == 0 or val[1] < 0 or val[2] < 0:
                    raise Refused("P007")
                q = Fraction(val[1], val[2])
            if want[slot] == "pos" and q <= 0:
                raise Refused("S008" if q == 0 else "S004")
            got[slot] = q
        if set(got) != set(want):
            raise Refused("S005")
        return got

    def ev(self, e, *kinds):
        m = self.mean(e)
        if kinds and m[0] not in kinds:
            raise Refused("S007")
        return m

    def mean(self, e):
        if e[0] == "name":
            b = self.env.get(e[1])
            if b is None:
                raise Refused("N001")
            if b == "refused":
                raise Refused("N003")
            return b
        if e[0] in ("str", "num"):
            raise Refused("S001")
        _, fn, args, params = e
        f = getattr(self, "f_" + fn, None)
        if f is None:
            raise Refused("S002")
        return f(args, params)

    # columns, rows, scope
    def column(self, header, a):
        if a[0] == "num":
            k = int(a[1]) if "." not in a[1] else 0
            if k < 1:
                raise Refused("S006")
            if k > len(header):
                raise Refused("V002")
            return k - 1
        if a[0] != "str":
            raise Refused("S006")
        try:
            name = a[1].decode("ascii")
        except UnicodeDecodeError:
            raise Refused("K001")
        if not name or any(c not in HEADER_CHARS for c in name):
            raise Refused("K001")
        where = [i for i, h in enumerate(header) if h == name]
        if not where:
            raise Refused("V002")
        if len(where) > 1:
            raise Refused("K002")
        scope(header)
        return where[0]

    def colscope(self, rows, k, lits):
        vals = list(lits)
        for r in rows:
            if r[k] not in vals:
                vals.append(r[k])
        scope(vals)

    def lit_cell(self, a):
        if a[0] != "str":
            raise Refused("S006")
        try:
            s = a[1].decode("utf-8")
        except UnicodeDecodeError:
            raise Refused("S008")
        if "\t" in s or "\n" in s or "\r" in s:
            raise Refused("S008")
        return s

    def f_tsv(self, args, params):
        self.arity(args, 1)
        self.params("tsv", params, {})
        f = self.ev(args[0], "file")
        return ("table", tsv(self.files[f[1]]), f[1], ("TSV", f[1]))

    def f_rows(self, args, params):
        self.arity(args, 1)
        self.params("rows", params, {})
        t = self.ev(args[0], "table")
        return ("count", len(t[1][1]), ("RowCount", t[3]))

    def f_count(self, args, params):
        self.arity(args, 1)
        self.params("count", params, {})
        m = self.ev(args[0], "table", "sel")
        n = len(m[1][1]) if m[0] == "table" else len(m[2])
        return ("count", n, ("Count", m[-1]))

    def f_share(self, args, params):
        self.arity(args, 1)
        self.params("share", params, {})
        m = self.ev(args[0], "sel")
        total = len(m[1][1][1])
        if total == 0:
            raise Refused("V003")
        return ("share", (len(m[2]), total), ("Share", m[-1]))

    def f_where(self, args, params):
        if len(args) < 2:
            raise Refused("S003")
        self.params("where", params, {})
        m = self.ev(args[0], "table", "sel")
        base = m if m[0] == "table" else m[1]
        header, rows = base[1]
        conds = list(m[3]) if m[0] == "sel" else []
        for a in args[1:]:
            if a[0] != "call" or a[1] not in ("eq", "ne") or len(a[2]) != 2 or a[3]:
                raise Refused("S006")
            k = self.column(header, a[2][0])
            s = self.lit_cell(a[2][1])
            conds.append((a[1], k, s))
        for k in sorted({c[1] for c in conds}):
            here = [(op, s) for op, kk, s in conds if kk == k]
            self.colscope(rows, k, [s for _, s in here])
            eqs = [s for op, s in here if op == "eq"]
            nes = [s for op, s in here if op == "ne"]
            if len(set(eqs)) < len(eqs) or len(set(nes)) < len(nes):
                raise Refused("S008")
            if len(eqs) > 1 or (eqs and eqs[0] in nes):
                raise Refused("S011")
            if eqs and nes:
                raise Refused("S008")
        idx = [i for i, r in enumerate(rows) if all((r[k] == s) == (op == "eq") for op, k, s in conds)]
        return ("sel", base, idx, tuple(conds), ("Rows", base[3], tuple(conds)))

    def rowpos(self, header, rows, a):
        if a[0] == "call" and a[1] == "key":
            ka = a[2]
            if len(ka) < 2 or len(ka) % 2 or a[3]:
                raise Refused("S003")
            pairs = []
            for j in range(0, len(ka), 2):
                k = self.column(header, ka[j])
                if ka[j + 1][0] != "str":
                    raise Refused("S006")
                try:
                    key = ka[j + 1][1].decode("ascii")
                except UnicodeDecodeError:
                    raise Refused("K001")
                if not key or any(c not in KEYS for c in key):
                    raise Refused("K001")
                if any(k == p[0] for p in pairs):
                    raise Refused("S008")
                self.colscope(rows, k, [key])
                pairs.append((k, key))
            hit = [i for i, r in enumerate(rows) if all(r[k] == v for k, v in pairs)]
            if len(hit) != 1:
                raise Refused("V004")
            if len(pairs) > 1:
                for k, _ in pairs:
                    rest = [i for i, r in enumerate(rows) if all(r[k2] == v for k2, v in pairs if k2 != k)]
                    if rest == hit:
                        raise Refused("S008")
            return hit[0], ("key", tuple(pairs))
        if a[0] != "num" or "." in a[1] or int(a[1]) < 1:
            raise Refused("S006")
        r = int(a[1])
        if r > len(rows):
            raise Refused("V002")
        return r - 1, ("pos", r)

    def f_cell(self, args, params):
        self.arity(args, 3)
        self.params("cell", params, {})
        t = self.ev(args[0], "table")
        header, rows = t[1]
        k = self.column(header, args[2])
        r, rk = self.rowpos(header, rows, args[1])
        return ("bytes", rows[r][k].encode("utf-8"), ("Cell", t[3], rk, k))

    def f_header(self, args, params):
        self.arity(args, 2)
        self.params("header", params, {})
        t = self.ev(args[0], "table")
        a = args[1]
        if a[0] != "num" or "." in a[1] or int(a[1]) < 1:
            raise Refused("S006")
        k = int(a[1])
        if k > len(t[1][0]):
            raise Refused("V002")
        return ("bytes", t[1][0][k - 1].encode("utf-8"), ("Header", t[3], k))

    def f_number(self, args, params):
        self.arity(args, 1)
        self.params("number", params, {})
        b = self.ev(args[0], "bytes")
        try:
            q = decimal(b[1].decode("ascii"))
        except UnicodeDecodeError:
            q = None
        if q is None:
            raise Refused("V005")
        return ("num", q, q, ("Decimal", b[2]))

    def column_values(self, fn, args, params):
        self.arity(args, 2)
        self.params(fn, params, {})
        m = self.ev(args[0], "table", "sel")
        base = m if m[0] == "table" else m[1]
        header, rows = base[1]
        k = self.column(header, args[1])
        idx = range(len(rows)) if m[0] == "table" else m[2]
        vals = []
        for i in idx:
            q = decimal(rows[i][k])
            if q is None:
                raise Refused("V005")
            vals.append(q)
        return vals, (fn, m[-1], k)

    def f_sum(self, args, params):
        vs, key = self.column_values("sum", args, params)
        s = sum(vs, Fraction(0))
        return ("num", s, s, key)

    def f_mean(self, args, params):
        vs, key = self.column_values("mean", args, params)
        if not vs:
            raise Refused("V003")
        s = sum(vs, Fraction(0)) / len(vs)
        return ("num", s, s, key)

    def f_max(self, args, params):
        vs, key = self.column_values("max", args, params)
        if not vs:
            raise Refused("V003")
        return ("num", max(vs), max(vs), key)

    def f_min(self, args, params):
        vs, key = self.column_values("min", args, params)
        if not vs:
            raise Refused("V003")
        return ("num", min(vs), min(vs), key)

    def f_widen(self, args, params):
        self.arity(args, 1)
        t = self.params("widen", params, {"tolerance": "pos"})["tolerance"]
        x = self.ev(args[0], "num")
        if isinstance(x[3], tuple) and x[3][:1] == ("Widened",):   # widen of a widened value: one use of its base
            base, total = x[3][1], x[3][2] + t
        else:
            base, total = x[3], t
        f = self.form(x)
        if f is not None:   # x + t * e_base
            terms = dict(f[1])
            terms[base] = terms.get(base, 0) + t
            self.forms[("Widened", base, total)] = (f[0], terms)
        return ("num", x[1] - t, x[2] + t, ("Widened", base, total))

    def f_difference(self, args, params):
        self.arity(args, 2)
        self.params("difference", params, {})
        a = self.ev(args[0], "num", "count")
        b = self.ev(args[1], "num", "count")
        if a[0] != b[0]:
            raise Refused("U001")
        if a[-1] == b[-1]:
            raise Refused("S008")
        if a[0] == "count":
            v = Fraction(a[1] - b[1])
            return ("num", v, v, ("Diff", a[-1], b[-1]))
        key, fa, fb = ("Diff", a[-1], b[-1]), self.form(a), self.form(b)
        if fa is not None and fb is not None:   # subtract the forms; a symbol on both sides cancels
            terms = {v: fa[1].get(v, 0) - fb[1].get(v, 0) for v in set(fa[1]) | set(fb[1])}
            terms = {v: q for v, q in terms.items() if q != 0}
            a0, r = fa[0] - fb[0], sum(abs(q) for q in terms.values())
            self.forms[key] = (a0, terms)
            return ("num", a0 - r, a0 + r, key)
        return ("num", a[1] - b[2], a[2] - b[1], key)

    def compare(self, op, args, params):
        self.arity(args, 1)
        c = self.params(op, params, {"c": "any"})["c"]
        m = self.ev(args[0], "num", "count", "share")
        if m[0] == "num":
            lo, hi = m[1], m[2]
        elif m[0] == "count":
            lo = hi = Fraction(m[1])
            dom = (0, None)
        else:
            lo = hi = Fraction(*m[1])
            dom = (0, 1)
        if m[0] != "num":
            a, b = dom
            if (op == "exceeds" and c < a) or (op == "atleast" and c <= a) or (op == "below" and b is not None and c > b) or (op == "atmost" and b is not None and c >= b):
                raise Refused("S008")
            if (op == "exceeds" and b is not None and c >= b) or (op == "atleast" and b is not None and c > b) or (op == "below" and c <= a) or (op == "atmost" and c < a):
                raise Refused("S011")
        yes = {"exceeds": lo > c, "below": hi < c, "atleast": lo >= c, "atmost": hi <= c}[op]
        no = {"exceeds": hi <= c, "below": lo >= c, "atleast": hi < c, "atmost": lo > c}[op]
        if not yes and not no:
            raise Refused("V006")
        if no:
            raise Refused("V001")
        return ("bool", ("Cmp", op, m[-1], c))

    def f_exceeds(self, a, p):
        return self.compare("exceeds", a, p)

    def f_below(self, a, p):
        return self.compare("below", a, p)

    def f_atleast(self, a, p):
        return self.compare("atleast", a, p)

    def f_atmost(self, a, p):
        return self.compare("atmost", a, p)


def esc(b):
    out = ""
    for x in b:
        out += '\\"' if x == 34 else "\\\\" if x == 92 else chr(x) if 32 <= x < 127 else f"\\x{x:02x}"
    return '"' + out + '"'


def value_text(m):
    if m[0] == "bytes":
        return "= " + esc(m[1])
    if m[0] == "count":
        return f"= {m[1]} (Exact)"
    if m[0] == "share":
        return f"= {m[1][0]}/{m[1][1]} (Exact)"
    if m[0] == "bool":
        return "holds"
    if m[1] == m[2]:
        return f"= {show(m[1])} (Exact)"
    return f"lies within [{show(m[1])}, {show(m[2])}] (Interval)"


def check_is(m, toks):
    kind, v = toks[0]
    if m[0] == "bool":
        raise Refused("S010")
    if m[0] == "bytes":
        if kind != "s":
            raise Refused("S010")
        if v != m[1]:
            raise Refused("V001")
        return
    if kind == "s":
        raise Refused("S010")
    ratio = len(toks) > 1 and toks[1] == ("p", "/")
    if m[0] == "share":
        if not ratio:
            raise Refused("S010")
        if (int(v), int(toks[2][1])) != m[1]:
            raise Refused("V001")
        return
    if ratio:
        raise Refused("S010")
    if m[0] == "num" and m[1] != m[2]:
        raise Refused("S010")
    unit = toks[1][1] if len(toks) > 1 and toks[1][0] == "w" else None
    if unit is not None or (m[0] == "count" and "." in v):
        raise Refused("U002")
    got = m[1] if m[0] == "num" else Fraction(m[1])
    if Fraction(v) != got:
        raise Refused("V001")


def syntax_ok(toks):
    """Written ratios are checked when the line is read, before anything is computed."""
    for i, t in enumerate(toks):
        if t == ("p", "/"):
            a, b = toks[i - 1][1], toks[i + 1][1]
            if a.startswith("-") or b.startswith("-") or int(b) == 0:
                raise Refused("P007")


def run(program: bytes, files: dict):
    r = Run(files)
    out = []
    for ln, line in enumerate(program.decode("ascii").split("\n"), start=1):
        if not line.strip() or line.startswith("#"):
            continue
        try:
            if line.startswith("file "):
                name, h = line[5:].split(" = sha256:")
                if h not in files:
                    r.env[name] = "refused"
                    raise Refused("F001")
                r.env[name] = ("file", h)
                continue
            if line.startswith("let "):
                name, rhs = line[4:].split(" = ", 1)
                syntax_ok(tokens(rhs))
                if name in r.env:
                    raise Refused("N002")
                try:
                    r.env[name] = r.mean(P(tokens(rhs)).expr())
                except Refused:
                    r.env[name] = "refused"
                    raise
                continue
            body = line[6:]
            toks = tokens(body)
            syntax_ok(toks)
            p = P(toks)
            e = p.expr()
            rest = toks[p.i:]
            m = r.mean(e)
            if m[0] not in ("bytes", "count", "share", "num", "bool"):
                raise Refused("S009")
            if rest:
                check_is(m, rest[1:])
            out.append([ln, "formed", value_text(m), m])
        except Refused as x:
            out.append([ln, "refused", x.code, None])
    # call 4: one value, one tolerance, in one program
    tol = {}

    def walk(key, acc):
        if isinstance(key, tuple):
            if key and key[0] == "Widened":
                acc.append((key[1], key[2]))
            for k in key:
                walk(k, acc)
    found = []
    for o in out:
        acc = []
        if o[1] == "formed":
            walk(o[3][-1], acc)
            for inner, t in acc:
                tol.setdefault(inner, set()).add(t)
        found.append(acc)
    mixed = {k for k, v in tol.items() if len(v) > 1}
    for o, acc in zip(out, found):
        if o[1] == "formed" and any(k in mixed for k, _ in acc):
            o[1], o[2] = "refused", "S012"
    return [(o[0], o[1], o[2]) for o in out]

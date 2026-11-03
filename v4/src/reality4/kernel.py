"""The meaning-and-support function of Reality v4, and the checker around it.

One function, `meaning`, gives every expression its sort and its value. Sorts come only from
the fixed readers and computations below; no author, literal or declaration assigns one (check
1). Every meaning carries the set of files whose bytes its value was computed from, recorded by
the store at the read; a claim forms only if that set equals the set of files its sort names
(check 2). A `let` is evaluated once, where it is written (call by value), and its work is
counted there. Each statement starts with fresh bounds, and nothing a statement does changes
what a later one finds, except the one-set rule for tolerances (Patsak's call 4), which is
applied to the whole program after every statement has been checked."""

import sys
from fractions import Fraction

from . import bids101, witness
from .exact import Surd, SurdMix, sqrt as exact_sqrt
from . import readers as R
from .keys import PinError, check_pins, invisible, is_header_name, is_key, lookalikes, skeleton
from .readers import Refusal
from .sorts import File, Lit, S, esc, files, nodes, render
from .syntax import Call, Dec, Int, Name, Ratio, Str, SyntaxRefusal, parse_line, split_program

MAX_BYTES_SLICE = 4096
RECURSION = 10_000
UNITS = ("s",)


class M:
    """A meaning: what kind of thing an expression is, its sort, its value, and the files its
    value was read from."""
    __slots__ = ("kind", "sort", "val", "aux", "reads")

    def __init__(self, kind, sort, val=None, aux=None, reads=frozenset()):
        self.kind, self.sort, self.val, self.aux, self.reads = kind, sort, val, aux, frozenset(reads)


class Num:
    """A number with its precision (a point or an interval; `recorded` when the bytes give it
    under a standard's unit with no precision) and its time frame: `frame` is the recording a
    time point is measured in (from the first volume of its BOLD file); durations have none."""
    __slots__ = ("lo", "hi", "unit", "recorded", "frame", "aff")

    def __init__(self, lo, hi, unit=None, recorded=False, frame=None, aff=None):
        self.lo, self.hi, self.unit, self.recorded, self.frame = lo, hi, unit, recorded, frame
        # v4 SPEC 5.2: the affine form a0 + sum(a_v * e_v), e_v in [-1, 1], one symbol per
        # widened value identity; None for a point (its form is the point itself)
        self.aff = aff

    def form(self):
        if self.aff is not None:
            return self.aff
        return (self.lo, {}) if self.lo == self.hi else None

    def precision(self):
        p = "Exact" if self.lo == self.hi else "Interval"
        if self.recorded:
            p = f"Recorded[{self.unit}]" if self.lo == self.hi else f"Recorded[{self.unit}], Interval"
        return p


def fmt(q) -> str:
    if isinstance(q, Surd):
        return q.text(fmt)
    if abs(q.numerator) >= 10 ** 3000 or q.denominator >= 10 ** 3000:
        fail("R009", "bounds", "a value with more than 3000 digits cannot be printed (Reality bounds)")
    d, k2, k5 = q.denominator, 0, 0
    while d % 2 == 0:
        d //= 2
        k2 += 1
    while d % 5 == 0:
        d //= 5
        k5 += 1
    if d != 1:
        return f"{q.numerator}/{q.denominator}"
    k = max(k2, k5)
    if k > 3000:
        fail("R009", "bounds", "a value with more than 3000 digits cannot be printed (Reality bounds)")
    n = abs(q.numerator) * (10 ** k) // q.denominator
    s = str(n).rjust(k + 1, "0")
    s = s[:-k] + "." + s[-k:] if k else s
    return ("-" if q < 0 else "") + s


def unit_str(q, unit):
    return fmt(q) + (f" {unit}" if unit else "")


def fmt_msg(q: Fraction) -> str:
    """A number inside a refusal message. Messages never raise R009 (SPEC 9.9): a number too long
    to print is named, not printed, so the code never depends on message wording."""
    try:
        return fmt(q)
    except Refusal:
        return "(a number too long to print)"


def unit_msg(q, unit):
    return fmt_msg(q) + (f" {unit}" if unit else "")


def fail(code, item, msg):
    raise Refusal(code, item, msg)


def union(*ms):
    out = set()
    for m in ms:
        out |= m.reads
    return out


# ---- argument helpers ----------------------------------------------------------------------

def nargs(c: Call, lo, hi=None):
    hi = lo if hi is None else hi
    if not lo <= len(c.args) <= hi:
        want = f"{lo}" if lo == hi else f"{lo} to {hi}"
        fail("S003", "1", f"{c.fn}() takes {want} arguments, not {len(c.args)}")


NUM_CONDS = {"ge": lambda q, c: q >= c, "gt": lambda q, c: q > c, "le": lambda q, c: q <= c, "lt": lambda q, c: q < c}
NUM_SIGNS = {"ge": ">=", "gt": ">", "le": "<=", "lt": "<"}


def slots(c: Call, declared: dict):
    """Parameters: only the slots the computation declares, each given once, none missing (no
    defaults). Returns {slot: (value, unit written or None)}."""
    got = {}
    for p in c.params:
        if p.slot not in declared:
            fail("S004", "1", f"{c.fn}() has no slot {p.slot!r}; its slots are {', '.join(declared) or 'none'} (unknown arguments are refused)")
        if p.slot in got:
            fail("S004", "2", f"{c.fn}(): slot {p.slot!r} is given twice")
        if isinstance(p.value, (Int, Dec)):
            v = Fraction(p.value.v)
        elif isinstance(p.value, Ratio):
            v = Fraction(p.value.n, p.value.d)
        else:
            fail("S004", "1", f"{c.fn}(): slot {p.slot!r} takes a number")
        if p.unit is not None and p.unit not in UNITS:
            fail("U002", "1", f"{c.fn}(): {p.unit!r} is not a unit any reader of Reality v4 gives")
        if declared[p.slot] == "positive" and v <= 0:
            fail("S004" if v < 0 else "S008", "1", f"{c.fn}(): slot {p.slot!r} takes a number greater than 0" + ("; a tolerance of 0 widens nothing, so it does not bear on the answer" if v == 0 else ""))
        got[p.slot] = (v, p.unit)
    for s in declared:
        if s not in got:
            fail("S005", "1", f"{c.fn}(): the slot {s!r} is empty; Reality has no default values, so every slot is written")
    return got


def unit_matches(fn, slot, written, unit):
    """Patsak's call 6: the unit of a cutoff or tolerance is written, never filled in."""
    if unit is None and written is not None:
        fail("U002", "5", f"{fn}(): the value has no unit, and the slot {slot!r} writes {written!r}; a unit comes only from a standard's reader")
    if unit is not None and written != unit:
        fail("U004", "1", f"{fn}(): the value is in {unit}, so the slot {slot!r} must be written with its unit ({slot} = ... {unit}); Reality does not fill a unit in")


def nid(m):
    """v4 SPEC 5.1: the identity of a number; a count of rows is its selection's (files, row set),
    a BIDS value its dataset's manifest and the paths it reads (bids_id); a value with no
    positions of its own is identified by its sort, as in v3."""
    meta = m.sort.meta
    if meta and meta[0] in ("num", "rows", "count"):
        return meta[1]
    if meta and meta[0] == "widen":
        return ("Widened", meta[1], meta[2])
    return ("sort", m.sort)


def is_root(m):
    """v4 SPEC 7.2 (O4): a standard deviation, or a widen of one, is a root by its sort, whatever its bytes give."""
    meta = m.sort.meta
    return bool(meta) and meta[0] in ("num", "widen") and isinstance(meta[1], tuple) and meta[1][:1] in (("SampleSD",), ("PopulationSD",))


def is_square(m):
    """v4 SPEC 7.2 (Part B 5b): a variance, a widen of one or a difference of two is in its column's unit squared, by its sort
    (a difference's first argument may itself be widened: its identity is ("Widened", base, t), 28 Oct 2026)."""
    meta = m.sort.meta
    i = meta[1] if meta and meta[0] in ("num", "widen") else None
    while isinstance(i, tuple) and i[:1] in (("Difference",), ("Widened",)):
        i = i[1]
    return isinstance(i, tuple) and i[:1] in (("SampleVariance",), ("PopulationVariance",))


def cell_decimal(cell):
    """v4 SPEC 7.3 (O3): a where condition's reading of a cell; a number beyond the reader's bounds has no answer
    yet, like a cell that is not a number, so another condition may drop the row whatever the order."""
    try:
        return R.decimal(cell)
    except Refusal:
        return None


def position(a, what):
    if not isinstance(a, Int) or a.v < 1:
        fail("S006", "1", f"{what} is a position: a whole number from 1")
    return a.v


def text_arg(a, what):
    if not isinstance(a, Str):
        fail("S006", "1", f"{what} is written as a string")
    return a.v


def bom_first(what):
    fail("T011", "2", f"{what}: the file starts with a byte-order mark, so its first header name could begin with U+FEFF or not, two readings; the other columns and every cell have one reading")


def scope_ok(strings, what, code="K002"):
    """Patsak's call 2, one rule everywhere: no invisible or format character, and no two
    distinct strings with equal UTS #39 skeletons, among the strings a claim reads as names."""
    seen = {}
    for s in strings:
        c = invisible(s)
        if c is not None:
            fail("K004", "1", f"{what}: {esc(s.encode())} holds U+{ord(c):04X}, a character that cannot be seen or told from its absence (principle section 10.3, Patsak's call of 25 Oct)")
        sk = skeleton(s)
        if sk in seen and seen[sk] != s:
            fail(code, "1", f"{what}: {esc(seen[sk].encode())} and {esc(s.encode())} look alike (UTS #39 confusables 18.0.0 skeletons, with the spec's case folding); a claim that tells them apart by bytes alone is refused (principle section 10.3)")
        seen.setdefault(sk, s)


def cell_literal(lit: bytes, what):
    """A byte literal compared with cells: it must be bytes a cell can hold, or the condition
    could never bear on the answer."""
    try:
        return lit.decode("utf-8")   # a tab or line break matches no cell: W1 (witness)
    except UnicodeDecodeError:
        fail("S008", "1", f"{what}: {esc(lit)} is not UTF-8, and no cell of a table Reality reads is, so the condition cannot bear on the answer")


def _by(name, tag, f, **kw):
    """The kernel function c_<name>: an aggregate (Checker._agg) of f(checker, values)."""
    return lambda self, c: self._agg(c, name, tag, lambda qs: f(self, qs), **kw)


class Checker:
    def __init__(self, store: R.Store):
        self.store = store
        self.env = {}   # name -> ('file', h, line) | ('dataset', h, line) | ('let', M, line) | ('refused', line)
        self.exprs = {}   # let name -> its inlined expression (v4 SPEC 4.1)
        self.colres = {}  # id(Str) of a column header -> its position on the real bytes (BB's call 02)
        self.prefix = []  # (B0304) each let and claim so far, formed or refused: (its inlined expression, the files it read)
        self.st_ix = None   # (C02) the index in prefix of the let or claim being checked: where() rows are kept by it

    # ---- the meaning-and-support function --------------------------------------------------

    def meaning(self, e):
        if isinstance(e, Name):
            b = self.env.get(e.id)
            if b is None:
                fail("N001", "1", "a name used here is not declared above")
            if b[0] == "refused":
                fail("N003", "1", f"a name used here comes from the statement on line {b[1]}, which was refused")
            if b[0] == "let":
                self.used_logs.append(b[3])
            if b[0] == "file":
                return M("file", S(File(b[1])), b[1])
            if b[0] == "dataset":
                return M("dataset", S(File(b[1])), b[1])
            return b[1]
        if isinstance(e, (Int, Dec)):
            fail("S001", "5", "a number written where a value is needed is a stipulation: values come from bytes (principle item 5); a written number is allowed only in a slot a computation declares (slot = number), as a position, or after 'is'")
        if isinstance(e, Str):
            fail("S001", "5", "text written where a value is needed is a stipulation: values come from bytes (principle item 5)")
        h = getattr(self, "c_" + e.fn, None)
        if h is None:
            fail("S002", "1", f"{e.fn!r} is not a computation of Reality v4; no reader or computation produces such a sort, so this has no form (principle section 2: a sentence of a sort no reader produces cannot be written)")
        self.store.steps.add(1)
        return h(e)

    def first(self, c, n, *kinds):
        """nargs, no slots, then the first argument's meaning, of one of these kinds."""
        nargs(c, n)
        slots(c, {})
        return self.sub(c.args[0], *kinds, what=f"{c.fn}()'s {'argument' if n == 1 else 'first argument'}")

    def sub(self, e, *kinds, what="argument"):
        m = self.meaning(e)
        if m.kind not in kinds:
            fail("S007", "1", f"{what} must be {' or '.join(KIND_NAMES[k] for k in kinds)}, not {KIND_NAMES[m.kind]}")
        return m

    # ---- files and plain TSV ---------------------------------------------------------------

    def table(self, h, kind="tsv"):
        data = self.store.text(h)
        if (kind, h) not in self.store._memo:   # its cells cost at least this (a cell per tab and per line); refuse before building it
            self.store.room(80 * ((data.count(b"\t") if kind == "tsv" else 0) + data.count(b"\n") - 1))
        return self.store._cached((kind, h), lambda t: (len(t.rows) + len(data) // 64 + 1, 0), size=_table_size, make=lambda: (R.parse_tsv if kind == "tsv" else R.parse_csv)(data, h, R.Steps(), room=self.store.room))

    c_csv = lambda self, c: self.c_tsv(c, "csv")   # noqa: E731 (the CSV file-level reader of principle section 12, SPEC 6.5)

    def c_tsv(self, c, kind="tsv"):
        f = self.first(c, 1, "file")
        return M("table", S(kind.upper() + "[", File(f.val), "]"), self.table(f.val, kind), None, {f.val})

    # ---- JSON, the file-level reader of principle section 11 -------------------------------

    def c_json(self, c):
        f = self.first(c, 1, "file")
        v = self.store.json_file(f.val)
        return M("json", S("JSON[", File(f.val), "]", meta=("json", f.val, ())), v, None, {f.val})

    def json_value(self, sort, v, reads):
        if isinstance(v, (dict, list)):
            return M("json", sort, v, None, reads)
        if isinstance(v, Fraction):
            sort.meta = ("num", ("JSON",) + sort.meta[1:])
            return M("num", sort, Num(v, v), None, reads)   # no unit: RFC 8259 gives none
        if isinstance(v, str):
            return M("bytes", sort, v.encode("utf-8"), None, reads)
        word = {True: "true", False: "false", None: "null"}[v]
        fail("J004", "1", f"the JSON value is {word}; v4 states JSON numbers, strings, and members or items of objects and arrays, and {word} is none of these")

    def c_member(self, c):
        j = self.first(c, 2, "json")
        key = text_arg(c.args[1], "member()'s key")
        try:
            k = key.decode("utf-8")
        except UnicodeDecodeError:
            fail("S008", "1", f"member(): {esc(key)} is not UTF-8, and no key Reality's JSON reader reads is, so it cannot bear on the answer")
        if not isinstance(j.val, dict):
            fail("V002", "1", "member(): the JSON value is an array, not an object; use item()")
        self.store.steps.add(len(j.val) + 1)
        scope_ok([k], "member()'s key")
        sk = skeleton(k)
        for x in j.val:   # a sibling key that looks like the named one (principle section 10.3)
            if x != k and skeleton(x) == sk:
                fail("K003", "1", f"member(): the object's keys {esc(k.encode())} and {esc(x.encode())} look alike; a claim that tells them apart by bytes alone is refused (principle section 10.3)")
        if k not in j.val:
            fail("V002", "1", f"member(): the object has no member {esc(key)}")
        jm = j.sort.meta
        return self.json_value(S("Member[", Lit(key), " of ", j.sort, "]", meta=("json", jm[1], jm[2] + (("m", key),))), j.val[k], j.reads)

    def c_item(self, c):
        j = self.first(c, 2, "json")
        k = position(c.args[1], "item()'s position")
        if not isinstance(j.val, list):
            fail("V002", "1", "item(): the JSON value is an object, not an array; use member()")
        if k > len(j.val):
            fail("V002", "1", f"item(): the array has {len(j.val)} items, not {k}")
        jm = j.sort.meta
        return self.json_value(S(f"Item[{k} of ", j.sort, "]", meta=("json", jm[1], jm[2] + (("i", k),))), j.val[k - 1], j.reads)

    # ---- one NIfTI header, a file-level reader (principle section 1; v4 SPEC 7.6) ---------

    def c_nifti(self, c):
        f = self.first(c, 1, "file")
        hd, _ = self.store.nifti_file(f.val)
        return M("nifti", S(f"NIfTI-{hd.version}[", File(f.val), "]"), hd, None, {f.val})

    def c_dim(self, c):
        n = self.first(c, 2, "nifti")
        k = position(c.args[1], "dim()'s axis")
        if k > n.val.dim[0]:
            fail("V008", "1", f"dim(): the header has {n.val.dim[0]} dimensions; no byte gives a size along axis {k}")
        return M("count", S("Dim[", n.sort, f", {k}]"), n.val.dim[k], None, n.reads)

    def c_pixdim(self, c):
        n = self.first(c, 2, "nifti")
        k = position(c.args[1], "pixdim()'s axis")
        hd = n.val
        if k != 4:
            fail("S006", "1", "pixdim(): v4 reads pixdim along time only (axis 4); spatial units are not among Reality's units")
        if hd.dim[0] < 4:
            fail("V008", "1", f"pixdim(): the header has {hd.dim[0]} dimensions; no byte gives a time step")
        unit = R.TIME_UNITS.get(hd.xyzt_units & 0x38)
        if unit is None:
            fail("I005", "1", f"pixdim(): the header's time unit code is {hd.xyzt_units & 0x38}; NIfTI gives seconds only for 8 (s), 16 (ms) and 24 (us), so no byte gives this step a unit")
        if hd.pixdim[4] is None:
            fail("I005", "1", "pixdim(): pixdim[4] is NaN or infinite, which no unit makes a time")
        v = hd.pixdim[4] * unit   # the exact stored float, in seconds (Patsak 25 Oct: Recorded)
        return M("num", S("Pixdim[", n.sort, ", 4]", meta=("num", ("Pixdim", tuple(sorted(n.reads)), 4))), Num(v, v, "s", True), None, n.reads)

    def c_size(self, c):
        f = self.first(c, 1, "file")
        return M("count", S("ByteCount[", File(f.val), "]"), self.store.size(f.val), None, {f.val})

    def c_bytes(self, c):
        f = self.first(c, 3, "file")
        if not isinstance(c.args[1], Int) or c.args[1].v < 0:
            fail("S006", "1", "bytes(): the offset is a position: a whole number from 0")
        o, n = c.args[1].v, position(c.args[2], "bytes(): the length")
        if n > MAX_BYTES_SLICE:
            fail("R004", "bounds", f"bytes(): at most {MAX_BYTES_SLICE} bytes at a time (Reality bounds)")
        size = self.store.size(f.val)
        if o + n > size:
            fail("V002", "1", f"bytes(): the file has {size} bytes, so it has no bytes {o}..{o + n}")
        b = self.store.slice(f.val, o, n)
        return M("bytes", S("Bytes[", File(f.val), f", {o}..{o + n}]"), b, None, {f.val})

    def column(self, tab, a, what):
        """A column by position, or by header text; by text, every header is in the claim's
        scope (lookalikes and invisible characters refuse)."""
        if isinstance(a, Int):
            k = position(a, what)
            if k > len(tab.header):
                fail("V002", "1", f"{what}: the table has {len(tab.header)} columns, not {k}")
            return k
        if not isinstance(a, Str):
            fail("S006", "1", f"{what} is a column position (a whole number) or a header written as a string")
        try:
            name = a.v.decode("ascii")
        except UnicodeDecodeError:
            name = None
        if name is None or not is_header_name(name):
            fail("K001", "1", f"{what}: a column is named only by a header of ASCII letters, digits and '_'; address this one by position")
        hits = [i for i, x in enumerate(tab.header, start=1) if x == name]
        if tab.bom and hits[:1] == [1]:
            bom_first(what)
        if not hits:
            fail("V002", "1", f"{what}: no header is {esc(a.v)}")
        self.store.steps.add(len(tab.header))
        if len(hits) > 1:
            fail("K002", "1", f"{what}: the header {esc(a.v)} repeats (columns {', '.join(map(str, hits))}), so the name picks no single column; address it by position")
        scope_ok(tab.header, f"{what}: the headers")
        self.colres[id(a)] = (a, hits[0])   # a is kept, so its id is not reused
        return hits[0]

    def key_column_scope(self, tab, k, lit_strings, what):
        self.store.steps.add(len(tab.rows) + 1)
        vals = list(lit_strings)
        seen = set(vals)
        for r in tab.rows:
            if r[k - 1] not in seen:
                seen.add(r[k - 1])
                vals.append(r[k - 1])
        scope_ok(vals, what)

    def colname(self, base, k):
        """How a column is printed: in a BIDS participant set, 1.0.1 defines participant_id and
        nothing else, so every other column is printed as an ExtraCell column."""
        if base.kind == "pset":
            return "participant_id" if k - 1 == base.aux[2] else f"ExtraCell col {k}"
        return f"col {k}"

    def sel_id(self, m):
        """v4 SPEC 5.1: a selection's identity is its files and the set of rows it selects; a
        recording set's, its dataset and the paths of the recordings it holds."""
        if m.kind == "rset":
            return ("BIDS", "BOLDRecordings", m.aux.mh, tuple(r.path for r in m.val))
        return tuple(sorted(m.reads)), frozenset(self.idx_of(m))

    def base_of(self, m):
        """(base meaning, table, conditions) for a table, a participant set or a selection."""
        if m.kind == "sel":
            return m.aux[0], m.aux[0].val, m.aux[1]
        return m, m.val, []

    def idx_of(self, m):
        if m.kind == "sel":
            return m.val
        return list(range(len(m.val.rows)))

    def c_rows(self, c):
        m = self.first(c, 1, "table", "pset")
        return M("count", S("RowCount[", m.sort, "]", meta=("rows", ("Count", self.sel_id(m)))), len(m.val.rows), None, m.reads)

    def c_count(self, c):
        m = self.first(c, 1, "table", "pset", "sel", "rset")
        return M("count", S("Count[", m.sort, "]", meta=("rows", ("Count", self.sel_id(m)))), len(m.val) if m.kind == "rset" else len(self.idx_of(m)), None, m.reads)

    def c_share(self, c):
        if len(c.args) not in (1, 2):
            fail("S003", "1", "share() takes a selection, or a selection and the selection it is a share of: share(sel) or share(sel, base)")
        slots(c, {})
        m = self.sub(c.args[0], "sel", what="share()'s argument")
        base, tab, conds = self.base_of(m)
        if len(c.args) == 1:
            if not tab.rows:
                fail("V003", "2", "share(): the set is empty, so no share of it has a value")
            return M("share", S("Share[", m.sort, " of ", base.sort, "]"), (len(m.val), len(tab.rows)), None, m.reads)
        o = self.sub(c.args[1], "table", "pset", "sel", what="share()'s second argument")
        obase, _, oconds = self.base_of(o)
        if obase is not base and obase.sort != base.sort:
            fail("S006", "1", "share(sel, base): base must select from the same table as sel")
        key = lambda t: (t[0], t[1], t[2])
        mine = [key(t) for t in conds]
        theirs = [key(t) for t in oconds]
        if any(t not in mine for t in theirs):
            fail("S006", "1", "share(sel, base): every condition of base must also be a condition of sel, so that sel is a part of base whatever the file holds")
        n = len(self.idx_of(o))
        if n == 0:
            fail("V003", "2", "share(sel, base): base selects no row, so no share of it has a value")
        return M("share", S("Share[", m.sort, " of ", o.sort, "]"), (len(m.val), n), None, m.reads | o.reads)

    def c_where(self, c):
        if len(c.args) < 2:
            fail("S003", "1", "where() takes a table, set or selection and at least one condition eq(column, \"bytes\") or ne(column, \"bytes\")")
        slots(c, {})
        inner = self.sub(c.args[0], "table", "pset", "sel", what="where()'s first argument")
        base, tab, conds = self.base_of(inner)
        conds = list(conds)
        for a in c.args[1:]:
            if isinstance(a, Call) and a.fn in NUM_CONDS and len(a.args) == 1:
                cut, cu = slots(a, {"c": "rational"})["c"]
                if cu is not None:
                    fail("U002", "5", f"{a.fn}(): a cell decimal has no unit, and the slot 'c' writes {cu!r}; a unit comes only from a standard's reader")
                k = self.column(tab, a.args[0], f"{a.fn}()'s column")
                conds.append((a.fn, k, cut, None))
                continue
            if not isinstance(a, Call) or a.fn not in ("eq", "ne") or len(a.args) != 2 or a.params:
                fail("S006", "1", "a condition is eq(column, \"bytes\"), ne(column, \"bytes\"), or ge/gt/le/lt(column, c = number)")
            k = self.column(tab, a.args[0], f"{a.fn}()'s column")
            lit = text_arg(a.args[1], f"{a.fn}()'s second argument")
            s = cell_literal(lit, f"{a.fn}()")
            conds.append((a.fn, k, lit, s))
        by_col = {}
        for op, k, lit, s in conds:
            if op in ("eq", "ne"):
                by_col.setdefault(k, []).append((op, lit, s))
        for k in sorted(by_col):
            cs = by_col[k]
            self.key_column_scope(tab, k, [s for _, _, s in cs], f"column {k}")
        # byte conditions first, then number conditions; a row whose cell a number condition cannot
        # read stays undecided and is dropped only if another condition is false on it, so the
        # verdict does not depend on the order the conditions are written in (v4 SPEC 7.3)
        idx, undecided = list(range(len(tab.rows))), {}
        for op, k, lit, s in sorted(conds, key=lambda t: t[0] in NUM_CONDS):
            self.store.steps.add(len(idx))   # v4 SPEC 9.1: the rows still selected when the condition runs
            if op in ("eq", "ne"):
                idx = [i for i in idx if (tab.rows[i][k - 1] == s) == (op == "eq")]
            else:
                qs = [(i, cell_decimal(tab.rows[i][k - 1])) for i in idx]
                self.store.steps.add(self.wide([lit] + [q for _, q in qs if q is not None]) * len(qs))   # one comparison per row
                undecided.update((i, min(undecided.get(i, (k, op)), (k, op))) for i, q in qs if q is None)
                idx = [i for i, q in qs if q is None or NUM_CONDS[op](q, lit)]
        for i, (k, op) in ((i, undecided[i]) for i in idx if i in undecided):
            R.decimal(tab.rows[i][k - 1])   # O3: a number beyond the reader's bounds refuses R007 here, in any order
            fail("V005", "1", f"{op}(): column {k} holds a cell that is not a decimal in a row it reads (row {i + 1} holds {esc(tab.rows[i][k - 1].encode())}); a comparison with a number has no answer there, every other condition keeps the row, and dropping it would be a choice no byte states")
        parts = []
        for op, k, lit, s in conds:
            cname = self.colname(base, k)
            if parts:
                parts.append(" and ")
            if op in NUM_CONDS:
                parts.append(f"{cname} {NUM_SIGNS[op]} {unit_str(lit, None)}")
            else:
                parts += [f"{cname} {'=' if op == 'eq' else '!='} ", Lit(lit)]
        self.store.account(72 * len(idx) + 64)   # each kept row number is 8 bytes and an object (v4 SPEC 9.4)
        r = self.st_ix   # (B0304; C02, review 3 02) for held(): by the statement that made the rows
        self.store.anon_by[r] = self.store.anon_by.get(r, 0) + 72 * len(idx) + 64
        return M("sel", S("Rows[", base.sort, " where ", *parts, "]"), idx, (base, conds), inner.reads)

    def c_cell(self, c):
        m = self.first(c, 3, "table")
        tab = m.val
        k = self.column(tab, c.args[2], "cell()'s column")
        r, rs = self.row(tab, c.args[1])
        return M("bytes", S("Cell[", m.sort, ", ", *rs, f", col {k}]", meta=("cell", tuple(sorted(m.reads)), r, k)), tab.rows[r][k - 1].encode("utf-8"), None, m.reads)

    def row(self, tab, a):
        if isinstance(a, Call) and a.fn == "key":
            self.store.steps.add(1)   # key() is a computation and charges its step (finding 20)
            if len(a.args) < 2 or len(a.args) % 2 or a.params:
                fail("S003", "1", "key() takes a column and a key, or several column-key pairs: key(column, \"key\", ...)")
            pairs = []
            for j in range(0, len(a.args), 2):
                k = self.column(tab, a.args[j], "key()'s column")
                lit = text_arg(a.args[j + 1], "key()'s key")
                try:
                    s = lit.decode("ascii")
                except UnicodeDecodeError:
                    s = None
                if s is None or not is_key(s):
                    fail("K001", "1", f"key(): {esc(lit)} is not a key; a key is one or more ASCII letters or digits (principle section 10.3)")
                self.key_column_scope(tab, k, [s], f"key() column {k}")
                pairs.append((k, lit, s))
            self.store.steps.add(len(tab.rows) + 1)   # one pass over the rows (v4 SPEC 9.1)
            hits = [i for i, r in enumerate(tab.rows) if all(r[k - 1] == s for k, _, s in pairs)]
            if len(hits) != 1:
                fail("V004", "2", f"key(): {len(hits)} rows hold this key; a key picks out exactly one row")
            # v4: idleness is structural (SPEC 2 item 2); a pair that only these bytes make
            # redundant is not idle, so the v3 data-dependent S008 is gone (finding 13)
            parts = [f"row {hits[0] + 1} (the row whose "]
            for j, (k, lit, _) in enumerate(pairs):
                parts += [(" and " if j else "") + f"col {k} is ", Lit(lit)]
            return hits[0], parts + [")"]
        r = position(a, "a row")
        if r > len(tab.rows):
            fail("V002", "1", f"the table has {len(tab.rows)} rows, not {r}")
        return r - 1, [f"row {r}"]

    def c_header(self, c):
        m = self.first(c, 2, "table")
        k = position(c.args[1], "header()'s column")
        if k > len(m.val.header):
            fail("V002", "1", f"the table has {len(m.val.header)} columns, not {k}")
        if k == 1 and m.val.bom:
            bom_first("header()")
        return M("bytes", S("Header[", m.sort, f", col {k}]", meta=("header", tuple(sorted(m.reads)), k)), m.val.header[k - 1].encode("utf-8"), None, m.reads)   # (B08) no reader in its identity, as Model.ident

    # ---- numbers and precision -------------------------------------------------------------

    def c_number(self, c):
        m = self.first(c, 1, "bytes")
        try:
            q = R.decimal(m.val.decode("ascii"))
        except UnicodeDecodeError:
            q = None
        if q is None:
            fail("V005", "1", f"number(): {esc(m.val)} is not a number under Reality's number reader (-?digits[.digits][e[+-]digits], ASCII, no leading zero; v4 SPEC 6.4)")
        return M("num", S("Decimal[", m.sort, "]", meta=("num", ("Decimal", m.sort.meta or m.sort))), Num(q, q), None, m.reads)

    def column_numbers(self, c, name, extra=0):
        m = self.first(c, 2 + extra, "table", "pset", "sel")
        base, tab, _ = self.base_of(m)
        k = self.column(tab, c.args[1], f"{name}()'s column")
        self.store.steps.add(len(tab.rows) + 1)
        col = []
        # v4 SPEC 6.3: only the selected rows are read; a non-decimal there refuses V005
        for i in self.idx_of(m):
            q = R.decimal(tab.rows[i][k - 1])
            if q is None:
                fail("V005", "1", f"{name}(): column {k} holds a cell that is not a decimal in a row it reads (row {i + 1} holds {esc(tab.rows[i][k - 1].encode())}); skipping a row would be a choice no byte states")
            col.append(q)
        self.store.steps.add(self.wide(col) * len(col))   # a sum, mean or variance: a few operations per value
        return m, self.colname(base, k), col

    def _agg(self, c, name, tag, value, empty=None, rset=True):
        """One number over a column's selected cells (SPEC 6.3), or over a recording set (Phase F)."""
        if rset and self.is_rset(c):
            return self.rset_agg(c, name, tag, value)
        m, k, qs = self.column_numbers(c, name)
        if empty and not qs:
            fail("V003", "2", f"{name}(): the set is empty, so it has no {empty}")
        v = value(qs)
        return M("num", S(f"{tag}[", m.sort, f", {k}]", meta=("num", (tag, self.sel_id(m), k))), Num(v, v), None, m.reads)

    def _variance(self, name, qs, ddof):
        n = len(qs)
        if n < ddof + 1:
            fail("V003", "2", f"{name}(): the set has {n} values; {'the sample convention needs at least 2' if ddof else 'the population convention needs at least 1'}")
        self.store.steps.add(n + 1)
        mu = sum(qs, Fraction(0)) / n
        return sum(((q - mu) ** 2 for q in qs), Fraction(0)) / (n - ddof)

    def _median(self, qs):
        n = len(qs)
        if n % 2 == 0:
            fail("V009", "2", f"median(): the set has an even number of values ({n}); the lower middle, the upper middle and their mean are three conventions, so 'the median' has more than one reading (use order())")
        self.store.steps.add(n * max(1, n.bit_length()) * (1 + self.wide(qs)) + 1)   # each comparison multiplies
        return sorted(qs)[n // 2]

    c_sample_variance = _by("sample_variance", "SampleVariance", lambda k, qs: k._variance("sample_variance", qs, 1), rset=False)
    c_population_variance = _by("population_variance", "PopulationVariance", lambda k, qs: k._variance("population_variance", qs, 0), rset=False)
    c_sample_sd = _by("sample_sd", "SampleSD", lambda k, qs: exact_sqrt(k._variance("sample_sd", qs, 1)), rset=False)
    c_population_sd = _by("population_sd", "PopulationSD", lambda k, qs: exact_sqrt(k._variance("population_sd", qs, 0)), rset=False)
    c_median = _by("median", "Median", lambda k, qs: k._median(qs), empty="median", rset=False)
    c_sum = _by("sum", "Sum", lambda k, xs: sum(xs, Fraction(0)))
    c_mean = _by("mean", "Mean", lambda k, xs: sum(xs, Fraction(0)) / len(xs), empty="mean")
    c_max = _by("max", "Max", lambda k, xs: max(xs), empty="maximum")
    c_min = _by("min", "Min", lambda k, xs: min(xs), empty="minimum")

    def _two_conventions(self, c):
        fail("V009", "2", f"{c.fn}(): the sample (n - 1) and the population (n) conventions are two readings of this name; write sample_{c.fn}() or population_{c.fn}()")

    c_variance = c_sd = c_pvariance = c_psd = _two_conventions

    def c_order(self, c):
        m, k, qs = self.column_numbers(c, "order", extra=1)
        j = position(c.args[2], "order()'s rank")
        n = len(qs)
        self.store.steps.add(n * max(1, n.bit_length()) * (1 + self.wide(qs)) + 1)   # each comparison multiplies
        if j > n:
            fail("V003", "2", f"order(): rank {j} is beyond the {n} values the set holds")
        q = sorted(qs)[j - 1]
        return M("num", S("Order[", m.sort, f", {k}, {j}]", meta=("num", ("Order", self.sel_id(m), k, j))), Num(q, q), None, m.reads)


    def as_num(self, m):
        if m.kind == "num":
            return m.val
        if m.kind == "count":
            return Num(Fraction(m.val), Fraction(m.val))
        return Num(Fraction(m.val[0], m.val[1]), Fraction(m.val[0], m.val[1]))

    def c_difference(self, c):
        a = self.first(c, 2, "num", "count")
        b = self.sub(c.args[1], "num", "count", what="difference()'s second argument")
        if a.kind != b.kind:
            fail("U001", "1", f"difference(): {KIND_NAMES[a.kind]} and {KIND_NAMES[b.kind]} are not one kind")
        if a.kind == "count":
            v = Fraction(a.val - b.val)
            return M("num", S("Difference[", a.sort, ", ", b.sort, "]", meta=("num", ("Difference", nid(a), nid(b)))), Num(v, v), None, union(a, b))
        x, y = a.val, b.val
        if is_root(a) or is_root(b) or any(isinstance(z, Surd) for z in (x.lo, x.hi, y.lo, y.hi)):
            fail("S006", "1", "difference(): a standard deviation is an exact square root, and v4 has no arithmetic between roots and other numbers (SPEC 7.2); compare it with a cutoff instead")
        if is_square(a) != is_square(b):
            fail("S006", "1", "difference(): a variance is in the square of its column's unit, and the other number is not, so their difference is not one kind (SPEC 7.2); subtract two variances, or compare it with a cutoff")
        if x.unit != y.unit:
            fail("U001", "1", f"difference(): {x.unit or 'no unit'} and {y.unit or 'no unit'} are not one kind")
        if x.frame is not None and y.frame is not None and x.frame != y.frame:
            fail("U003", "1", "difference(): the two times are measured from the first volumes of two different recordings; no byte relates the two frames, so their difference has no meaning")
        if x.frame is None and y.frame is not None:
            fail("U003", "1", "difference(): a duration minus a time point in a recording is neither a time nor a duration")
        frame = x.frame if y.frame is None else None
        fx, fy = x.form(), y.form()
        lo, hi, aff = x.lo - y.hi, x.hi - y.lo, None
        if fx is not None and fy is not None:   # v4 SPEC 5.2: one symbol per value, so x - x is 0
            terms = dict(fx[1])
            for v, c in fy[1].items():
                terms[v] = terms.get(v, Fraction(0)) - c
            terms = {v: c for v, c in terms.items() if c != 0}
            a0, rad = fx[0] - fy[0], sum((abs(c) for c in terms.values()), Fraction(0))
            lo, hi, aff = a0 - rad, a0 + rad, (a0, terms)
        return M("num", S("Difference[", a.sort, ", ", b.sort, "]", meta=("num", ("Difference", nid(a), nid(b)))), Num(lo, hi, x.unit, x.recorded or y.recorded, frame, aff), None, union(a, b))

    def c_widen(self, c):
        nargs(c, 1)
        t, tu = slots(c, {"tolerance": "positive"})["tolerance"]
        a = self.sub(c.args[0], "num", what="widen()'s argument")
        x = a.val
        unit_matches("widen", "tolerance", tu, x.unit)
        f = x.form()
        # O9 (v4 SPEC 5.3): a widened value widened again is its base value widened by the sum
        base, t0 = a.sort.meta[1:] if a.sort.meta and a.sort.meta[0] == "widen" else (nid(a), 0)
        aff = None
        if f is not None:
            terms = dict(f[1])
            terms[base] = terms.get(base, Fraction(0)) + t
            aff = (f[0], terms)
        return M("num", S("Widened[", a.sort, f", tolerance = {unit_str(t, x.unit)}]", meta=("widen", base, t0 + t)), Num(x.lo - t, x.hi + t, x.unit, x.recorded, x.frame, aff), None, a.reads)

    def compare(self, c, op):
        nargs(c, 1)
        cut, cu = slots(c, {"c": "rational"})["c"]
        a = self.sub(c.args[0], "num", "count", "share", what=f"{c.fn}()'s argument")
        x = self.as_num(a)
        unit_matches(c.fn, "c", cu, x.unit)
        yes, no = {"exceeds": (x.lo > cut, x.hi <= cut), "below": (x.hi < cut, x.lo >= cut),
                   "atleast": (x.lo >= cut, x.hi < cut), "atmost": (x.hi <= cut, x.lo > cut)}[op]
        if not yes and not no:
            fail("V006", "2", f"{c.fn}(): the value lies in [{unit_msg(x.lo, x.unit)}, {unit_msg(x.hi, x.unit)}], on both sides of {unit_msg(cut, x.unit)}; the claim has no single answer")
        if no:
            val = unit_msg(x.lo, x.unit) if x.lo == x.hi else f"[{unit_msg(x.lo, x.unit)}, {unit_msg(x.hi, x.unit)}]"
            fail("V001", "5", f"{c.fn}(): the claim says the value is {dict(exceeds='above', below='below', atleast='at least', atmost='at most')[op]} {unit_msg(cut, x.unit)}; computed from the bytes it is {'recorded as ' if x.recorded else ''}{val}")
        tag = {"exceeds": "Exceeds", "below": "Below", "atleast": "AtLeast", "atmost": "AtMost"}[op]
        return M("bool", S(f"{tag}[", a.sort, f", c = {unit_str(cut, x.unit)}]"), True, x, a.reads)

    c_exceeds = c_below = c_atleast = c_atmost = lambda self, c: self.compare(c, c.fn)   # noqa: E731

    # ---- BIDS 1.0.1 ------------------------------------------------------------------------

    def c_bids(self, c):
        m = self.first(c, 1, "dataset")
        ds = self.store.measured(("bids", m.val), lambda: bids101.read(self.store, m.val))
        return M("bids", S("BIDS-1.0.1[", File(m.val), f": {len(ds.subjects)} subjects, {len(ds.manifest)} files]"), ds, None, {m.val})

    def labels_distinct(self, labels, what):
        self.store.steps.add(len(labels) + 1)
        pair = lookalikes(labels)
        if pair:
            fail("K003", "1", f"the {what} labels {esc(pair[0].encode())} and {esc(pair[1].encode())} look alike (principle section 10.3); a claim reading them is refused")

    def c_participants(self, c):
        b = self.first(c, 1, "bids")
        ds = b.val
        if ds.participants is None:
            fail("V007", "1", "the dataset has no participants.tsv; BIDS 1.0.1 defines participants only there (section 8.11)")
        p, h, _, idc = ds.participants
        self.labels_distinct(sorted(set(ds.ptable_labels) | set(ds.subjects)), "participant")
        tab = self.bids_tsv(h, p)
        return M("pset", S("Participants[", b.sort, " from ", File(h), "]"), tab, ("pset", ds, idc), b.reads | {h})

    def c_participant(self, c):
        nargs(c, 2)
        slots(c, {})
        ps = self.c_participants(Call("participants", c.args[:1], ()))
        lab = text_arg(c.args[1], "participant()'s label")
        ds = ps.aux[1]
        s = lab.decode("ascii", errors="replace")
        if not is_key(s):
            fail("K001", "1", f"participant(): {esc(lab)} is not a BIDS label (letters and digits, without 'sub-'; section 5)")
        if s not in ds.ptable_labels:
            fail("V004", "1", f"participant(): the dataset has no participant sub-{s}")
        r = ds.ptable_labels.index(s)
        return M("part", S("Participant[", ps.sort, f", sub-{s}]"), (ps.val, r), ps.aux, ps.reads)

    def c_extra(self, c):
        p = self.first(c, 2, "part")
        tab, r = p.val
        k = self.column(tab, c.args[1], "extra()'s column")
        if k - 1 == p.aux[2]:
            fail("S006", "1", "extra(): participant_id is the key BIDS defines, not an extra column")
        return M("bytes", S("ExtraCell[", p.sort, f", col {k}]"), tab.rows[r][k - 1].encode("utf-8"), None, p.reads)

    def c_recording(self, c):
        if len(c.args) < 3:
            fail("S003", "1", "recording() takes a BIDS dataset, a subject and a task label, optionally a run label, then optionally acq(\"label\") and rec(\"label\")")
        slots(c, {})
        b = self.sub(c.args[0], "bids", what="recording()'s first argument")
        ds = b.val
        want, pos = {}, ["sub", "task", "run"]
        for a in c.args[1:]:
            if isinstance(a, Str) and pos and not (want.keys() - {"sub", "task", "run"}):
                key, v = pos.pop(0), a.v
            elif isinstance(a, Call) and a.fn in ("acq", "rec") and len(a.args) == 1 and not a.params:
                key, v = a.fn, text_arg(a.args[0], f"{a.fn}()'s label")
            else:
                fail("S006", "1", "recording(): after the dataset come the subject, the task and optionally the run (strings), then optionally acq(\"label\") and rec(\"label\")")
            if key in want:
                fail("S004", "2", f"recording(): {key} is given twice")
            v = v.decode("ascii", errors="replace")
            ok = is_key(v) if key != "run" else (v != "" and set(v) <= set("0123456789"))
            if not ok:
                fail("K001", "1", f"recording(): {v!r} is not a BIDS {key} label (section 5)")
            want[key] = v
        if "sub" not in want or "task" not in want:
            fail("S005", "1", "recording(): the subject and the task are both written")
        self.bold_labels(ds)
        hits = [r for r in ds.recordings if dict(r.ents) == want]
        if len(hits) != 1:
            fail("V004", "2", f"recording(): {len(hits)} BOLD recordings have exactly the entities {' '.join(f'{k}-{v}' for k, v in want.items())}; exactly one is needed (a recording's run, acq and rec labels are part of its name and are written when it has them)")
        r = hits[0]
        name = " ".join(f"{k} {v}" for k, v in r.ents)
        return M("rec", S("BOLDRecording[", b.sort, f", {name}]"), r, ds, b.reads)

    def bold_labels(self, ds):
        """No two subject, task, acq or rec labels of the dataset's recordings look alike (K003)."""
        self.store.steps.add(4 * len(ds.recordings) + 1)   # the three label passes and the match (SPEC 9.1)
        self.labels_distinct(sorted(set(ds.subjects) | set(ds.ptable_labels)), "subject")
        for key in ("task", "acq", "rec"):
            self.labels_distinct(sorted({dict(r.ents)[key] for r in ds.recordings if key in dict(r.ents)}), key)

    def c_recordings(self, c):
        """Phase F (DESIGN 4, finding 29): the BOLD recordings of one task, optionally only those
        of the participants a selection of participants(b) picks. The join is 1.0.1's own key:
        participant_id "sub-<label>" matches a recording's sub entity (text line 1238)."""
        if len(c.args) not in (2, 3):
            fail("S003", "1", "recordings() takes a BIDS dataset and a task label, optionally then a selection of participants(dataset)")
        slots(c, {})
        b = self.sub(c.args[0], "bids", what="recordings()'s first argument")
        ds = b.val
        t = text_arg(c.args[1], "recordings()'s task label").decode("ascii", errors="replace")
        if not is_key(t):
            fail("K001", "1", f"recordings(): {t!r} is not a BIDS task label (section 5)")
        self.bold_labels(ds)
        recs = [r for r in ds.recordings if dict(r.ents)["task"] == t]
        sort, reads = S("BOLDRecordings[", b.sort, f", task {t}]"), set(b.reads)
        if len(c.args) == 3:
            m = self.sub(c.args[2], "pset", "sel", what="recordings()'s third argument")
            base, tab, _ = self.base_of(m)
            if base.kind != "pset" or base.aux[1] is not ds:
                fail("S006", "1", "recordings(): the third argument selects from participants() of the same dataset")
            idc = base.aux[2]
            self.labels_distinct(sorted(set(ds.ptable_labels) | set(ds.subjects)), "participant")
            subs = {tab.rows[i][idc][4:] for i in self.idx_of(m)}
            recs = [r for r in recs if r.sub in subs]
            sort, reads = S("BOLDRecordings[", b.sort, f", task {t}, of ", m.sort, "]"), reads | m.reads
        recs.sort(key=lambda r: r.ents)
        return M("rset", sort, recs, ds, reads)

    RSET_QUANTITIES = ("volumes", "events", "tr", "trials")
    wide = staticmethod(lambda qs: (1 + max((q.numerator.bit_length() + q.denominator.bit_length() for q in qs), default=0) // 64) ** 2 // 16)   # SPEC 9.1: extra steps per exact operation, W*W/16 for W 64-bit words [prov] (review 22)

    def is_rset(self, c):
        """Whether an aggregate's first argument is a recording set, read from the syntax (a
        recordings() call or a let name bound to one), so the table path is not evaluated twice."""
        a = c.args[0] if c.args else None
        if isinstance(a, Call):
            return a.fn == "recordings"
        b = self.env.get(a.id) if isinstance(a, Name) else None
        return b is not None and b[0] == "let" and b[1].kind == "rset"

    def rset_agg(self, c, name, tag, pick):
        """sum/mean/max/min over a recording set of one quantity from a closed list (DESIGN 4):
        volumes, events, tr, or trials with a trial type. Each keeps its unit and precision."""
        rs = self.meaning(c.args[0])
        q = c.args[1].v.decode("ascii", "replace") if len(c.args) >= 2 and isinstance(c.args[1], Str) else None
        if q not in self.RSET_QUANTITIES:
            fail("S006", "1", f"{name}() over recordings takes one of {', '.join(map(repr, self.RSET_QUANTITIES))} as its second argument")
        nargs(c, 3 if q == "trials" else 2)
        slots(c, {})
        lit = text_arg(c.args[2], "the trial type") if q == "trials" else None
        self.store.steps.add(len(rs.val) + 1)
        one = {"volumes": self.volumes_of, "events": self.events_of, "tr": self.tr_of, "trials": lambda rm: self.trials_of(rm, lit)}[q]
        vals = [one(M("rec", S("BOLDRecording[", rs.sort, "]"), r, rs.aux, rs.reads)) for r in rs.val]
        nums = [v.val if v.kind == "num" else Num(Fraction(v.val), Fraction(v.val)) for v in vals]
        reads = set(rs.reads).union(*(v.reads for v in vals))
        if not nums and name != "sum":
            fail("V003", "2", f"{name}(): the set of recordings is empty")
        v = pick([n.lo for n in nums]) if nums else Fraction(0)
        label = f"{q} {esc(lit)}" if lit is not None else q
        # check 2: the sort names every file the value was read from, in hash order
        files = [x for i, h in enumerate(sorted(reads - set(rs.reads))) for x in (", " if i else " from ", File(h))]
        # v4 SPEC 5.1: identified by its dataset and what each recording's value reads (bids_id), not by
        # file hashes: two subjects' events files with the same bytes are two values (fix pass R1)
        meta = ("num", (tag, label, rs.aux.mh, tuple(nid(x) for x in vals)))
        return M("num", S(f"{tag}[", rs.sort, f", {label}", *files, "]", meta=meta), Num(v, v, "s" if q == "tr" else None, any(n.recorded for n in nums)), None, reads)

    def bold_header(self, r):
        return self.store.nifti(r.val.h, r.val.path, full=False)

    def c_volumes(self, c):
        return self.volumes_of(self.first(c, 1, "rec"))

    def volumes_of(self, r):
        hd = self.bold_header(r)
        if hd.dim[0] < 4:
            fail("V008", "1", f"volumes(): the NIfTI header has {hd.dim[0]} dimensions; no byte gives a fourth, so there is no count of volumes")
        return M("count", S("VolumeCount[", r.sort, ", BOLD ", File(r.val.h), "]", meta=("count", bids_id(r, "VolumeCount", r.val.path))), hd.dim[4], None, r.reads | {r.val.h})

    def c_tr(self, c):
        return self.tr_of(self.first(c, 1, "rec"))

    def tr_of(self, r):
        _, ps, hs = r.val.meta["RepetitionTime"]   # every sidecar of the winning folder that sets it
        v = [self.store.json(h, p)["RepetitionTime"] for h, p in zip(hs, ps)][0]
        hd = self.bold_header(r)
        if not bids101.tr_consistent(v, hd):
            fail("B09", "reading rules", "tr(): RepetitionTime is not consistent with the BOLD header's pixdim[4]")
        meta = ("num", bids_id(r, "RepetitionTime", r.val.path, *ps))
        return M("num", S("RepetitionTime[", r.sort, ", BOLD ", File(r.val.h), *(x for i, h in enumerate(sorted(hs)) for x in (", " if i else ", from ", File(h))), "]", meta=meta), Num(v, v, "s", True), None, r.reads | {*hs, r.val.h})

    def events_table(self, r, fn):
        if r.val.events is None:
            fail("V007", "1", f"{fn}(): the recording has no events file")
        p, h = r.val.events
        return h, self.bids_tsv(h, p)

    def bids_tsv(self, h, p):
        """(H07, Opus 5.5 max2 review 07) A BIDS table (events, participants) is kept like a plain one (table()): refused
        before it is built when its cells alone pass the bound, then charged kernel._table_size once a program."""
        data = self.store.text(h, p)
        if ("bids-tsv", h) not in self.store._memo:
            self.store.room(80 * (data.count(b"\t") + data.count(b"\n") - 1))
        return self.store._cached(("bids-tsv", h), lambda t: (len(data.replace(b"\r\n", b"\n").decode("utf-8")) // 64 + 1, 0), size=_table_size,
                                  make=lambda: bids101.bids_tsv(data, h, p, R.Steps(), self.store.room))   # the steps R.parse_tsv charges, each call

    def event(self, c, col, label):
        r = self.first(c, 2, "rec")
        i = position(c.args[1], f"{c.fn}()'s row")
        h, tab = self.events_table(r, c.fn)
        if i > len(tab.rows):
            fail("V002", "1", f"{c.fn}(): the events file has {len(tab.rows)} rows, not {i}")
        q = R.decimal(tab.rows[i - 1][col])
        meta = ("num", bids_id(r, label, r.val.events[0], i))
        if col == 0:
            self.bold_header(r)
            frame = (r.aux.mh, r.val.ents)
            return M("num", S(f"{label}[", r.sort, ", from the first volume of BOLD ", File(r.val.h), ", ", File(h), f" row {i}]", meta=meta), Num(q, q, "s", True, frame), None, r.reads | {h, r.val.h})
        return M("num", S(f"{label}[", r.sort, ", ", File(h), f" row {i}]", meta=meta), Num(q, q, "s", True), None, r.reads | {h})

    c_onset = lambda self, c: self.event(c, 0, "EventOnset")   # noqa: E731 (kernel functions by table)
    c_duration = lambda self, c: self.event(c, 1, "EventDuration")   # noqa: E731
    c_events = lambda self, c: self.events_of(self.first(c, 1, "rec"))   # noqa: E731

    def events_of(self, r):
        h, tab = self.events_table(r, "events")
        return M("count", S("EventCount[", r.sort, ", ", File(h), "]", meta=("count", bids_id(r, "EventCount", r.val.events[0]))), len(tab.rows), None, r.reads | {h})

    def c_trials(self, c):
        return self.trials_of(self.first(c, 2, "rec"), text_arg(c.args[1], "trials()'s trial type"))

    def trials_of(self, r, lit):
        s = cell_literal(lit, "trials()")
        h, tab = self.events_table(r, "trials")
        ks = [i for i, x in enumerate(tab.header) if x == "trial_type"]
        if len(ks) != 1:
            fail("V002", "1", "trials(): the events file has no trial_type column (BIDS 1.0.1 section 8.5)")
        k = ks[0] + 1
        self.key_column_scope(tab, k, [s], "trial_type")
        n = sum(1 for row in tab.rows if row[k - 1] == s)
        return M("count", S("EventCount[", r.sort, ", ", File(h), " where trial_type = ", Lit(lit), "]", meta=("count", bids_id(r, "TrialCount", r.val.events[0], lit))), n, None, r.reads | {h})

    # ---- statements ------------------------------------------------------------------------

    def inline(self, e):
        """The expression with every let name replaced by its own expression (SPEC 4.1)."""
        if isinstance(e, Name):
            b = self.env.get(e.id)
            if b is not None and b[0] == "let" and e.id in self.exprs:
                return self.exprs[e.id]
            return e
        if isinstance(e, Call):
            return Call(e.fn, tuple(self.inline(a) for a in e.args), e.params)
        return e

    def claim(self, st):
        m = self.meaning(st.expr)
        if m.kind not in ("bytes", "count", "share", "num", "bool"):
            fail("S009", "1", f"a claim states a value or a comparison; {KIND_NAMES[m.kind]} is neither")
        named = files(m.sort)
        log, gate = self.actual_reads()
        extra = sorted((m.reads | log) - set(named))
        idle = [h for h in named if h not in m.reads or h not in log | gate]
        listed = set()
        for h in named:
            if h in self.store._manifests:
                listed |= self.store._manifests[h]
        ungated = sorted(gate - listed - set(named))
        if ungated:
            fail("C002", "floor", f"check 2: checking a dataset read sha256:{ungated[0]}, which no manifest the claim's sort names lists (a refusal, and a bug report against the reader)")
        if extra:
            fail("C001", "floor", f"check 2: the value was computed from sha256:{extra[0]}, which the claim's sort does not name; the sort and the dependency set disagree (a refusal, and a bug report against one of them)")
        if idle:
            fail("C001", "floor", f"check 2: the claim's sort names sha256:{idle[0]}, but its value was not computed from it; the sort and the dependency set disagree (a refusal, and a bug report against one of them)")
        witness.check(self, self.inline(st.expr))   # after check 2: v4 SPEC 4.3
        value = self.render(m)
        if st.lit is not None:
            self.check_is(m, st.lit)
        return m, named, value

    def actual_reads(self):
        """(value reads, gate reads) behind the current statement: the store's logs for this
        statement plus those recorded when the let names it uses were evaluated."""
        log, gate = set(self.store.log), set(self.store.gate)
        for lg, gt in self.used_logs:
            log |= lg
            gate |= gt
        return frozenset(log), frozenset(gate)

    def render(self, m):
        if m.kind == "bytes":
            return "= " + esc(m.val)
        if m.kind == "count":
            return f"= {m.val}"
        if m.kind == "share":
            k, n = m.val
            return f"= {k}/{n}"
        if m.kind == "bool":
            return "holds of the recorded value" if m.aux.recorded else "holds"
        x = m.val
        if x.lo == x.hi:
            return ("is recorded as " if x.recorded else "= ") + unit_str(x.lo, x.unit)
        return ("is recorded within " if x.recorded else "lies within ") + f"[{unit_str(x.lo, x.unit)}, {unit_str(x.hi, x.unit)}]"

    def check_is(self, m, lit):
        kind = lit[0]
        if m.kind == "bool":
            fail("S010", "1", "a comparison claim takes no 'is'; it holds or it is refused")
        if m.kind == "bytes":
            if kind != "str":
                fail("S010", "1", "this value is bytes; write 'is \"...\"'")
            if lit[1] != m.val:
                fail("V001", "5", f"the claim writes {esc(lit[1])}; the bytes are {esc(m.val)}")
            return
        if kind == "str":
            fail("S010", "1", "this value is a number; write it as a number")
        if m.kind == "share":
            if kind != "ratio":
                fail("S010", "1", "a share is written as k/n, the count over the size of its set")
            if (lit[1], lit[2]) != m.val:
                fail("V001", "5", f"the claim writes {lit[1]}/{lit[2]}; computed from the bytes the share is {m.val[0]}/{m.val[1]} (shares are compared exactly as written, not reduced)")
            return
        if kind == "ratio":
            fail("S010", "1", "only a share is written as k/n")
        if m.kind == "num" and m.val.lo != m.val.hi:
            fail("S010", "2", "this value is an interval; 'is' with one number has no single meaning here")
        want, unit = lit[1], lit[2]
        if m.kind == "num":
            if unit != m.val.unit:
                if m.val.unit is None:
                    fail("U002", "5", f"the bytes give this number without a unit, and the claim writes {unit!r}; a unit comes only from a standard's reader (for example BIDS 1.0.1: event onsets in seconds from the first volume of the recording's BOLD file, which a claim must name)")
                fail("U002", "1", f"the value's unit is {m.val.unit}; the claim writes {unit or 'no unit'}")
            got = m.val.lo
        else:
            if unit is not None or "." in lit[3]:
                fail("U002", "1", "a count is a whole number without a unit")
            got = Fraction(m.val)
        if want != got:
            fail("V001", "5", f"the claim writes {fmt_msg(want)}; computed from the bytes it is {fmt_msg(got)}")

    def statement(self, st):
        self.st_ix = len(self.prefix) if st.kind in ("let", "claim") else None
        try:
            return self.statement1(st)
        finally:   # (B0304) a let's own expression object, which a claim using it holds (decide.LETS)
            if st.kind in ("let", "claim"):
                b = self.env.get(st.name) if st.kind == "let" else None
                e = self.exprs[st.name] if b and b[0] == "let" and b[2] == st.line else self.inline(st.expr)
                self.prefix.append((e, frozenset().union(*self.actual_reads())))

    def statement1(self, st):
        self.used_logs = []
        if st.kind in ("file", "dataset", "let"):
            if st.name in self.env and self.env[st.name][0] != "refused":
                fail("N002", "1", f"the name is already declared on line {self.env[st.name][2]}; a name stands for one thing")
            if st.name in self.env:
                fail("N002", "1", "the name was used by a refused statement above; a name stands for one thing")
            if st.kind == "let":
                m = self.meaning(st.expr)
                self.exprs[st.name] = self.inline(st.expr)
                self.env[st.name] = ("let", m, st.line, self.actual_reads())
            else:
                self.store.path(st.hash)   # F001 for every declared file, used or not
                self.env[st.name] = (st.kind, st.hash, st.line)
            return None
        return self.claim(st)


def bids_id(r, what, *read):
    """v4 SPEC 5.1: a BIDS value of recording r is identified by its dataset's manifest and the
    manifest paths (and rows) it reads, not by file hashes: two files with the same bytes at two
    paths are two values."""
    return ("BIDS", what, r.aux.mh) + read


def number_uses(sort):
    """(identity, tolerance) for every number a formed statement uses (v4 SPEC 5.3): the value
    directly under widen() at its tolerance; a number under no widen() at 0; the parts of a
    widened value are not uses of their own; widen(widen(x, a), b) is one use of x at a + b."""
    out, stack = set(), [(sort, False)]
    while stack:
        x, inside = stack.pop()
        if not isinstance(x, S):
            continue
        meta = x.meta
        if meta and meta[0] == "widen":
            out.add((meta[1], meta[2]))
            inside = True
            while isinstance(x.parts[1], S) and x.parts[1].meta and x.parts[1].meta[0] == "widen":
                x = x.parts[1]   # O9: a widen directly inside a widen is part of this one use
        elif meta and meta[0] == "num" and not inside:
            out.add((meta[1], Fraction(0)))
        stack.extend((p, inside) for p in x.parts)
    return out


KIND_NAMES = {"file": "a file", "dataset": "a dataset manifest", "table": "a TSV table", "sel": "a selection of rows",
              "pset": "a BIDS participant set", "part": "a BIDS participant", "bids": "a BIDS dataset",
              "rec": "a BIDS recording", "rset": "a set of BIDS recordings", "bytes": "bytes", "count": "a count", "share": "a share", "num": "a number",
              "bool": "a comparison", "json": "a JSON object or array", "nifti": "a NIfTI header"}
ITEMS = ("bounds", "floor", "reading rules", "text", "bug")


def _table_size(t):
    """Accounted bytes of a parsed table (v4 SPEC 9.4): 80 per cell plus its length, 64 per row."""
    return 64 + sum(64 + sum(80 + len(c) for c in r) for r in [t.header] + t.rows)


MAX_LINE_OUTPUT = 1 << 20        # [prov] v4 SPEC 9.3
MAX_PROGRAM_OUTPUT = 64 << 20    # [prov] v4 SPEC 9.3


def refusal_line(ln, e):
    item = e.item if e.item in ITEMS else "item " + e.item
    return f"line {ln}: refused [{e.code}, {item}]: {e.msg}"


def no_verdict(why):
    return None, [f"no verdict: {why}. The machine running the checker is a floor like the bytes (principle section 1, trusted base); nothing was checked or refused"]


def check(program: bytes, store: R.Store):
    """Check a program. Returns (accepted: True | False | None for no verdict, lines)."""
    old, old_digits = sys.getrecursionlimit(), sys.get_int_max_str_digits()
    try:
        sys.setrecursionlimit(RECURSION)
        sys.set_int_max_str_digits(0)   # Reality's own digit bounds apply, not the interpreter's
        check_pins()
        store.begin_program()
        return _check(program, store)
    except PinError as e:
        return no_verdict(str(e))
    except MemoryError:
        return no_verdict("the machine ran out of memory")
    except RecursionError:
        return no_verdict("the interpreter's stack ran out")
    finally:
        sys.setrecursionlimit(old)
        sys.set_int_max_str_digits(old_digits)


def _check(program, store):
    try:
        lines = split_program(program)
    except SyntaxRefusal as e:
        return False, [f"line {e.line}: refused [{e.code}, item 1]: {e.msg}", "refused: the program is not Reality text"]
    ck = Checker(store)
    results = []    # (line, 'formed', printed lines, widened (sort, tolerance) pairs) | (line, 'refused', text)
    total = 0       # bytes of output so far (v4 SPEC 9.3)
    counted, stated = 0, False

    def count_refusals():
        nonlocal total, counted
        for r in results[counted:]:
            if r[1] == "refused":
                total += len(r[2].encode("utf-8", "backslashreplace")) + 1
        counted = len(results)

    for ln, text in lines:
        count_refusals()
        try:
            st = parse_line(text, ln)
            if st is None:
                continue
            stated = True
        except SyntaxRefusal as e:
            results.append((ln, "refused", f"line {ln}: refused [{e.code}, item 1]: {e.msg}"))
            continue
        store.begin()
        try:
            try:
                res = ck.statement(st)
            except (Refusal, SyntaxRefusal, MemoryError, RecursionError):
                raise
            except Exception as e:  # a bug in the checker: the statement does not form
                raise Refusal("X001", "bug", f"internal error {type(e).__name__}; nothing formed (please report)") from None
        except SyntaxRefusal as e:
            results.append((ln, "refused", f"line {ln}: refused [{e.code}, item 1]: {e.msg}"))
            continue
        except Refusal as e:
            results.append((ln, "refused", refusal_line(ln, e)))
            if st.kind in ("file", "dataset", "let") and st.name not in ck.env:
                ck.env[st.name] = ("refused", ln)
            continue
        if res is not None:
            m, named, value = res
            labels = {h: f"#{i}" for i, h in enumerate(named, start=1)}
            prec = f" ({m.val.precision()})" if m.kind == "num" else (" (Exact)" if m.kind in ("count", "share") else "")
            text_lines = [f"line {ln}: formed: {render(m.sort, labels)} {value}{prec}"] + [f"  {labels[h]} = sha256:{h}" for h in named]
            size = sum(len(t.encode("utf-8", "backslashreplace")) + 1 for t in text_lines)
            if size > MAX_LINE_OUTPUT:
                results.append((ln, "refused", refusal_line(ln, Refusal("R014", "bounds", f"the formed statement would print {size} bytes; Reality prints at most {MAX_LINE_OUTPUT} bytes per statement (Reality bounds, v4 SPEC 9.3)"))))
                continue
            if total + size > MAX_PROGRAM_OUTPUT:
                results.append((ln, "refused", refusal_line(ln, Refusal("R011", "bounds", f"the program's output would pass {MAX_PROGRAM_OUTPUT} bytes here (Reality bounds, v4 SPEC 9.3)"))))
                continue
            total += size
            widened = number_uses(m.sort)
            results.append((ln, "formed", text_lines, widened))
            continue
    if not stated and not results:   # O10: 'accepted' would state nothing
        return False, ["line 0: refused [P011, item 1]: the program has no statement (only blank lines and comments), so there is nothing to accept", "refused: the program is not Reality text"]
    # Patsak's call 4: one program is one set (spec section 10.2 (ii)); one value, one tolerance;
    # v4 SPEC 5.3: grouped by value identity, and an exact use is tolerance 0 (Patsak, 25 Oct).
    tols = {}
    for r in results:
        if r[1] == "formed":
            for key, tol in r[3]:
                tols.setdefault(key, set()).add(tol)
    mixed = {s for s, ts in tols.items() if len(ts) > 1}
    out, refused = [], 0
    for r in results:
        if r[1] == "formed" and mixed and any(key in mixed for key, _ in r[3]):
            r = (r[0], "refused", refusal_line(r[0], Refusal("S012", "6", "this program uses one value (the same computation on the same positions of the same files) with two different tolerances, an exact use counting as tolerance 0; a program is one set of claims, and a set uses one accuracy profile per value (spec section 10.2 (ii), Patsak's call 4, v4 SPEC 5.3)")))
        if r[1] == "refused":
            out.append(r[2])
            refused += 1
            continue
        out.extend(r[2])
    out.append("accepted" if refused == 0 else f"refused ({refused} statement{'s' if refused != 1 else ''})")
    return refused == 0, out

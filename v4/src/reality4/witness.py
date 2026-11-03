"""Witnesses (v4 SPEC 4): a claim forms only if readable inputs, read by the checker's own readers and
evaluated by its own computations, show that (W1) every computed value has two different answers and
(W2) every part changes its computation's answer. decide.py decides both exactly for part T
(SPEC-EXACT); this module holds what it shares: the in-memory store, evaluation on made-up inputs,
W2's parts and the made-up BIDS datasets. A statement outside part T refuses S013 (phase 7: the
search that decided it before is deleted; its frozen, untrusted copy is under tests/, for the tools)."""

import hashlib
import os
from fractions import Fraction

from . import readers as R
from .syntax import Call, Dec, Int, Name, Ratio, Str

NO_ANSWER_FNS = frozenset({"bids", "participant", "recording", "acq", "rec"})   # sorts, not values
TABLE_FNS = frozenset({"where", "cell", "header", "sum", "mean", "max", "min", "rows", "count", "share",
                       "sample_variance", "population_variance", "sample_sd", "population_sd", "order", "median"})
MAX_WITNESS_STEPS = 50_000_000   # SPEC 4.5 [prov]


class MemStore(R.Store):
    """A store whose files are byte strings in memory (the witness candidates)."""

    def __init__(self, blobs, base=None):
        self.blobs, self.base = blobs, base   # (B0304) base: the program's store, for the files a certificate does not vary
        self.by_hash = {h: h for h in blobs}
        self.roots, self.hints, self._found, self._memo, self._sizes, self._manifests = [], {}, {}, {}, {}, {}
        self.begin_program()
        self.begin()

    def locate(self, h):
        return h if h in self.blobs or self.base is not None and self.base.locate(h) is not None else None

    def _b(self, h):
        """(B0304) A file's bytes; one the certificate does not vary, the program's (the text its memo holds, if any)."""
        if h not in self.blobs:
            b = self.base
            self.blobs[h] = b._b(h) if isinstance(b, MemStore) else b._memo.get(("text", h)) or open(b.path(h), "rb").read()
        return self.blobs[h]

    def size(self, h):
        self.path(h)
        self.log.add(h)
        if h in self.blobs or isinstance(self.base, MemStore):
            return len(self._b(h))
        return os.path.getsize(self.base.path(h))   # (B0304) the program's file, not read whole

    def nifti(self, h, what, full):
        self.path(h, what)
        self.log.add(h)
        d = self._b(h)
        return self._nifti(h, what, full, len(d) // 4096 + 1, lambda m: R.nifti_read(None, what.endswith(".gz"), what, full, d, m))   # (B05) as Store.nifti

    def slice(self, h, o, n):
        self.path(h)
        self.log.add(h)
        self.steps.add(n // 64 + 1)
        return self._b(h)[o:o + n]

    def text(self, h, what=None):
        self.path(h, what)
        self.log.add(h)
        d = self._b(h)
        if len(d) > R.MAX_TEXT_FILE:
            raise _TooLarge()   # a candidate beyond the file bound is no readable input
        d = d.whole if isinstance(d, Periodic) else d
        return self._cached(("text", h), lambda d: (len(d) // 64 + 1, len(d)), lambda: d, lambda d: len(d) + 64)


class Periodic:
    """A certificate's raw file of n bytes, byte i = (7i + 1 + 31·seed) mod 256 (SPEC-EXACT 6): held as its rule, so
    size() and bytes() read any n up to 2^63 - 1; up to MAX_TEXT_FILE it is also its bytes and its real sha256."""

    def __init__(self, n, seed):
        self.n, self.cycle = n, bytes((7 * i + 1 + 31 * seed) % 256 for i in range(256))
        self.args = (n, seed)   # (BLD, decide.plain) rebuilt from these, the same file
        self.whole = (self.cycle * (n // 256 + 1))[:n] if n <= R.MAX_TEXT_FILE else None
        self.sha = hashlib.sha256(self.whole if self.whole is not None else b"periodic %d %d" % (n, seed)).hexdigest()

    def __len__(self):
        return self.n

    def __getitem__(self, s):
        return bytes(self.cycle[i % 256] for i in range(*s.indices(self.n))) if self.whole is None else self.whole[s]


class _TooLarge(Exception):
    pass


# ---- analysis of the inlined expression -----------------------------------------------------

def walk(e):
    stack = [e]
    while stack:
        x = stack.pop()
        yield x
        if isinstance(x, Call):
            stack.extend(reversed(x.args))
            stack.extend(p.value for p in x.params)


def slot_of(e):
    """The file name a table-valued expression is read from, or None."""
    while isinstance(e, Call):
        if e.fn in ("tsv", "csv") and e.args and isinstance(e.args[0], Name):
            return e.args[0].id
        if e.fn == "participants" and e.args and ds_of(e.args[0]):
            return "P:" + ds_of(e.args[0])
        if e.fn in TABLE_FNS and e.args:
            e = e.args[0]
        else:
            return None
    return None


def ds_of(e):
    """The dataset name a BIDS value is read from, or None."""
    while isinstance(e, Call) and e.args and e.fn in ("bids", "participants", "participant", "recording", "recordings"):
        if e.fn == "bids":
            return e.args[0].id if isinstance(e.args[0], Name) else None
        e = e.args[0]
    return None


def rec_ents(c):
    """recording(b, sub, task[, run], acq(..), rec(..)) -> its entities, as the kernel reads them."""
    want, pos = {}, ["sub", "task", "run"]
    for a in c.args[1:]:
        if isinstance(a, Str) and pos:
            want[pos.pop(0)] = a.v.decode("ascii", "replace")
        elif isinstance(a, Call) and a.fn in ("acq", "rec") and a.args and isinstance(a.args[0], Str):
            want[a.fn] = a.args[0].v.decode("ascii", "replace")
    return want


def dec_text(q: Fraction):
    """The shortest decimal text for q, or None if q has no finite decimal."""
    d, k = q.denominator, 0
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    if d != 1:
        return None
    while (q * 10 ** k).denominator != 1:
        k += 1
    n = q * 10 ** k
    sign = "-" if n < 0 else ""
    s = str(abs(n.numerator)).rjust(k + 1, "0")
    return sign + (s[:-k] + "." + s[-k:] if k else s)


def _nii(dims, tr, unit=8, data=True):
    """A NIfTI-1 header (and, with data, its zero image) for dims and a time step in `unit`."""
    import struct
    b = bytearray(352)
    struct.pack_into("<i", b, 0, 348)
    struct.pack_into("<8h", b, 40, len(dims), *dims, *[1] * (7 - len(dims)))
    struct.pack_into("<2h", b, 70, 2, 8)
    struct.pack_into("<8f", b, 76, 1, 1, 1, 1, float(tr), 0, 0, 0)
    struct.pack_into("<f", b, 108, 352.0)
    b[123] = unit | 2
    b[344:348] = b"n+1\x00"
    n = 1
    for x in dims:
        n *= x
    return bytes(b) + b"\x00" * (n if data else 0)


def _fresh():
    import itertools
    for n in itertools.count(1):   # (H04) never runs out: a, ..., z, aa, ..., zzzz, ...
        for t in itertools.product("abcdefghijklmnopqrstuvwxyz", repeat=n):
            yield "".join(t)


# ---- evaluation -----------------------------------------------------------------------------

def answer(m):
    if m.kind == "count":
        return ("count", m.val)
    if m.kind == "share":
        return ("share", Fraction(*m.val))   # the share, not its two counts
    if m.kind == "bytes":
        return ("bytes", m.val)
    if m.kind == "num":
        x = m.val
        return ("num", x.lo, x.hi, x.unit, x.recorded)
    if m.kind == "sel":
        return ("sel", tuple(m.val))
    if m.kind in ("table", "pset"):
        return ("sel", tuple(range(len(m.val.rows))))   # a table is the selection of all its rows
    if m.kind == "rset":
        return ("rset", tuple(r.path for r in m.val))
    if m.kind == "bool":
        return ("bool", True)
    if m.kind == "json":
        return ("json", _canon(m.val))
    return None


def _canon(v):
    if isinstance(v, dict):
        return ("obj", tuple(sorted((k, _canon(x)) for k, x in v.items())))
    if isinstance(v, list):
        return ("arr", tuple(_canon(x) for x in v))
    return ("v", type(v).__name__, v)


def _same(got, a, b):
    """(G03) a let's later use b answers as its first use a, node by node."""
    if isinstance(a, Call) and isinstance(b, Call):
        if id(a) in got:
            got[id(b)] = got[id(a)]
        for x, y in zip(a.args, b.args):
            _same(got, x, y)


class _Recorder:
    def __init__(self, checker_cls, store, env, lets=None):
        self.ck = checker_cls(store)
        self.ck.env = env
        self.ck.exprs = {}
        self.got, self.lm = {}, {}
        orig = self.ck.meaning

        def meaning(e):
            k = (lets or {}).get(id(e))
            if k is not None and k[0] is e:   # (G03) a let: read once, in its own statement (its own text total), as the kernel does
                if k[1] in self.lm:
                    m, first = self.lm[k[1]]
                    _same(self.got, first, e)
                    return m
                saved, store.text_total = store.text_total, 0
                try:
                    m = orig(e)
                finally:
                    store.text_total = saved
                self.lm[k[1]] = (m, e)
            else:
                m = orig(e)
            if isinstance(e, Call):
                a = answer(m)
                if a is not None:
                    self.got[id(e)] = a
            return m
        self.ck.meaning = meaning


def evaluate(checker_cls, expr, names, assignment, budget, lets=None, held=0, pre=None):
    """Evaluate expr with each file name bound to the candidate bytes in assignment. Returns
    {id(sub-expression): answer} (the top comparison answers ('bool', False) when it does not
    hold), or None when the evaluation refuses."""
    blobs, env = {}, {}
    for n in names:
        b = assignment[n]
        if isinstance(b, tuple):   # a candidate dataset
            blobs.update(b[0])
            env[n] = ("dataset", b[1])
            continue
        h = b.sha if isinstance(b, Periodic) else hashlib.sha256(b).hexdigest()
        blobs[h] = b
        env[n] = ("file", h, 0)
    st = MemStore(blobs, pre and pre[2])
    st.prog_bytes = held   # (H03) the memory the program holds before the statement (SPEC-EXACT 1)
    rec = _Recorder(checker_cls, st, env, lets)
    if pre:   # (B0304, Argon review 2 03 and 04) the earlier statements on these files, run again on the candidate in order
        env.update((n, b) for n, b in pre[1].items() if n not in env)
        st._memo, st._sizes, st.prog_seen = dict(pre[3]), dict(pre[4]), set(pre[5])
        rec.lm.update(pre[6])   # (D02, review 4 02) a let on none of these files: the program's value, not run again
        mods, todo = {}, [expr]   # the judged statement's node of a let (renamed, decide.rename; changed, decide.subst, first) in its place
        while todo:   # every node (subexprs keeps only computed values, not a let's table)
            x = todo.pop()
            if not isinstance(x, Call):
                continue
            todo.extend(x.args)
            k = (lets or {}).get(id(x))
            if k is not None and k[0] is x:
                w = k[1]
                while isinstance(w, tuple):
                    w = w[1]
                if w not in mods or isinstance(k[1], tuple) and not isinstance(lets[id(mods[w])][1], tuple):
                    mods[w] = x
        for p in pre[0]:
            st.begin()
            try:
                rec.ck.meaning(mods.get(id(p), p))
            except (R.Refusal, _TooLarge):
                pass   # refused (a file past MAX_TEXT_FILE: R003 before it is read); its charges so far stay, as the kernel's
            except (MemoryError, RecursionError):
                raise
            except Exception:
                budget[0] += st.steps.n
                return None
            budget[0] += st.steps.n
    st.begin()
    try:
        rec.ck.meaning(expr)
    except R.Refusal as e:
        budget[0] += st.steps.n
        if e.code == "V001" and isinstance(expr, Call) and expr.fn in ("exceeds", "below", "atleast", "atmost"):
            rec.got[id(expr)] = ("bool", False)
        else:   # its finished parts still answer, unless a reader rejects the input: then it is not readable (4.1)
            rec.got = {} if e.code[:1] in "TJIBMF" else rec.got
            rec.got.pop(id(expr), None)
            rec.got["refused"] = e.code
        return rec.got
    except (MemoryError, RecursionError):
        raise   # the machine's limit, not an answer: the kernel prints no verdict (v4 SPEC 9.4)
    except Exception:
        budget[0] += st.steps.n
        return None
    budget[0] += st.steps.n
    return rec.got


def subexprs(expr):
    """Computed sub-values, innermost first (post-order), each once."""
    out, seen = [], set()

    def go(e):
        if not isinstance(e, Call):
            return
        if e.fn in ("eq", "ne", "key", "ge", "gt", "le", "lt"):
            return
        if e.fn in ("tsv", "csv", "json", "nifti"):
            return
        if e.fn in NO_ANSWER_FNS:
            for a in e.args:
                go(a)
            return
        for a in e.args:
            go(a)
        if id(e) not in seen:
            seen.add(id(e))
            out.append(e)
    go(expr)
    return out


def parts(expr):
    """(node, modified node, description) for every removable part (SPEC 4.3 W2)."""
    out = []
    # share(sel, base) repeats base's conditions in sel (S006): such a condition is removed from both
    shares = {id(x.args[0]): x for x in walk(expr) if isinstance(x, Call) and x.fn == "share" and len(x.args) == 2 and all(isinstance(a, Call) and a.fn == "where" for a in x.args)}
    for x in walk(expr):
        if not isinstance(x, Call):
            continue
        if x.fn == "where" and len(x.args) >= 2:
            for i in range(1, len(x.args)):
                sh = shares.get(id(x))
                sh = sh if sh is not None and x.args[i] in sh.args[1].args[1:] and x.args.count(x.args[i]) == 1 else None
                mod = Call("share", (_drop(x, i), _drop(sh.args[1], sh.args[1].args.index(x.args[i]))), sh.params) if sh else _drop(x, i)
                out.append((sh or x, mod, f"the condition {_desc(x.args[i])}"))
        elif x.fn == "recordings" and len(x.args) == 3:
            out.append((x, Call("recordings", x.args[:2], x.params), "the participant filter"))
        elif x.fn == "widen" and x.args:
            out.append((x, x.args[0], "widen()"))
        elif x.fn == "cell" and len(x.args) == 3 and isinstance(x.args[1], Call) and x.args[1].fn == "key" and len(x.args[1].args) >= 4:
            ka = x.args[1].args
            for j in range(0, len(ka) - 1, 2):
                rest = ka[:j] + ka[j + 2:]
                out.append((x, Call("cell", (x.args[0], Call("key", rest, ()), x.args[2]), ()), f"the key part on {_desc(ka[j])}"))
    return out


def _drop(w, i):
    """where(...) without its i-th argument; with no condition left, its base."""
    rest = w.args[:i] + w.args[i + 1:]
    return Call("where", rest, w.params) if len(rest) >= 2 else rest[0]


def _path(e, node):
    """The calls from e down to node, outermost first."""
    if e is node:
        return [e]
    for a in (e.args if isinstance(e, Call) else ()):
        p = _path(a, node)
        if p:
            return [e] + p
    return []


def _subst(e, node, mod):
    if e is node:
        return mod
    if isinstance(e, Call):
        return Call(e.fn, tuple(_subst(a, node, mod) for a in e.args), e.params)
    return e


def _one_spelling(e, inner):
    """For share(where(where(B, c..), d..), base) whose inner where repeats a base condition (BB's call
    D4, exact-decision): the one spelling that says it, with sel's conditions in one where()."""
    for x in walk(e):
        if isinstance(x, Call) and x.fn == "share" and len(x.args) == 2 and all(isinstance(a, Call) and a.fn == "where" for a in x.args) \
                and x.args[0].args[0] is inner and inner.fn == "where" and any(c in x.args[1].args[1:] for c in inner.args[1:]):
            flat = Call("where", inner.args + x.args[0].args[1:], ())
            return f"; the inner where() says the base's condition a second time; the one spelling of this share is {_src(Call('share', (flat, x.args[1]), x.params))}"
    return ""


def _src(e):
    """e as written, for messages."""
    from .sorts import esc
    if isinstance(e, Call):
        return f"{e.fn}({', '.join([_src(a) for a in e.args] + [f'{p.slot} = {_src(p.value)}' + (f' {p.unit}' if p.unit else '') for p in e.params])})"
    return e.id if isinstance(e, Name) else esc(e.v) if isinstance(e, Str) else e.text if isinstance(e, Dec) else f"{e.n}/{e.d}" if isinstance(e, Ratio) else str(e.v)


def _desc(a):
    if isinstance(a, (Int, Str)):
        return f"column {a.v if isinstance(a, Int) else repr(a.v.decode('utf-8', 'replace'))}"
    return f"{a.fn}(...)" if isinstance(a, Call) else "?"


def _as_judged(e, checker):
    """The statement as it formed: two names bound to one hash are one slot (SPEC 4.1), and a
    column named by its header is the position it resolved to on the real bytes (BB's call 02)."""
    first = {}
    canon = {n: first.setdefault(checker.env.get(n, (n,))[:2], n) for n in sorted({x.id for x in walk(e) if isinstance(x, Name)})}

    def go(x):
        if isinstance(x, Call):
            return Call(x.fn, tuple(go(a) for a in x.args), x.params)
        return Name(canon[x.id]) if isinstance(x, Name) else Int(checker.colres[id(x)][1]) if id(x) in checker.colres else x
    return go(e)


def check(checker, expr):
    """Raise S008 / S011 / R013 unless W1 and W2 hold for expr (SPEC 4.3); S013 outside part T."""
    from .kernel import fail
    written, expr = expr, _as_judged(expr, checker)
    # slots in the order of their hashes, so the decision, and so R013, is the same under any renaming
    names = sorted({x.id for x in walk(expr) if isinstance(x, Name)}, key=lambda n: checker.env.get(n, (n,))[:2])
    if not names:
        return
    from . import decide as exact
    try:
        return exact.check(checker, expr, written, names)   # part T: decided exactly (SPEC-EXACT)
    except exact.NotT as x:   # outside part T (SPEC-EXACT 2; D5, phase 7): no search decides it
        fail("S013", "1", f"Reality cannot decide this kind of statement: it is outside the fragment SPEC-EXACT part T decides ({x}), so it is shown neither that the bytes bear on the answer nor that they do not")

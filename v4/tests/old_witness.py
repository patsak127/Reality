# FROZEN, UNTRUSTED TEST COPY of src/reality4/witness.py at commit 6f21606 (sha256 76100d70349340c34aa342515e704de6dbac3dc9f0ec528be1042704d73c822e).
# Exact-decision Phase 0 (plans/exact-decision-procedure.md section 7): the old W1/W2 search, kept so the
# differential harness (tools/exact_diff.py) can compare it with the live and, later, the exact decider.
# Not part of the trusted base and not imported by the checker. Only the three import lines differ from
# the original (absolute instead of relative); tests/test_exact_harness.py pins both facts.
"""Witnesses (v4 SPEC 4): a claim forms only if the checker has built readable inputs, read by
its own readers and evaluated by its own computations, on which (W1) every computed value has two
different answers and (W2) every part changes its computation's answer. A witness the readers
refuse does not count. That an idle value cannot form is an argument with conditions, not a theorem
(SPEC 4.4 item 12; tests/test_v4_bruteforce.py measures it); a weak family refuses more.

Scope: every statement. A BIDS dataset name's candidates are small made-up datasets built from
the statement's own labels, columns and cutoffs (SPEC 4.4 item 9); each must pass the whole BIDS
1.0.1 reader to count."""

import hashlib
from fractions import Fraction

from reality4 import readers as R
from reality4.syntax import Call, Dec, Int, Name, Param, Ratio, Str

NO_ANSWER_FNS = frozenset({"bids", "participant", "recording", "acq", "rec"})   # sorts, not values
TABLE_FNS = frozenset({"where", "cell", "header", "sum", "mean", "max", "min", "rows", "count", "share",
                       "sample_variance", "population_variance", "sample_sd", "population_sd", "order", "median"})
NUMERIC_FNS = frozenset({"sum", "mean", "max", "min", "sample_variance", "population_variance", "sample_sd", "population_sd", "order", "median"})
MAX_TYPES = 64          # row types per table slot (SPEC 4.4 item 1) [prov]
MAX_PAIR_TYPES = 16     # two-row tables are built from the first 16 types [prov]
MAX_WITNESS_STEPS = 50_000_000   # SPEC 4.5 [prov]
MAX_REAL = 1 << 20               # [prov] v4-fixes 14: the real bytes are a candidate up to this size


class MemStore(R.Store):
    """A store whose files are byte strings in memory (the witness candidates)."""

    def __init__(self, blobs):
        self.blobs = blobs
        self.by_hash = {h: h for h in blobs}
        self.roots, self.hints, self._found, self._memo, self._sizes, self._manifests = [], {}, {}, {}, {}, {}
        self.begin_program()
        self.begin()

    def locate(self, h):
        return h if h in self.blobs else None

    def size(self, h):
        self.path(h)
        self.log.add(h)
        return len(self.blobs[h])

    def nifti(self, h, what, full):
        self.path(h, what)
        self.log.add(h)
        d = self.blobs[h]
        return self._cached(("nifti", h, full, what.endswith(".gz")), lambda v: (len(d) // 4096 + 1, 0), lambda: R.nifti_read(None, what.endswith(".gz"), what, full, d), lambda v: 2048)

    def slice(self, h, o, n):
        self.path(h)
        self.log.add(h)
        self.steps.add(n // 64 + 1)
        return self.blobs[h][o:o + n]

    def text(self, h, what=None):
        self.path(h, what)
        self.log.add(h)
        d = self.blobs[h]
        if len(d) > R.MAX_TEXT_FILE:
            raise _TooLarge()   # a candidate beyond the file bound is no readable input
        return self._cached(("text", h), lambda d: (len(d) // 64 + 1, len(d)), lambda: d, lambda d: len(d) + 64)


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


def _as_csv(tsv: bytes) -> bytes:
    """The same candidate table written as CSV: a cell is quoted when it holds a comma, quote,
    tab or semicolon, so the CSV reader reads back exactly the TSV reader's cells."""
    def cell(c):
        return b'"' + c.replace(b'"', b'""') + b'"' if any(x in c for x in (b",", b'"', b"\t", b";")) else c
    return b"".join(b",".join(cell(c) for c in ln.split(b"\t")) + b"\n" for ln in tsv.split(b"\n")[:-1])


def _note(d, k, v):
    """Add v to the list d[k] once, keeping first-seen order (candidate order is SPEC 4.4's)."""
    lst = d.setdefault(k, [])
    if v not in lst:
        lst.append(v)


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


def colkey(a):
    if isinstance(a, Int):
        return ("pos", a.v)
    if isinstance(a, Str):
        return ("name", a.v)
    return None


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


class Plan:
    """Per table slot: the columns the statement names, their literals, which are numeric."""

    def __init__(self, expr):
        self.cols = {}       # slot -> {colkey: [literal bytes...]}
        self.numeric = {}    # slot -> set(colkey)
        self.raw = {}        # slot -> min length needed by bytes() (slots read raw)
        self.tsv_slots = set()
        self.csv_slots = set()
        self.rows = {}       # slot -> row numbers named by position (cell(t, r, k))
        self.json_paths = {} # slot -> paths named by member()/item() chains (SPEC 4.4 item 5)
        self.nifti_slots = set()
        self.cuts, self.tols = [], []
        self.bids = {}       # dataset name -> {"subs": [...], "recs": [entities...]}
        for x in walk(expr):
            if not isinstance(x, Call):
                continue
            d = ds_of(x.args[0]) if x.args and x.fn != "bids" else None
            if d is not None:
                info = self.bids.setdefault(d, {"subs": [], "recs": []})
                self.cols.setdefault("P:" + d, {})
                ev = self.events_slot(d) if x.fn in ("onset", "duration", "events", "trials") else None
                if x.fn in ("participant", "recording") and len(x.args) >= 2 and isinstance(x.args[1], Str):
                    lab = x.args[1].v.decode("ascii", "replace")
                    if lab not in info["subs"]:
                        info["subs"].append(lab)
                if x.fn == "recording" and rec_ents(x) not in info["recs"]:
                    info["recs"].append(rec_ents(x))
                if x.fn == "recordings" and len(x.args) >= 2 and isinstance(x.args[1], Str):
                    t = x.args[1].v.decode("ascii", "replace")
                    if t not in info.setdefault("tasks", []):
                        info["tasks"].append(t)
                q = x.args[1].v if x.fn in ("sum", "mean", "max", "min") and len(x.args) >= 2 and isinstance(x.args[1], Str) else None
                if q in (b"events", b"trials"):
                    self.events_slot(d)
                if q == b"trials" and len(x.args) == 3 and isinstance(x.args[2], Str):
                    _note(self.cols["E:" + d], ("name", b"trial_type"), x.args[2].v)
                if x.fn == "extra" and len(x.args) == 2 and colkey(x.args[1]):
                    self.cols["P:" + d].setdefault(colkey(x.args[1]), [])
                if x.fn == "duration":
                    ev.setdefault(("pos", 2), [])
                    self.numeric["E:" + d].add(("pos", 2))
                if x.fn in ("onset", "duration"):
                    if len(x.args) == 2 and isinstance(x.args[1], Int) and 1 <= x.args[1].v <= 100_000:
                        self.rows.setdefault("E:" + d, set()).add(x.args[1].v)
                if x.fn == "trials" and len(x.args) == 2 and isinstance(x.args[1], Str):
                    _note(ev, ("name", b"trial_type"), x.args[1].v)
            for p in x.params:
                v = p.value
                f = Fraction(v.v) if isinstance(v, Int) else v.v if isinstance(v, Dec) else Fraction(v.n, v.d) if isinstance(v, Ratio) else None
                if f is not None:
                    self.cuts.append(f)
                    self.tols += [abs(f)] if x.fn == "widen" else []
            if x.fn in ("member", "item"):
                ch = json_chain(x)
                if ch is not None:
                    _note(self.json_paths, ch[0], ch[1])
            if x.fn in ("nifti", "tsv", "csv") and x.args and isinstance(x.args[0], Name):
                getattr(self, x.fn + "_slots").add(x.args[0].id)
            if x.fn == "json" and x.args and isinstance(x.args[0], Name):
                self.json_paths.setdefault(x.args[0].id, [])
            if x.fn in ("size", "bytes") and x.args and isinstance(x.args[0], Name):
                need = 0
                if x.fn == "bytes" and len(x.args) == 3 and all(isinstance(a, Int) for a in x.args[1:]):
                    need = x.args[1].v + x.args[2].v
                self.raw[x.args[0].id] = max(self.raw.get(x.args[0].id, 0), need)
            s = slot_of(x.args[0]) if x.fn in TABLE_FNS and x.args else None
            if s is None:
                continue
            cols = self.cols.setdefault(s, {})
            if x.fn == "where":
                for c in x.args[1:]:
                    if isinstance(c, Call) and c.fn in ("ge", "gt", "le", "lt") and len(c.args) == 1:
                        k = colkey(c.args[0])
                        if k is not None:
                            cols.setdefault(k, [])
                            self.numeric.setdefault(s, set()).add(k)
                        continue
                    if isinstance(c, Call) and len(c.args) == 2 and isinstance(c.args[1], Str):
                        k = colkey(c.args[0])
                        if k is not None:
                            _note(cols, k, c.args[1].v)
            elif x.fn == "cell" and len(x.args) == 3:
                k = colkey(x.args[2])
                if k is not None:
                    cols.setdefault(k, [])
                r = x.args[1]
                if isinstance(r, Int) and 1 <= r.v <= 100_000:
                    self.rows.setdefault(s, set()).add(r.v)
                if isinstance(r, Call) and r.fn == "key":
                    for j in range(0, len(r.args) - 1, 2):
                        kk = colkey(r.args[j])
                        if kk is not None and isinstance(r.args[j + 1], Str):
                            _note(cols, kk, r.args[j + 1].v)
            elif x.fn == "header" and len(x.args) == 2:
                k = colkey(x.args[1])
                if k is not None:
                    cols.setdefault(k, [])
            elif x.fn in NUMERIC_FNS and len(x.args) >= 2:
                k = colkey(x.args[1])
                if k is not None:
                    cols.setdefault(k, [])
                    self.numeric.setdefault(s, set()).add(k)
        for x in walk(expr):   # number(cell(t, r, k)) makes column k numeric
            if isinstance(x, Call) and x.fn == "number" and x.args and isinstance(x.args[0], Call) and x.args[0].fn == "cell":
                cl = x.args[0]
                s = slot_of(cl.args[0]) if cl.args else None
                k = colkey(cl.args[2]) if len(cl.args) == 3 else None
                if s is not None and k is not None:
                    self.numeric.setdefault(s, set()).add(k)

    def events_slot(self, d):
        """The events-table slot of dataset d: its first column is the onset, a decimal in every
        events file the reader accepts (1.0.1 section 8.5), so it takes decimal candidates."""
        self.numeric.setdefault("E:" + d, set()).add(("pos", 1))
        ev = self.cols.setdefault("E:" + d, {})
        ev.setdefault(("pos", 1), [])
        return ev

    def values(self):
        """Candidate decimals: 0, then values far on both sides of every cutoff (so a spread,
        a sum or a mean can pass any cutoff with two or three rows), then 1, 2, the values
        next to each cutoff and half of each cutoff (SPEC 4.4 item 2)."""
        out = []
        qs = [abs(c) for c in self.cuts] or [Fraction(0)]
        # then values where one widen() changes a comparison: a cutoff less the other widenings and half
        # of this one, on each side (v4-fixes 07)
        cand = [Fraction(0)] + [c + s * (sum(self.tols) - q / 2) for c in self.cuts for q in self.tols for s in (1, -1) if q]
        for c in self.cuts:
            for q in qs:
                cand += [c + 2 * q + 1, c - 2 * q - 1]
        cand += [Fraction(1), Fraction(2)]
        for c in self.cuts:
            cand += [c, c + 1, c - 1]
        cand += [c / 2 for c in self.cuts]   # between 0 and the cutoff, for values that must be positive (a TR, a duration)
        for q in cand:
            t = dec_text(q)
            if t is not None and t not in out:
                out.append(t)
        return out

    def tables(self, slot):
        """Candidate TSV byte strings for one slot, in the fixed order of SPEC 4.4."""
        cols = self.cols.get(slot, {})
        npos = max([k[1] for k in cols if k[0] == "pos"] + [0])
        names = [k[1] for k in cols if k[0] == "name"]
        order = [("pos", i) for i in range(1, npos + 1)] + [("name", n) for n in names]
        nums = self.numeric.get(slot, set())
        vals = self.values()
        options = []
        for k in order:
            lits = [b.decode("utf-8", "surrogateescape") if isinstance(b, bytes) else b for b in cols.get(k, [])]
            if k in nums:
                opts = _interleave(vals, [l for l in lits if l not in vals])
            else:
                taken = set(lits)
                fresh = [w for w, _ in zip((w for w in _fresh() if w not in taken), range(2 if k in cols else 1))]
                # two fresh literals, so an unmentioned cell can differ (one where no part reads the
                # column); fresh and named options alternate so the first types mix both (SPEC 4.4 item 1)
                opts = _interleave(fresh, lits)
            options.append(opts)
        types = _shells(options, MAX_TYPES)

        # an empty cell is readable only beside another column (a one-column row of no bytes is a
        # blank line), so a statement naming "" gets one more, unnamed column (SPEC 4.4 item 1)
        pad = any(o == "" for opts in options for o in opts)

        def header(alt):
            hs = []
            for k in order:
                if k[0] == "name":
                    hs.append(k[1].decode("utf-8", "surrogateescape"))
                else:
                    hs.append(("d" if alt else "c") + str(k[1]))
            if pad:
                hs.append(next(w for w in ("zpad" + str(i) for i in range(len(hs) + 1)) if w.encode() not in names))
            return hs or (["d1"] if alt else ["c1"])

        def table(rows, alt=False):
            hs = header(alt)
            lines = ["\t".join(hs)] + ["\t".join(list(r) + (["p"] if pad else [])) if r or pad else "z" for r in rows]
            return ("\n".join(lines) + "\n").encode("utf-8", "surrogateescape")

        yield table([])
        for t in types:
            yield table([t])
        pt = types[:MAX_PAIR_TYPES]
        for i in range(len(pt)):
            for j in range(i, len(pt)):
                yield table([pt[i], pt[j]])
        ms = sorted({int(abs(c)) + 1 for c in self.cuts if abs(c) >= 2})
        for m in ms[:4]:   # every type, so a bound can be crossed by rows that pass every condition but one
            for t in types:
                yield table([t] * min(m, 100_000))
        for r in sorted(self.rows.get(slot, ()))[:8]:   # a row named by position: vary that row (SPEC 4.4 item 3)
            if r > 3 and types:
                for t in types[:MAX_PAIR_TYPES]:
                    yield table([types[0]] * (r - 1) + [t])
        if len(options) > 6:   # past the shell cap: the row of each column's first named option, alone and beside itself with one column changed (v4-fixes 14)
            full = [o[1] if len(o) > 1 else o[0] for o in options]
            yield table([full])
            for j in range(len(full)):
                yield table([full, full[:j] + [options[j][0]] + full[j + 1:]])
        yield table([], alt=True)
        if types:
            yield table([types[0]], alt=True)
        for i in range(min(len(pt), 6)):
            for j in range(i, min(len(pt), 6)):
                for k in range(j, min(len(pt), 6)):
                    yield table([pt[i], pt[j], pt[k]])

    def datasets(self, name):
        """Candidate BIDS datasets for one dataset name (SPEC 4.4 item 7): (blobs, manifest
        hash). The participants table takes the table candidates of its slot (participant_id is
        added, with the statement's subject labels first); each named recording in turn takes the
        events-table candidates, then candidate RepetitionTimes, then candidate volume counts."""
        info = dict(self.bids.get(name, {"subs": [], "recs": []}))
        pc = self.cols.get("P:" + name, {})   # participant_id, by name or as column 1 (BB's call 12)
        info["ids"] = [v[4:].decode("ascii", "replace") for v in pc.get(("name", b"participant_id"), []) + pc.get(("pos", 1), []) if v.startswith(b"sub-")]
        ps = list(self.tables("P:" + name))
        evs = list(self.tables("E:" + name)) if ("E:" + name) in self.cols else []
        trs = [Fraction(2)] + [Fraction(t) for t in self.values() if 0 < Fraction(t) != 2][:8]
        vols = [5, 1, 2] + sorted({int(abs(c)) + d for c in self.cuts for d in (0, 1) if 3 <= int(abs(c)) + d <= 100_000})[:8]
        base = ps[1] if len(ps) > 1 else ps[0]
        yield _dataset(info, base, {})
        for p in ps:
            yield _dataset(info, p, {})
        # a recording set (recordings(b, task)) gives every participant a recording of the task;
        # all of them take each per-recording candidate together, over the first participants
        # tables (so a selection of participants picks some of them on some candidate)
        if info.get("tasks"):
            for p in ps[:MAX_PAIR_TYPES]:
                for over in [(e, None, None) for e in evs] + [(None, t, None) for t in trs] + [(None, None, v) for v in vols]:
                    yield _dataset(info, p, {"auto": over})
        for j in range(len(info["recs"])):
            for e in evs:
                yield _dataset(info, base, {j: (e, None, None)})
            for t in trs:
                yield _dataset(info, base, {j: (None, t, None)})
            for v in vols:
                yield _dataset(info, base, {j: (None, None, v)})

    def jsons(self, slot):
        """Candidate JSON texts: every named leaf takes a candidate decimal or one of two fresh
        strings, types listed by shells; then the empty object (SPEC 4.4 item 5)."""
        paths = self.json_paths.get(slot, [])
        leaves = [p for p in paths if not any(q != p and q[:len(p)] == p for q in paths)]
        nums = self.values()
        fresh = [w for w, _ in zip(_fresh(), range(2))]
        options = [_interleave(nums, ['"' + w + '"' for w in fresh]) for _ in leaves]
        yield b"{}"
        for t in _shells(options, MAX_TYPES):
            tree = _build(leaves, t)
            if tree is not None:
                yield _dump(tree).encode("utf-8")

    def niftis(self):
        """Candidate NIfTI-1 headers (SPEC 4.4 item 6): a 3-D one, then 4-D ones whose volume
        count, time step (float32 of the candidate decimals) and time unit (s, ms) vary."""
        counts = [1, 2] + sorted({int(abs(c)) + d for c in self.cuts for d in (0, 1) if 1 <= int(abs(c)) + d <= 100_000})
        steps = [Fraction(t) for t in self.values() if Fraction(t) > 0] or [Fraction(1)]
        steps += [Fraction(c) * 1000 for c in self.cuts if c > 0]   # the same cutoff, met in ms
        opts = [_interleave(counts, []), _interleave(steps, []), [8, 16]]
        yield _nii((1, 1, 1), 1, data=False)
        for n, step, unit in _shells(opts, MAX_TYPES):
            yield _nii((1, 1, 1, n), step, unit, data=False)
        for k in range(3):   # each spatial axis varied too, so dim(n, 1..3) has witnesses (v4-fixes 16)
            yield from (_nii(tuple(n if i == k else 1 for i in range(3)), 1, data=False) for n in counts[1:])

    def blobs(self, slot):
        yield from self.niftis() if slot in self.nifti_slots else ()
        yield from self.jsons(slot) if slot in self.json_paths else ()
        yield from self.tables(slot) if slot in self.tsv_slots else ()
        yield from map(_as_csv, self.tables(slot)) if slot in self.csv_slots else ()
        if slot in self.raw:
            n = self.raw[slot]
            for size in sorted({0, 1, n, n + 1}):
                for fill in (b"\x00", b"\x01"):
                    yield fill * size


def json_chain(e):
    """(file slot, path) for member()/item() chains that start at json(Name), else None."""
    path = []
    while isinstance(e, Call) and e.fn in ("member", "item") and len(e.args) == 2:
        a = e.args[1]
        if e.fn == "member" and isinstance(a, Str):
            path.append(("m", a.v))
        elif e.fn == "item" and isinstance(a, Int) and 1 <= a.v <= 1000:
            path.append(("i", a.v))
        else:
            return None
        e = e.args[0]
    if isinstance(e, Call) and e.fn == "json" and e.args and isinstance(e.args[0], Name):
        return e.args[0].id, tuple(reversed(path))
    return None


def _build(leaves, values):
    root = [None]

    def put(holder, idx, path, v):
        if not path:
            holder[idx] = ("raw", v)
            return True
        step, rest = path[0], path[1:]
        cur = holder[idx]
        if step[0] == "m":
            if cur is None:
                cur = holder[idx] = ("obj", {})
            if cur[0] != "obj":
                return False
            d = cur[1]
            d.setdefault(step[1], None)
            box = [d[step[1]]]
            ok = put(box, 0, rest, v)
            d[step[1]] = box[0]
            return ok
        if cur is None:
            cur = holder[idx] = ("arr", [])
        if cur[0] != "arr":
            return False
        arr = cur[1]
        while len(arr) < step[1]:
            arr.append(None)
        return put(arr, step[1] - 1, rest, v)

    for p, v in zip(leaves, values):
        if not put(root, 0, p, v):
            return None
    return root[0] or ("obj", {})


def _dump(node):
    if node is None:
        return "0"
    kind, v = node
    if kind == "raw":
        return v
    if kind == "arr":
        return "[" + ", ".join(_dump(x) for x in v) + "]"
    import json as _json
    return "{" + ", ".join(_json.dumps(k.decode("utf-8", "replace")) + ": " + _dump(x) for k, x in v.items()) + "}"


def _interleave(a, b):
    out = []
    for i in range(max(len(a), len(b))):
        out += a[i:i + 1] + b[i:i + 1]
    return list(dict.fromkeys(out))


def _shells(options, cap):
    """Row types in order of their largest option index (all types from options 0..r before
    any that needs option r + 1), lexicographic within a shell; at most cap (SPEC 4.4 item 1)."""
    import itertools
    if not options:
        return [[]]
    out = []
    for r in range(max(len(o) for o in options)):
        ranges = [range(min(r + 1, len(o))) for o in options]
        for ix in itertools.product(*ranges):
            if max(ix) != r:
                continue
            out.append([options[c][i] for c, i in enumerate(ix)])
            if len(out) >= cap:
                return out
    return out


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


def _cols(tsv):
    lines = tsv.decode("utf-8", "surrogateescape").split("\n")[:-1]
    return lines[0].split("\t"), [ln.split("\t") for ln in lines[1:]]


def _dataset(info, ptsv, over):
    """One made-up dataset: the participants candidate, one BOLD recording (with its own sidecar
    and events) per recording the statement names, and a T1w image for every other subject."""
    files = {"dataset_description.json": b'{"Name": "witness", "BIDSVersion": "1.0.1"}', "README": b"witness\n"}
    hs, rows = _cols(ptsv)
    if "participant_id" not in hs:   # it is the first column (S0556, BB's call 12); one named only by position 1 becomes it
        hs, rows = (hs, rows) if hs[0] in ("c1", "d1") else (["participant_id"] + hs, [[""] + r for r in rows])
        hs = ["participant_id"] + hs[1:]
    i = hs.index("participant_id")
    hs, rows = [hs[i]] + hs[:i] + hs[i + 1:], [[r[i]] + r[:i] + r[i + 1:] for r in rows]
    need = list(info["subs"])
    rows += [["n/a"] * len(hs) for _ in range(len(need) - len(rows))]
    pool = [x for x in info["ids"] if x not in need] + [f"w{i}" for i in range(1, len(rows) + 1)]
    labels = need + [w for w in pool if w not in need][:len(rows) - len(need)]
    for r, lab in zip(rows, labels):
        r[hs.index("participant_id")] = "sub-" + lab
    files["participants.tsv"] = ("\n".join("\t".join(r) for r in [hs] + rows) + "\n").encode("utf-8", "surrogateescape")
    recs = list(info["recs"])
    for t in info.get("tasks", []):
        recs += [{"sub": lab, "task": t} for lab in labels if {"sub": lab, "task": t} not in recs]
    for j, ents in enumerate(recs):
        ev, tr, v = over.get(j if j < len(info["recs"]) else "auto", (None, None, None))
        tr = tr or Fraction(2)
        eh, er = _cols(ev) if ev else (["onset", "duration"], [["0.5", "1"]])
        eh = [{"c1": "onset", "d1": "onset", "c2": "duration", "d2": "duration"}.get(h, h) for h in eh]
        if eh[:1] != ["onset"]:
            eh, er = ["onset"] + eh, [["0.5"] + r for r in er]
        if eh[1:2] != ["duration"]:
            eh, er = eh[:1] + ["duration"] + eh[1:], [r[:1] + ["1"] + r[1:] for r in er]
        ons = [R.decimal(r[0]) for r in er]
        if v is None:
            v = max([5] + [int(o / tr) + 2 for o in ons if o is not None])
        if dec_text(tr) is None or v > 100_000 or "sub" not in ents or "task" not in ents:
            return None
        stem = "sub-{0}/func/sub-{0}_task-{1}".format(ents["sub"], ents["task"]) + "".join(f"_{k}-{ents[k]}" for k in ("acq", "rec", "run") if k in ents)
        files[stem + "_bold.nii"] = _nii((1, 1, 1, v), tr)
        files[stem + "_bold.json"] = ('{"TaskName": "%s", "RepetitionTime": %s}' % (ents["task"], dec_text(tr))).encode()
        files[stem + "_events.tsv"] = ("\n".join("\t".join(r) for r in [eh] + er) + "\n").encode("utf-8", "surrogateescape")
    for lab in labels:
        if not any(p.startswith(f"sub-{lab}/") for p in files):
            files[f"sub-{lab}/anat/sub-{lab}_T1w.nii"] = _nii((1, 1, 1), 1)
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files, key=lambda p: p.encode("utf-8", "surrogateescape")))).encode("utf-8", "surrogateescape")
    mh = hashlib.sha256(man).hexdigest()
    blobs[mh] = man
    return blobs, mh


def _fresh():
    import itertools
    for n in range(1, 4):
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


class _Recorder:
    def __init__(self, checker_cls, store, env):
        self.ck = checker_cls(store)
        self.ck.env = env
        self.ck.exprs = {}
        self.got = {}
        orig = self.ck.meaning

        def meaning(e):
            m = orig(e)
            if isinstance(e, Call):
                a = answer(m)
                if a is not None:
                    self.got[id(e)] = a
            return m
        self.ck.meaning = meaning


def evaluate(checker_cls, expr, names, assignment, budget):
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
        h = hashlib.sha256(b).hexdigest()
        blobs[h] = b
        env[n] = ("file", h, 0)
    st = MemStore(blobs)
    rec = _Recorder(checker_cls, st, env)
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
    """Raise S008 / S011 / R013 unless W1 and W2 hold for expr (SPEC 4.3)."""
    from reality4.kernel import Checker, fail
    expr = _as_judged(expr, checker)
    # slots in the order of their hashes, so the search, and so R013, is the same under any renaming
    names = sorted({x.id for x in walk(expr) if isinstance(x, Name)}, key=lambda n: checker.env.get(n, (n,))[:2])
    if not names:
        return
    plan = Plan(expr)
    cands = {n: [d for d in plan.datasets(n) if d is not None] if checker.env.get(n, ("",))[0] == "dataset" else list(plan.blobs(n)) for n in names}
    real = {}   # the real bytes are a readable input too: tried last, for a file read whole of at most MAX_REAL bytes (v4-fixes 14)
    for n in names:
        b = checker.store._memo.get(("text", checker.env[n][1])) if checker.env.get(n, ("",))[0] == "file" else None
        real.update({n: b} if isinstance(b, bytes) and len(b) <= MAX_REAL else {})
        cands[n] += [b] if n in real and b not in cands[n] else []
    if any(not c for c in cands.values()):
        return
    budget = [0]
    base = {n: (cands[n][1] if len(cands[n]) > 1 else cands[n][0]) for n in names}
    # each slot varied with the others at their base, then (two slots or more) at their real bytes (v4-fixes 15)
    assignments = [{**b0, n: b} for b0 in [base] + ([{**base, **real}] if real and len(names) > 1 else []) for n in names for b in cands[n]]
    results = []
    for a in assignments:
        got = evaluate(Checker, expr, names, a, budget)
        if budget[0] > MAX_WITNESS_STEPS:
            break
        if got is not None:
            results.append((a, got))
    checker.store.steps.add(budget[0])
    if budget[0] > MAX_WITNESS_STEPS:
        fail("R013", "bounds", f"showing that the bytes bear on the answer needs more than {MAX_WITNESS_STEPS} counted steps (Reality bounds, v4 SPEC 4.5)")
    for e in subexprs(expr):
        seen = {got[id(e)] for _, got in results if id(e) in got}
        if len(seen) >= 2:
            continue
        what = e.fn + "()"
        if seen == {("bool", False)} or (seen and all(s[0] == "sel" and s[1] == () for s in seen)) or (not seen and e is expr and e.fn in ("exceeds", "below", "atleast", "atmost")):
            fail("S011", "6", f"{what}: Reality found no readable input on which {'it holds' if e.fn in ('exceeds', 'below', 'atleast', 'atmost') else 'the selection has a row'} (its search, with the real bytes when small), so it is not shown that the claim's parts allow one (v4 SPEC 4.3)")
        fail("S008", "1", f"{what}: Reality could not find two inputs its readers accept on which this value differs, so the bytes do not bear on the answer (v4 SPEC 4.3, W1)")
    for node, mod, desc in parts(expr):
        found = False
        # W2 is judged at the highest enclosing value that still answers without the part (the
        # statement itself when it can be; v4 SPEC 4.3), so a condition idle inside a nested
        # where() is idle, and a part whose removal leaves no well-formed statement is judged on
        # the value it is a part of; widen() too (v4-fixes 07)
        levels = [(x, _subst(x, node, mod)) for x in _path(expr, node)]
        for a, _ in results:
            for top, whole in levels:
                g1 = evaluate(Checker, top, names, a, budget)
                g2 = evaluate(Checker, whole, names, a, budget)
                if budget[0] > MAX_WITNESS_STEPS:
                    fail("R013", "bounds", f"showing that every part bears on the answer needs more than {MAX_WITNESS_STEPS} counted steps (Reality bounds, v4 SPEC 4.5)")
                # a value refusal (V: no such row, no single row) is an outcome; any other is no answer
                a1, a2 = (g.get(id(x), ("V", g.get("refused"))) if g is not None else None for g, x in ((g1, top), (g2, whole)))
                bad = [t is None or (t[0] == "V" and (t[1] or "")[:1] != "V") for t in (a1, a2)]
                if bad[0]:
                    break      # the statement has no answer on this input: no witness here
                if bad[1]:
                    continue   # without the part this value is not well formed: judge one level down
                found = a1 != a2
                break
            if found:
                break
        if not found:
            fail("S008", "1", f"{node.fn}(): Reality found no readable input on which {desc} changes the answer, so it is not shown to bear on it (v4 SPEC 4.3, W2)")

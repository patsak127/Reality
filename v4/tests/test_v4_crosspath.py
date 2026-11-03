"""Standing cross-path differential (fix pass, FIX-BRIEF section 2): the same numbers read through BIDS
1.0.1 (participants.tsv, one BOLD recording per subject with its events) and through a plain TSV table
(one row per participant, the events and volume counts as columns) must give identical verdicts and
identical values: sums, means, max/min, counts, shares, differences, widen, comparisons, over groups
(where on a group column, or on a number column) and their differences, several claims per program
(so value identity and S012 are compared too). Seeded and deterministic.

The only differences allowed are the ones listed in INTENDED, each with the register row (or
principle clause) it rests on. Any other difference is a break (R1 was one: two groups whose events
files had the same bytes were one value through BIDS and two through the TSV)."""
import hashlib
import random
import re

import helpers  # noqa: F401 (puts src on the path)
from reality4 import kernel as K, readers as R, witness as W

# subject: (group, age, events, volumes). Events files and images repeat bytes across subjects, as in
# real datasets, so different selections often read one set of file hashes (R1 hid there)
SUBJECTS = {"01": ("a", 20, 3, 5), "02": ("b", 31, 3, 5), "03": ("a", 45, 3, 7), "04": ("b", 31, 2, 5),
            "05": ("c", 27, 3, 8), "06": ("a", 52, 2, 7)}
TR = 2


def bids_files():
    files = {"dataset_description.json": b'{"Name": "x", "BIDSVersion": "1.0.1"}', "README": b"cross-path fixture\n",
             "task-x_bold.json": b'{"TaskName": "x", "RepetitionTime": %d}' % TR,
             "participants.tsv": ("participant_id\tgroup\tage\n" + "".join(f"sub-{s}\t{g}\t{a}\n" for s, (g, a, _, _) in SUBJECTS.items())).encode()}
    for s, (_, _, ev, vol) in SUBJECTS.items():
        files[f"sub-{s}/func/sub-{s}_task-x_bold.nii"] = W._nii((1, 1, 1, vol), TR)
        files[f"sub-{s}/func/sub-{s}_task-x_events.tsv"] = ("onset\tduration\n" + "".join(f"{k}\t1\n" for k in range(ev))).encode()
    return files


def tsv_bytes():
    return ("id\tgroup\tage\tevents\tvolumes\ttr\n" + "".join(f"sub-{s}\t{g}\t{a}\t{e}\t{v}\t{TR}\n" for s, (g, a, e, v) in SUBJECTS.items())).encode()


def stores():
    files = bids_files()
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    mh = hashlib.sha256(man).hexdigest()
    blobs[mh] = man
    t = tsv_bytes()
    th = hashlib.sha256(t).hexdigest()
    return (W.MemStore(blobs), f"dataset d = sha256:{mh}\nlet b = bids(d)\n"), (W.MemStore({th: t}), f"file f = sha256:{th}\nlet t = tsv(f)\n")


# ---- the family: each builder returns (BIDS text, TSV text, kind, unit) --------------------------

GROUPS = ["a", "b", "c", "z"]   # z: no participant (empty selections)


def selection(rng, simple=False):
    """(BIDS selection of participants(b), TSV selection of t)."""
    r = rng.random()
    if r < 0.45:
        c = f'{rng.choice(["eq", "ne"])}("group", "{rng.choice(GROUPS)}")'
    elif r < 0.75 or simple:
        c = f'{rng.choice(["ge", "gt", "le", "lt"])}("age", c = {rng.choice([20, 27, 31, 40, 52, 60])})'
    else:
        c = f'eq("group", "{rng.choice(GROUPS)}"), {rng.choice(["gt", "le"])}("age", c = {rng.choice([25, 31, 45])})'
    return f"where(participants(b), {c})", f"where(t, {c})"


def value(rng, simple=False):
    """A number or a count over a selection (or the whole set): (bids, tsv, kind, unit)."""
    sb, st = selection(rng, simple) if rng.random() < 0.85 else ("participants(b)", "t")
    r = rng.random()
    if r < 0.25:   # a participants column
        fn = rng.choice(["sum", "mean", "max", "min"])
        return f'{fn}({sb}, "age")', f'{fn}({st}, "age")', "num", None
    rs = f'recordings(b, "x", {sb})' if sb != "participants(b)" else 'recordings(b, "x")'
    if r < 0.65:   # a recording quantity
        fn = "sum" if simple else rng.choice(["sum", "mean", "max", "min"])
        q = rng.choice(["events", "volumes", "events", "tr"])
        return f'{fn}({rs}, "{q}")', f'{fn}({st}, "{q}")', "num", "s" if q == "tr" else None
    if r < 0.85:
        return f"count({rs})", f"count({st})", "count", None
    return f"count({sb})", f"count({st})", "count", None


def widened(rng, v):
    if v[2] == "num" and rng.random() < 0.35:
        q = rng.choice(["1", "1/2", "2"])
        return f"widen({v[0]}, tolerance = {q}{' s' if v[3] else ''})", f"widen({v[1]}, tolerance = {q})", "num", v[3]
    return v


def numeric(rng, depth=0):
    """A value, perhaps widened, or a difference of two of one kind and unit (nested up to depth 2)."""
    if depth < 2 and rng.random() < 0.35:
        a = numeric(rng, depth + 1)
        for _ in range(20):
            b = numeric(rng, depth + 1)
            if a[2:] == b[2:]:
                return f"difference({a[0]}, {b[0]})", f"difference({a[1]}, {b[1]})", "num", a[3]
        return a
    return widened(rng, value(rng))


def contrast(rng):
    """One aggregate over two selections (two groups), each widened, and their difference: the shape
    in which R1 hid (two groups whose files have the same bytes were one value through BIDS)."""
    fn = rng.choice(["sum", "sum", "mean", "max", "min"])
    q = rng.choice(["events", "volumes", "tr", "age"])
    (b1, t1), (b2, t2) = selection(rng), selection(rng)
    u = " s" if q == "tr" else ""
    if q == "age":
        x = [(f'{fn}({b}, "age")', f'{fn}({t}, "age")') for b, t in ((b1, t1), (b2, t2))]
    else:
        x = [(f'{fn}(recordings(b, "x", {b}), "{q}")', f'{fn}({t}, "{q}")') for b, t in ((b1, t1), (b2, t2))]
    tol = [rng.choice(["1", "1", "2"]) for _ in x]
    wb, wt = ([f"widen({v[i]}, tolerance = {k}{u if i == 0 else ''})" for v, k in zip(x, tol)] for i in (0, 1))
    return f"difference({wb[0]}, {wb[1]})", f"difference({wt[0]}, {wt[1]})"


def claim(rng, simple=False):
    r = rng.random()
    if not simple and r > 0.75:
        return contrast(rng)
    if r < 0.15:   # a share of a selection, or of a selection within another
        sb, st = selection(rng, simple)
        if simple or rng.random() < 0.5:
            return f"share({sb})", f"share({st})"
        c = 'eq("group", "a")'
        return (f"share(where(participants(b), {c}, {sb[len('where(participants(b), '):-1]}), where(participants(b), {c}))",
                f"share(where(t, {c}, {st[len('where(t, '):-1]}), where(t, {c}))")
    v = widened(rng, value(rng, True)) if simple else numeric(rng)
    if r < 0.55:
        return v[0], v[1]
    fn = rng.choice(["exceeds", "atleast", "below", "atmost"])
    c = rng.choice([6, 10, 31, 40] if simple else [0, 1, 2, 3, 6, 10, 31, 40])
    u = f" {v[3]}" if v[3] else ""
    return f"{fn}({v[0]}, c = {c}{u})", f"{fn}({v[1]}, c = {c})"


def program(rng, simple=False):
    """1-3 claims, sometimes through let names (so one value meets two tolerances: S012 by identity)."""
    pb, pt = [], []
    for i in range(1 if simple else rng.choice([1, 1, 2, 3])):
        b, t = claim(rng, simple)
        if rng.random() < 0.2:
            pb.append(f"let v{i} = {b}")
            pt.append(f"let v{i} = {t}")
            b, t = f"v{i}", f"v{i}"
        pb.append(f"claim {b}")
        pt.append(f"claim {t}")
    return "\n".join(pb) + "\n", "\n".join(pt) + "\n"


# ---- comparing outputs ----------------------------------------------------------------------------

VALUE = re.compile(r"\] ((?:= |lies within \[|holds|is recorded as |is recorded within \[).*)$")

# Intended differences (each: what, the rule it rests on). Applied to the BIDS output before comparing.
INTENDED = [
    # RepetitionTime is in seconds (S0293: "RepetitionTime: The time in seconds between ...") and
    # Recorded (principle section 1, Floor: "A value the bytes give without a stated precision is
    # Recorded"); the TSV's tr column is a plain decimal with no unit. Mapped back before comparing.
    ("tr: unit s and Recorded", [(r" s\b", ""), (r"is recorded as ", "= "), (r"is recorded within ", "lies within "),
                                  (r"holds of the recorded value", "holds"), (r"Recorded\[s\], Interval", "Interval"),
                                  (r"Recorded\[s\]", "Exact")]),
]


def verdicts(lines):
    """Per line number: ('formed', value text) or ('refused', code)."""
    out = {}
    for ln in lines:
        m = re.match(r"line (\d+): (formed|refused)(.*)$", ln)
        if not m:
            continue
        if m.group(2) == "refused":
            out[int(m.group(1))] = ("refused", re.match(r" \[(\w+)", m.group(3)).group(1))
        else:
            out[int(m.group(1))] = ("formed", VALUE.search(ln).group(1))
    return out


def normalise(v, unit):
    if v[0] == "formed" and unit:
        s = v[1]
        for _, subs in INTENDED:
            for a, b in subs:
                s = re.sub(a, b, s)
        return ("formed", s)
    return v


def run_pair(stores_, pb, pt):
    (sb, hb), (st, ht) = stores_
    sb.begin_program()
    st.begin_program()
    _, ob = K._check((hb + pb).encode(), sb)
    _, ot = K._check((ht + pt).encode(), st)
    return verdicts(ob), verdicts(ot)


class _NoWitness:
    """W1/W2 switched off on both paths: the two readers' input spaces differ by design (in BIDS an
    events count is a whole number >= 0, a volume count >= 1, a RepetitionTime > 0; a set's recordings
    share one candidate), so their witness searches are compared only on the simple family."""
    def __enter__(self):
        self.saved, W.check = W.check, lambda checker, expr: None

    def __exit__(self, *exc):
        W.check = self.saved


def divergences(seed, n, simple=False, witness=True):
    rng = random.Random(seed)
    st = stores()
    bad, seen = [], {"formed": 0, "refused": 0}
    for _ in range(n):
        pb, pt = program(rng, simple)
        if witness:
            vb, vt = run_pair(st, pb, pt)
        else:
            with _NoWitness():
                vb, vt = run_pair(st, pb, pt)
        units = '"tr"' in pb
        for ln in sorted(set(vb) | set(vt)):
            b, t = normalise(vb.get(ln), units) if vb.get(ln) else None, vt.get(ln)
            seen[t[0] if t else "refused"] += 1
            if b != t:
                bad.append((pb, pt, ln, vb.get(ln), t))
    return bad, seen


def _report(bad):
    return "\n\n".join(f"{pb}{pt}line {ln}: BIDS {b} / TSV {t}" for pb, pt, ln, b, t in bad[:10])


def test_values_identities_and_refusals_agree():
    """Every value and interval, every S012 (value identity) and every refusal but W1/W2, over a
    family with nested differences, widen, shares, comparisons and let names (R1's class)."""
    bad, seen = divergences(20261026, 400, witness=False)
    assert seen["formed"] > 300, seen
    assert not bad, _report(bad)


def test_verdicts_agree_with_the_witness_on():
    """The whole verdict, W1/W2 included, on single-value claims: one condition, recording sums."""
    bad, seen = divergences(20261027, 60, simple=True)
    assert seen["formed"] > 30, seen
    assert not bad, _report(bad)


# Intended differences in the witness's input space, each with the rule it rests on: through BIDS
# the quantity is bounded by the reader, through a plain TSV the same column is any decimal. So the
# comparison is constant over BIDS inputs (W1, S008) and not over TSV inputs (it forms).
INPUT_SPACE = [
    # an events count is the number of rows of an events TSV, each row an event (S0101 "Each event
    # has an onset time and duration."; SPEC 7.7 events()): a whole number >= 0
    ('atleast(widen(sum(recordings(b, "x"), "events"), tolerance = 2), c = 0)', 'atleast(widen(sum(t, "events"), tolerance = 2), c = 0)'),
    # RepetitionTime is a positive number (S0293, checked B08)
    ('atleast(min(recordings(b, "x"), "tr"), c = 0 s)', 'atleast(min(t, "tr"), c = 0)'),
    # a volume count is the BOLD header's dim[4] of a 4-D image (S0140, NIfTI-1/2; B05): at least 1
    ('exceeds(min(recordings(b, "x"), "volumes"), c = 0)', 'exceeds(min(t, "volumes"), c = 0)'),
]


def test_intended_input_space_differences_are_these():
    st = stores()
    for b, t in INPUT_SPACE:
        vb, vt = run_pair(st, f"claim {b}\n", f"claim {t}\n")
        assert vb == {3: ("refused", "S008")} and vt == {3: ("formed", "holds")}, (b, vb, vt)

"""The BIDS 1.0.1 reader: whole-dataset conformance, then the sorts BIDS 1.0.1 defines.

Every rule it checks is listed in ../../bids/RULES-1.0.1.md with its 1.0.1 section, together
with every 1.0.1 sentence it does not check and why. A dataset is read under the version it
declares; only "1.0.1" has a reader. If any rule fails, nothing BIDS-based forms from the
dataset (principle section 1, whole-dataset conformance); file-level claims about its files
still form, because they do not come through this reader.

A dataset is named by a manifest, and the name promises the whole dataset (Patsak's call 1):
every file the manifest lists must be supplied with its listed hash and size, whether or not
anything reads it, and participants.tsv rows without a subject folder refuse. Where 1.0.1 is
silent the reader refuses rather than pick a reading (Patsak's call 3)."""

import datetime
import re
import struct
from fractions import Fraction

from . import readers as R
from .keys import K, is_key, skeleton
from .readers import Refusal

VERSION = "1.0.1"
FUNC_SUFFIX = {"bold", "sbref"}
FMAP_CASE1 = {"phasediff", "magnitude1", "magnitude2"}
FMAP_OTHER = {"phase1", "phase2", "magnitude", "fieldmap", "epi"}
ROOT_DEFINED = {"dataset_description.json", "README", "CHANGES", "participants.tsv", "participants.json"}
DESC_KEYS = {"LongName", "Description", "Levels", "Units", "TermURL"}   # section 4.2; Derivative too in participants and phenotype (S0568)


def column_fails(p, key, v, derivative):
    """The form faults of one column description (sections 4.2, 8.11), as (code, message) pairs."""
    if key == "MeasurementToolMetadata":
        ok = isinstance(v, dict) and set(v) <= {"Description", "TermURL"} and all(isinstance(x, str) for x in v.values())
        return [] if ok else [("B19", f"{p}: MeasurementToolMetadata has only the string keys Description and TermURL (S0564)")]
    out = [("B30", f"{p}: {key!r} is described with {k!r}, a key BIDS 1.0.1 does not list for column descriptions (S0568), so it fixes no reading of it (v4 SPEC 8.3)")
           for k in sorted(set(v) - DESC_KEYS - ({"Derivative"} if derivative else set()))][:1]
    if "Levels" in v and not (isinstance(v["Levels"], dict) and all(isinstance(x, str) for x in v["Levels"].values())):
        out.append(("B19", f"{p}: the Levels of {key!r} are not a dictionary of values and their descriptions (S0157)"))
    if "Derivative" in v and not isinstance(v["Derivative"], bool):
        out.append(("B19", f"{p}: the Derivative of {key!r} is not true or false (S0569)"))
    return out
OPTIONAL_DIRS = {"code", "derivatives", "stimuli", "sourcedata"}
DATATYPES = {"func", "anat", "fmap"}
PED = {"i", "j", "k", "i-", "j-", "k-"}
# Number-valued keys, closed from the 1.0.1 text (RULES-1.0.1.md, B21): every key whose 1.0.1
# definition is a quantity (a unit, "number of", a factor or a fraction). Keys 1.0.1 does not
# define (DelayTime, DwellTime, SliceThickness, ...) are not number-checked.
NUMBER_KEYS = {
    "RepetitionTime": "section 8.4: a time in seconds",
    "MagneticFieldStrength": "section 8.4: a field strength in Tesla",
    "NumberShots": "section 8.4: the number of RF excitations",
    "ParallelReductionFactorInPlane": "section 8.4: the parallel imaging factor",
    "PartialFourier": "section 8.4: the fraction of partial Fourier information collected",
    "EffectiveEchoSpacing": "section 8.4: expressed in seconds",
    "TotalReadoutTime": "section 8.4: a time in seconds",
    "InversionTime": "section 8.4: specified in seconds",
    "NumberOfVolumesDiscardedByScanner": "section 8.4: a number of volumes",
    "NumberOfVolumesDiscardedByUser": "section 8.4: a number of volumes",
    "FlipAngle": "section 8.4: specified in degrees",
    "MultibandAccelerationFactor": "section 8.4: the multiband factor",
    "EchoTime1": "section 8.9.1: an echo time",
    "EchoTime2": "section 8.9.1: an echo time",
}


def _index(s):
    return s != "" and all(c in "0123456789" for c in s)


def parse_name(fn):
    """'sub-01_task-x_run-1_bold.nii.gz' -> ([('sub','01'),('task','x'),('run','1')], 'bold', 'nii.gz')."""
    for ext in ("nii.gz", "nii", "json", "tsv.gz", "tsv", "bval", "bvec"):
        if fn.endswith("." + ext):
            stem = fn[: -len(ext) - 1]
            break
    else:
        return None
    parts = stem.split("_")
    suffix = parts[-1]
    if not is_key(suffix):
        return None
    ents = []
    for p in parts[:-1]:
        k, dash, v = p.partition("-")
        if not dash or not k.isascii() or not k.isalpha() or not is_key(v):
            return None
        ents.append((k, v))
    return ents, suffix, ext


def _order_ok(ents, allowed):
    keys = [k for k, _ in ents]
    pos = [allowed.index(k) if k in allowed else -1 for k in keys]
    if -1 in pos or pos != sorted(pos) or len(set(keys)) != len(keys):
        return False
    d = dict(ents)
    return "run" not in d or _index(d["run"])


class Unsupported(Exception):
    pass


def _any_level(path, pn):
    """Register S0132: "Any metadata file (.json, .bvec, .tsv, etc.) may be defined at any
    directory level." A name of the entity form at the root or in a subject folder is metadata,
    never extra: a JSON is read and inherited; a TSV, bval or bvec is not implemented (B14)."""
    if pn is None:
        return ("extra", None)
    if pn[2] == "json":
        return ("meta", pn)
    raise Unsupported(f"{path}: an inherited {pn[2]} file outside a datatype folder (S0132)")


def classify(path):
    """-> (kind, info) for a 1.0.1-defined file; ('unknown', None) for a file in a datatype
    folder that matches no template, ('badsub', None) for one under a sub-<label> folder whose label
    is not a label (both refused, B17); ('extra', None) otherwise.
    Raises Unsupported for 1.0.1 file kinds this reader does not implement."""
    segs = path.split("/")
    if len(segs) == 1:
        fn = segs[0]
        if fn in ROOT_DEFINED:
            return ("root", fn)
        pn = parse_name(fn)
        return _any_level(path, pn)
    if segs[0] == "phenotype":
        if len(segs) == 2:
            for ext in ("tsv", "json"):
                if segs[1].endswith("." + ext) and len(segs[1]) > len(ext) + 1:
                    return ("phenotype-" + ext, None)
        return ("unknown", None)
    if segs[0] in OPTIONAL_DIRS:
        return ("extra", None)
    top = segs[0]
    if not top.startswith("sub-"):
        return ("extra", None)
    if not is_key(top[4:]):   # S0628: "hyphens and underscores are not allowed in subject labels" (fix pass R5)
        return ("badsub", None)
    sub = top[4:]
    if len(segs) >= 2 and segs[1].startswith("ses-"):
        raise Unsupported(f"{path}: sessions")
    if len(segs) >= 3 and segs[1] in ("dwi", "beh"):
        raise Unsupported(f"{path}: {segs[1]} data")
    fn = segs[-1]
    pn = parse_name(fn)
    if len(segs) == 2:
        if pn and pn[0] and pn[0][0] == ("sub", sub) and pn[1] in ("scans", "sessions") and pn[2] == "tsv":
            raise Unsupported(f"{path}: {pn[1]} files")
        return _any_level(path, pn)
    dt = segs[1]
    if dt not in DATATYPES:
        return ("extra", None)
    if len(segs) != 3 or pn is None or not pn[0] or pn[0][0] != ("sub", sub):
        return ("unknown", None)
    ents, suffix, ext = pn
    if dt == "func":
        if suffix in ("physio", "stim"):
            raise Unsupported(f"{path}: physiological and other continuous recordings")
        if suffix in FUNC_SUFFIX and ext in ("nii", "nii.gz", "json") and _order_ok(ents, ["sub", "task", "acq", "rec", "run"]) and "task" in dict(ents):
            return ("func-" + suffix + ("-json" if ext == "json" else ""), pn)
        if suffix == "events" and ext in ("tsv", "json") and _order_ok(ents, ["sub", "task", "acq", "rec", "run"]) and "task" in dict(ents):
            return ("events", pn) if ext == "tsv" else ("meta", pn)
    if dt == "anat" and ext in ("nii", "nii.gz", "json") and _order_ok(ents, ["sub", "acq", "rec", "run"]):
        return ("anat" + ("-json" if ext == "json" else ""), pn)
    if dt == "fmap":
        if suffix in FMAP_OTHER:
            raise Unsupported(f"{path}: fieldmap cases 2-4")
        if suffix in FMAP_CASE1 and ext in ("nii", "nii.gz", "json") and _order_ok(ents, ["sub", "acq", "run"]):
            return ("fmap-" + suffix + ("-json" if ext == "json" else ""), pn)
    return ("unknown", None)


IMAGE_KINDS = ("func-bold", "func-sbref", "anat", "fmap-phasediff", "fmap-magnitude1", "fmap-magnitude2")
FMAP_IMAGES = IMAGE_KINDS[3:]


def nearest(q: Fraction, version: int):
    """The float32 (NIfTI-1) or float64 (NIfTI-2) nearest to q, ties to even, computed exactly;
    None if q is outside the format's finite range."""
    fmt, ifmt, bits = ("<f", "<I", 32) if version == 1 else ("<d", "<Q", 64)
    limit = Fraction(3, 1) * 10 ** 38 if version == 1 else Fraction(17, 10) * 10 ** 308
    if abs(q) >= limit:
        return None
    x = struct.unpack(fmt, struct.pack(fmt, float(q)))[0]
    b0 = struct.unpack(ifmt, struct.pack(fmt, x))[0]
    cands = []
    for b in (b0 - 1, b0, b0 + 1):
        if 0 <= b < 2 ** bits:
            y = struct.unpack(fmt, struct.pack(ifmt, b))[0]
            if y == y and abs(y) != float("inf"):
                cands.append((abs(Fraction(y) - q), b & 1, Fraction(y)))
    cands.sort(key=lambda t: (t[0], t[1]))
    return cands[0][2]


def time_unit(hd):
    return R.TIME_UNITS.get(hd.xyzt_units & 0x38)


def tr_consistent(tr, hd) -> bool:
    """1.0.1 section 8.4: RepetitionTime "needs to be consistent with the pixdim[4] field (after
    accounting for units stored in xyzt_units)". Read here as: pixdim[4] is a positive number,
    and it is the float nearest to RepetitionTime in the header's time unit, in the header's
    own float width (float32 for NIfTI-1, float64 for NIfTI-2)."""
    unit = time_unit(hd)
    if unit is None or not isinstance(tr, Fraction) or tr <= 0 or hd.pixdim[4] is None or hd.pixdim[4] <= 0:
        return False
    return nearest(tr / unit, hd.version) == hd.pixdim[4]


class Recording:
    def __init__(self, sub, ents, path, h, ext):
        self.sub, self.ents, self.path, self.h, self.ext = sub, tuple(ents), path, h, ext
        self.events = None   # (path, h)
        self.meta = {}       # key -> (value, path, h)
        self.header = None


class BidsDataset:
    def __init__(self, mh, manifest):
        self.mh, self.manifest = mh, manifest
        self.subjects = []
        self.recordings = []
        self.participants = None  # (path, h, Table, id column index) or None
        self.ptable_labels = []


def _is_number(v):
    return isinstance(v, Fraction)


class MetaIndex:
    def __init__(self, metas):
        self.ix = {}
        for p, pn in metas:
            d = p.rsplit("/", 1)[0] if "/" in p else ""
            self.ix.setdefault((d, pn[1]), []).append((p, pn))

    def get(self, d, suffix, steps):
        lst = self.ix.get((d, suffix), ())
        if steps is not None:
            steps.add(len(lst) + 1)
        return lst


def _cpan_version(v):
    """CPAN::Meta::Spec Version Formats; BIDS 1.0.1's example "1.0.1" waives the dotted form's leading
    v and positive components (v4 SPEC 8.5). True, False or "B30" (a decimal reading and a dotted one
    beyond its 0-999 components)."""
    a, b = re.fullmatch(r"v?\d+(\.\d+)+[._]\d+", v, re.A), re.fullmatch(r"\d+(_\d+)?(\.\d+(_\d+)?)?", v, re.A)
    big = bool(a) and max(int(x) for x in re.split("[._]", v.lstrip("v"))[1:]) > 999
    return v.count("_") < 2 and (a or b) and ("B30" if big and b else not big)


def _cpan_date(s):
    """W3CDTF (the T optional: a space for it) or a no-date string ending at a word boundary: True;
    None if s starts with neither; "B30" if the longest date-shaped start is not a date (a shorter one
    is, the rest a release note), as when the date runs on into digits, letters or - / : . + (fix pass R4)."""
    if re.match(r"(Unknown Release Date|Unknown|Not Released|Development Release|Development|Developer Release)(?!\w)", s):
        return True
    m = re.match(r"(\d{4})(?:-(\d\d)(?:-(\d\d)(?:[T ](\d\d):(\d\d)(?::(\d\d)(?:\.\d+)?)?(Z|[+-](\d\d):(\d\d))?)?)?)?", s, re.A)
    if not m:
        return None
    if re.match(r"[\w/:.+-]", s[m.end():]):
        return "B30"
    y, mo, d, hh, mi, ss, tz, th, tm = m.groups()
    try:
        datetime.date(int(y), int(mo or 1), int(d or 1))
    except ValueError:
        return "B30"
    return hh is None or int(hh) < 24 and int(mi) < 60 and int(ss or 0) < 60 and bool(tz) and (tz == "Z" or int(th) < 24 and int(tm) < 60) or "B30"


def _closes_at_end(s):
    """C3: the '[' at s[0] is matched by the last character of s (a group heading ends with the matching bracket)."""
    d = 0
    for i, c in enumerate(s):
        d += (c == "[") - (c == "]")
        if d == 0:
            return i == len(s) - 1
    return False


def changes(t):
    """CHANGES against CPAN::Changes::Spec 0.04 (S0235; v4 SPEC 8.5): None, or (code, message)."""
    if "\r" in t.replace("\r\n", "") or "\r" in t and "\n" in t.replace("\r\n", ""):
        return "B31", "CHANGES: line ends are not all LF or all CR LF (Reality's own call, as for TSV)"
    rel, two, sus, amb = [], "CHANGES line {}: {}, two readings (CPAN::Changes::Spec, S0235)", 0, 0
    at = [i for i in (t.removeprefix("\ufeff").find(c) for c in R._SEPARATORS) if i >= 0]
    if at:   # C2: as the TSV reader (T006), a character other readers take as a line break is two readings
        return "B30", f"CHANGES contains U+{ord(t.removeprefix(chr(0xFEFF))[min(at)]):04X}, which other readers take as a line or field break or a byte-order mark, two readings"
    for n, ln in enumerate(t.removeprefix("\ufeff").replace("\r\n", "\n").split("\n"), 1):
        m = re.fullmatch(r"(\S+)(\s\W*)(.*)", ln, re.A) if ln[:1].strip() else None
        v = m and _cpan_version(m[1])
        r = v and _cpan_date(m[3])
        if r and ("B30" in (v, r) or not m[2].isascii()):
            return "B30", two.format(n, "a version line's date (or a shorter date and a release note), separator (ASCII or Unicode word characters) or version (decimal or dotted) has a second reading")
        if r:
            rel.append(0)
        elif rel and ln.strip():
            if not ln[0].isspace():
                return "B30", two.format(n, "an unindented line after a release is a change or group (the spec's Groups example) or does not conform")
            if not ln[:len(ln) - len(ln.lstrip())].isascii():   # C2: U+00A0 and the like
                return "B30", two.format(n, "a line indented with a non-ASCII space is a change (Unicode whitespace) or not indented (ASCII whitespace)")
            if ln.lstrip()[0] == "[" and not _closes_at_end(ln.lstrip()):
                return "B30", two.format(n, "a line starting with '[' whose matching ']' is not its last character is a group heading or a change")
            rel[-1] += ln.lstrip()[0] != "["
        elif ln.strip():   # C1: before any release; a version-shaped line with a date and indented lines under it
            amb = amb or ln[0].isspace() and sus
            sus = not ln[0].isspace() and m and not v and re.match(r"v?\d", m[1]) and _cpan_date(m[3]) and n
    if not any(rel):
        return "B31", "CHANGES has no Version line with a Date and a change (the required elements of CPAN::Changes::Spec; S0235)"
    if amb:   # C1 (with no release after it, either reading fails: B31 above)
        return "B30", two.format(amb, "a line with a malformed version, a date and indented changes under it, before the first release, is a release or preamble")
    if 0 in rel:
        return "B30", f"CHANGES release {rel.index(0) + 1} has no change: the required changes are per release or per file, two readings (CPAN::Changes::Spec, S0235)"


def choice_point(fails, rid, what, readings):
    """v4 SPEC 8.3: the register row `rid` leaves a decision open; `readings` maps each reading to
    the result it gives. Different results: the dataset does not conform (B30). Equal: go on."""
    vals = list(readings.values())
    if any(v != vals[0] for v in vals[1:]):
        fails.append(("B30", f"{what}: BIDS 1.0.1 ({rid}) does not fix one reading ({' / '.join(readings)}), and the readings give different results (v4 SPEC 8.3)"))
        return None
    return vals[0]


def _run_key(ents, one_run):
    """Entities as a set; under the reading 'run-1 and run-01 are one run' the run is its index."""
    return {(k, str(int(v)) if one_run and k == "run" and _index(v) else v) for k, v in ents}


def _inherit_once(metas, target_path, target_ents, suffix, js, steps, one_run):
    tdir = target_path.rsplit("/", 1)[0]
    tset = _run_key(target_ents, one_run)
    ranked = []
    # v4 SPEC 9.1: metadata files indexed by (folder, suffix); only the folders on the file's
    # path are looked at, so the work is linear in the dataset (finding 18)
    segs = tdir.split("/") if tdir else []
    folders = [""] + ["/".join(segs[:i]) for i in range(1, len(segs) + 1)]
    for d in folders:
        for p, pn in metas.get(d, suffix, steps):
            if not _run_key(pn[0], one_run) <= tset:
                continue
            ranked.append((d.count("/") + (1 if d else 0), p))
    ranked.sort()
    out, clash = {}, []
    for depth, p in ranked:
        obj = js(p)
        if not isinstance(obj, dict):
            continue
        for k in sorted(obj):
            if k in out and out[k][2] == depth and out[k][0] != obj[k]:
                clash.append((k, out[k][1][0], p, depth))
            # equal values in one folder: the value rests on every file that sets it (review finding 24)
            out[k] = (obj[k], out[k][1] + (p,) if k in out and out[k][2] == depth and out[k][0] == obj[k] else (p,), depth)
    # O5: a clash a deeper file overrides decides nothing (the resolved values are what is compared)
    return {k: (v, p) for k, (v, p, _) in out.items()}, [c[:3] for c in clash if out[c[0]][2] == c[3]]


def inherited(metas, target_path, target_ents, suffix, js, fails, steps=None):
    """Metadata for a data file under the inheritance principle (register S0132, S0133; section
    8.4). A JSON file applies when it sits in the root, the subject folder or the file's own
    folder, has the same suffix, and its entities are a subset of the file's; a deeper folder
    overrides a shallower one (S0133). Two choice points (v4 SPEC 8.3, B30 when they matter):
    whether run-1 and run-01 are one run (S0265), and which of two files in one folder that set a
    key to different values applies (S0133 says nothing of one level). Equal values agree."""
    if not isinstance(metas, MetaIndex):
        metas = MetaIndex(metas)
    two, clash2 = _inherit_once(metas, target_path, target_ents, suffix, js, steps, False)
    one, clash1 = _inherit_once(metas, target_path, target_ents, suffix, js, steps, True)
    for k, a, b in clash2 + [c for c in clash1 if c not in clash2]:
        fails.append(("B30", f"{target_path}: {a} and {b} set {k} to different values in the same folder; BIDS 1.0.1 (S0133) does not say which one applies (v4 SPEC 8.3)"))
    vals = lambda m: {k: v for k, (v, _) in m.items()}  # noqa: E731
    if choice_point(fails, "S0265", f"{target_path}: whether run-1 and run-01 name one run decides which sidecars apply", {"two runs": vals(two), "one run": vals(one)}) is not None:
        for k, (v, q) in one.items():   # O13: an equal value rests on the files of both readings, the most specific included
            two[k] = (v, two[k][1] + tuple(x for x in q if x not in two[k][1]))
    return two


def bids_tsv(data, h, p, steps, room=None):
    """A BIDS 1.0.1 tabular file (section 4.2): Reality's TSV reader, plus header names that are
    distinct and do not look alike (a column named twice has two readings)."""
    t = R.parse_tsv(data, h, steps, bids=True, room=room)
    for i, row in enumerate(t.rows, start=2):
        for k, cell in enumerate(row, start=1):
            if cell == "":
                raise Refusal("B04", "reading rules", f"{p}: line {i} column {k} is empty; missing values should be coded as n/a (section 4.2, binding: SPEC 2 item 5)")
    seen = {}
    for name in t.header:
        sk = skeleton(name)
        if sk in seen:
            raise Refusal("B04", "reading rules", f"{p}: the header names {seen[sk]!r} and {name!r} are the same or look alike, so the column a name refers to has two readings (section 4.2)")
        seen[sk] = name
    return t


def read(store, mh: str):
    """Check the whole dataset named by manifest mh against BIDS 1.0.1. -> BidsDataset."""
    man = R.parse_manifest(store.text(mh), mh, store.steps)
    ds = BidsDataset(mh, man)
    store._manifests[mh] = frozenset(h for h, _ in man.values())

    # The name promises every listed file: each is supplied, with its hash and its size.
    for p, (h, size) in man.items():
        real = store.size(h) if store.locate(h) is not None else None
        if real is None:
            store.path(h, p)
        if real != size:
            raise Refusal("M003", "text", f"the manifest lists {p} with {size} bytes; the file with its hash has {real} bytes, so the manifest does not name these bytes")
        store.steps.add(size // 65536 + 1)

    if "dataset_description.json" not in man:
        raise Refusal("B01", "reading rules", "the dataset has no dataset_description.json, so it declares no BIDS version and no pinned reader applies (principle section 1, pinned versions)")
    desc = R.parse_json(store.text(man["dataset_description.json"][0], "dataset_description.json"), "dataset_description.json")
    if not isinstance(desc, dict) or not isinstance(desc.get("BIDSVersion"), str):
        raise Refusal("B01", "reading rules", "dataset_description.json declares no BIDSVersion string, so no pinned reader applies (BIDS 1.0.1 section 8.1)")
    if desc["BIDSVersion"] != VERSION:
        raise Refusal("B02", "reading rules", f"the dataset declares BIDSVersion {desc['BIDSVersion']!r}; Reality v4 has a reader only for {VERSION!r}, so nothing BIDS-based forms (principle section 1, pinned versions)")
    fails = []
    if not isinstance(desc.get("Name"), str):
        fails.append(("B01", "dataset_description.json has no Name string (section 8.1)"))
    for k in ("Authors", "ReferencesAndLinks"):   # S0224, S0229: lists
        if k in desc and not (isinstance(desc[k], list) and all(isinstance(x, str) for x in desc[k])):
            fails.append(("B01", f"dataset_description.json: {k} is not a list of strings (section 8.1)"))

    kinds = {}
    try:
        for p in man:
            kinds[p] = classify(p)
    except Unsupported as e:
        raise Refusal("B14", "reading rules", f"the dataset contains a BIDS 1.0.1 file kind this reader does not implement yet ({e}); nothing BIDS-based forms from it") from None
    def of(*ks):   # the manifest's paths of these kinds, in manifest order
        return [p for p in man if kinds[p][0] in ks]

    for p in of("badsub"):
        fails.append(("B17", f"{p} is in the folder {p.split('/')[0]}, whose subject label is not letters and digits: 1.0.1 section 10.2 (S0628) says \"hyphens and underscores are not allowed in subject labels\", so it is no subject folder and no folder 1.0.1 allows"))
    for p in of("unknown"):
        fails.append(("B17", f"{p} is in a folder BIDS 1.0.1 defines but matches none of its file names; it could be a misnamed BIDS file or an extra file, and 1.0.1 does not say which (Patsak's call 3)"))

    def text(p):
        return store.text(man[p][0], p)

    jcache = {}

    def js(p):
        if p not in jcache:
            try:
                jcache[p] = store.json(man[p][0], p)
                if not isinstance(jcache[p], dict):
                    fails.append(("B03", f"{p} is not a JSON object (section 4.3)"))
            except Refusal as e:
                if e.code[0] in "FRM":
                    raise
                fails.append(("B03", f"{e.msg} (section 4.3)"))
                jcache[p] = None
        return jcache[p]

    def tsv_ok(p):
        try:
            d = text(p)
            store.room(80 * (d.count(b"\t") + d.count(b"\n") - 1))   # (H07) its cells alone: refused before it is parsed
            return bids_tsv(d, man[p][0], p, store.steps)
        except Refusal as e:
            if e.code[0] in "FRM":
                raise
            msg = e.msg if p in e.msg else f"{p}: {e.msg}"
            fails.append(("B04", msg if "(section 4.2)" in msg else msg + " (section 4.2)"))
            return None

    json_kinds = ("meta", "func-bold-json", "func-sbref-json", "anat-json", "fmap-phasediff-json",
                  "fmap-magnitude1-json", "fmap-magnitude2-json", "phenotype-json")
    for p in man:
        if kinds[p][0] in json_kinds or p in ("participants.json", "dataset_description.json"):
            js(p)
    if "README" not in man:
        fails.append(("B01", "the dataset has no README at its root; 1.0.1 section 8.1: a README \"should be provided\" (S0233; binding by v4 SPEC 2 item 5)"))
    fails += [("B01", f"{d}/ holds files but no {d}/README; 1.0.1 section 3.4: a README \"should be found at the root of\" it (S0126; a folder with no file is not in the manifest, so it binds nothing)") for d in ("derivatives", "sourcedata") if any(q.startswith(d + "/") for q in man) and d + "/README" not in man]
    for p in ("README", "CHANGES"):
        if p in man:
            try:
                c = R.decode_utf8(text(p), p, bom_ok=True)
                fails += [x for x in [p == "CHANGES" and changes(c)] if x]
            except Refusal as e:
                fails.append(("B18", f"{e.msg}; README and CHANGES are ASCII or UTF-8 (section 8.1)"))
    metas = [(p, kinds[p][1]) for p in of(*json_kinds[:-1])]

    subjects = sorted({p.split("/")[0][4:] for p in man if "/" in p and p.startswith("sub-") and is_key(p.split("/")[0][4:])})
    ds.subjects = subjects

    # images: every defined NIfTI file has a whole header and data (section 4.1)
    headers = {}
    for p in of(*IMAGE_KINDS):
        try:
            headers[p] = store.nifti(man[p][0], p, full=True)
        except Refusal as e:
            if e.code[0] in "FRM":
                raise
            fails.append(("B05", f"{e.msg} (section 4.1)"))

    # one image per name; runs (section 4.1, 8.3, 8.4, 8.9)
    stems, groups = {}, {}
    for p in of(*IMAGE_KINDS):
        pn = kinds[p][1]
        stem = p[: p.rindex("_") + 1] + pn[1]
        if stem in stems:
            stems[stem].append(p)
            continue
        stems[stem] = [p]
        ents = dict(pn[0])
        run = ents.pop("run", None)
        groups.setdefault((p.rsplit("/", 1)[0], pn[1], tuple(sorted(ents.items()))), []).append(run)
    for stem in sorted(stems):
        if len(stems[stem]) > 1:
            fails.append(("B07", f"{stem} is stored as both .nii and .nii.gz: two files for one image (section 4.1)"))
    for key in sorted(groups):
        runs = groups[key]
        if len(runs) > 1 and None in runs:
            choice_point(fails, "S0265", f"{key[0]}: {len(runs)} {key[1]} images with the same entities, and one has no run label",
                         {"the unlabelled image is one of the indexed runs": "fewer recordings", "it is a scan of its own": "one more recording"})
        nums = {}
        for r in runs:
            if r is not None:
                nums.setdefault(int(r), set()).add(r)
        for v in sorted(nums):
            if len(nums[v]) > 1:
                choice_point(fails, "S0265", f"{key[0]}: run labels {', '.join(sorted(nums[v]))} name one index two ways",
                             {"one run": "one recording with two images", "two runs": "two recordings"})

    # functional: events need their BOLD (section 8.5); BOLD needs RepetitionTime and TaskName (8.4)
    base_of = {}
    for p in of("func-bold", "events"):
        base_of.setdefault(p[: p.rindex("_")], {}).setdefault(kinds[p][0], []).append(p)
    for stem in sorted(base_of):
        d = base_of[stem]
        if "events" in d and "func-bold" not in d:
            fails.append(("B07", f"{d['events'][0]} has no BOLD file; BIDS 1.0.1 section 8.5: \"Each task events file requires a corresponding task imaging data file\""))

    # pass 1: every image's metadata by inheritance (B15) and its number-valued keys (B21)
    image_meta = {}
    mindex = MetaIndex(metas)
    for p in of(*IMAGE_KINDS):
        ents, suffix, ext = kinds[p][1]
        meta = image_meta[p] = inherited(mindex, p, ents, suffix, js, fails, store.steps)
        for key in NUMBER_KEYS:
            if key in meta and not _is_number(meta[key][0]):
                fails.append(("B21", f"{p}: {key} is {meta[key][0]!r}, not a number ({NUMBER_KEYS[key]})"))
        if "EchoTime" in meta:
            v = meta["EchoTime"][0]
            if not (_is_number(v) or (isinstance(v, list) and v and all(_is_number(x) for x in v))):
                fails.append(("B21", f"{p}: EchoTime is {v!r}, neither a number nor a list of numbers (section 8.4)"))

    # pass 2: which BOLD images a case-1 fieldmap corresponds to (sections 8.4, 8.9). A fieldmap is
    # the images sharing one fmap stem; its IntendedFor is read from the merged metadata of each
    # of its images. A fieldmap none of whose images has IntendedFor may correspond to any scan
    # of its subject (1.0.1 makes IntendedFor optional and does not say), so it counts for all.
    fmap_targets, fm_stems, bold_of = set(), {}, {}
    for p in of("func-bold"):
        bold_of.setdefault(p.split("/")[0], set()).add(p)
    for p in of(*FMAP_IMAGES):
        fm_stems.setdefault(p[: p.rindex("_")], []).append(p)
    for stem in sorted(fm_stems):
        subdir = stem.split("/")[0]

        def intended(images):   # O7: a reading's result is the BOLD images the fieldmap corresponds to
            got = [image_meta[p]["IntendedFor"][0] for p in images if "IntendedFor" in image_meta[p]]
            ts = {subdir + "/" + x for v in got for x in ([v] if isinstance(v, str) else v if isinstance(v, list) else []) if isinstance(x, str)}
            return frozenset(ts & bold_of.get(subdir, set()) if got else bold_of.get(subdir, ()))
        # choice point (v4 SPEC 8.3): the 8.9.1 case-1 template puts IntendedFor in the phasediff
        # JSON; 8.9 says a fieldmap's files are linked by it without naming the file
        pd = [p for p in fm_stems[stem] if kinds[p][0] == "fmap-phasediff"]
        r = choice_point(fails, "S0495, S0510", f"{stem}: which JSON supplies the fieldmap's IntendedFor",
                         {"the phasediff JSON": intended(pd), "any image JSON of the fieldmap": intended(fm_stems[stem])})
        fmap_targets |= r if r is not None else intended(fm_stems[stem])

    # pass 3: BOLD images (section 8.4)
    tasknames, tasklabels, ends = {}, {}, {}
    for p in of("func-bold"):
        ents, suffix, ext = kinds[p][1]
        meta = image_meta[p]
        hd = headers.get(p)
        sub = ents[0][1]
        rec = Recording(sub, ents, p, man[p][0], ext)
        stem = p[: p.rindex("_")]
        if "events" in base_of.get(stem, {}):
            ep = base_of[stem]["events"][0]
            rec.events = (ep, man[ep][0])
        rec.meta = {key: (v, q, tuple(man[x][0] for x in q)) for key, (v, q) in meta.items()}
        rec.header = hd
        if hd is None:
            continue
        ds.recordings.append(rec)
        task = dict(ents)["task"]
        tr = meta.get("RepetitionTime")
        tn = meta.get("TaskName")
        if rec.events is not None and tr is not None and _is_number(tr[0]) and tr[0] > 0:
            ends[rec.events[0]] = (hd.dim[4] if hd.dim[0] >= 4 else 1) * tr[0]
        if tr is None or not _is_number(tr[0]) or tr[0] <= 0:
            fails.append(("B08", f"{p}: no positive RepetitionTime in its sidecar files (section 8.4, required)"))
        elif not tr_consistent(tr[0], hd):
            fails.append(("B09", f"{p}: RepetitionTime {tr[0]} s is not consistent with pixdim[4] {hd.pixdim[4]} (section 8.4; consistent means pixdim[4] is positive and is the float nearest to RepetitionTime in the header's time unit and float width)"))
        if tn is None or not isinstance(tn[0], str):
            fails.append(("B08", f"{p}: no TaskName string in its sidecar files (section 8.4, required)"))
        else:
            if "".join(c for c in tn[0] if c in K) != task:
                fails.append(("B08", f"{p}: task label {task!r} is not TaskName {tn[0]!r} with non-alphanumeric characters removed (section 8.4)"))
            if tasknames.setdefault(tn[0], task) != task:
                fails.append(("B08", f"TaskName {tn[0]!r} names two tasks ({tasknames[tn[0]]!r}, {task!r}); no two tasks may share a name (section 8.4)"))
            if tasklabels.setdefault(task, tn[0]) != tn[0]:
                fails.append(("B08", f"task {task!r} has two TaskNames ({tasklabels[task]!r}, {tn[0]!r}); the label is derived from one name (section 8.4)"))
        ped = meta.get("PhaseEncodingDirection")
        if ped is not None and (not isinstance(ped[0], str) or ped[0] not in PED):
            fails.append(("B10", f"{p}: PhaseEncodingDirection {ped[0]!r} is not one of i j k i- j- k- (section 8.4)"))
        if p in fmap_targets:
            for key in ("EchoTime", "EffectiveEchoSpacing", "PhaseEncodingDirection"):
                if key not in meta:
                    fails.append(("B10", f"{p}: {key} is required when a corresponding fieldmap is present (sections 8.4, 8.9: a fieldmap corresponds to the scans its IntendedFor names, and a fieldmap without IntendedFor may correspond to any scan of its subject, S0499: the other reading conforms only without these keys, so the result is a refusal either way)"))
        sed = meta.get("SliceEncodingDirection")
        axis = None
        if sed is not None:
            axis = {"i": 1, "j": 2, "k": 3, "i-": 1, "j-": 2, "k-": 3}.get(sed[0]) if isinstance(sed[0], str) else None
            if axis is None or (hd.dim_info >> 4) & 3 not in (0, axis):
                fails.append(("B10", f"{p}: SliceEncodingDirection {sed[0]!r} is not consistent with slice_dim in the NIfTI header (section 8.4)"))
        elif (hd.dim_info >> 4) & 3:
            axis = (hd.dim_info >> 4) & 3
        st = meta.get("SliceTiming")
        if st is not None:
            v = st[0]
            dims = [hd.dim[a] for a in (1, 2, 3) if a <= hd.dim[0]]
            want = [hd.dim[axis]] if axis is not None and axis <= hd.dim[0] else dims
            if not isinstance(v, list) or not v or not all(_is_number(x) for x in v):
                fails.append(("B10", f"{p}: SliceTiming is not a list of numbers (section 8.4)"))
            elif axis is None and want.count(len(v)) > 1:   # S0369 names no default axis: one reading per axis it fits
                fails.append(("B30", f"{p}: SliceTiming has {len(v)} times and {want.count(len(v))} axes have {len(v)} slices; neither SliceEncodingDirection nor slice_dim names the slice axis, and BIDS 1.0.1 (S0369) names no default, so the times have more than one reading (v4 SPEC 8.3)"))
            elif len(v) not in want:
                fails.append(("B10", f"{p}: SliceTiming has {len(v)} times, and the slice axis has {' or '.join(map(str, sorted(set(want))))} slices; it gives one time per slice (section 8.4)"))
            elif tr is not None and _is_number(tr[0]) and not all(0 <= x < tr[0] for x in v):
                fails.append(("B10", f"{p}: a SliceTiming time lies outside [0, RepetitionTime); times are from the beginning of the volume's acquisition (section 8.4)"))

    # events files: onset and duration first, in seconds; duration > 0 (section 8.5)
    ev_header = {}
    for p in of("events"):
        t = tsv_ok(p)
        if t is None:
            continue
        ev_header[p] = t.header
        if t.header[:2] != ["onset", "duration"]:
            fails.append(("B06", f"{p}: the first two columns are not 'onset' and 'duration' (section 8.5)"))
            continue
        cols = {c: i for i, c in enumerate(t.header)}
        store.steps.add(len(t.rows))
        for i, row in enumerate(t.rows, start=1):
            on, du = R.decimal(row[0]), R.decimal(row[1])
            if on is None or du is None or du <= 0:
                fails.append(("B06", f"{p} row {i}: onset must be a number and duration a number greater than zero (section 8.5)"))
                break
            if p in ends and on >= ends[p]:
                fails.append(("B30", f"{p} row {i}: onset {row[0]} s is at or after the end of its recording ({ends[p]} s = volumes x RepetitionTime): refused by Reality's own rule"
                              " (DESIGN section 5, call 3; register S0412), not by a reading of BIDS 1.0.1"))
                break
            if "response_time" in cols and row[cols["response_time"]] != "n/a" and R.decimal(row[cols["response_time"]]) is None:
                fails.append(("B06", f"{p} row {i}: response_time is a time in seconds or n/a (sections 8.5, 4.2)"))
                break
            if "stim_file" in cols and row[cols["stim_file"]] != "n/a" and "stimuli/" + row[cols["stim_file"]] not in man:
                fails.append(("B20", f"{p} row {i}: stim_file {row[cols['stim_file']]!r} is not a file under stimuli/ (section 8.5)"))
                break

    # fieldmaps, case 1 (section 8.9, 8.9.1)
    fstems = {}
    for p in man:
        k = kinds[p][0]
        if k.startswith("fmap-") and not k.endswith("-json"):
            fstems.setdefault(p[: p.rindex("_")], set()).add(k)
    # one case-1 fieldmap per stem that has a fieldmap image or a phasediff JSON, in the order of
    # the stem's first manifest entry: a phasediff image and a magnitude1 image are required
    for stem in dict.fromkeys(p[: p.rindex("_")] for p in of(*FMAP_IMAGES, "fmap-phasediff-json")):
        have = fstems.get(stem, set())
        if "fmap-phasediff" not in have:
            fails.append(("B12", f"{stem}: no phasediff image ({stem}_phasediff.nii[.gz]); section 8.9.1 case 1 requires it"))
        if "fmap-magnitude1" not in have:
            fails.append(("B12", f"{stem}: no magnitude1 image; section 8.9.1 case 1 requires at least magnitude1"))
    for p in of("fmap-phasediff"):
        if not all(_is_number(image_meta[p].get(x, (None,))[0]) for x in ("EchoTime1", "EchoTime2")):
            fails.append(("B12", f"{p}: its sidecar does not define EchoTime1 and EchoTime2 as numbers (section 8.9.1)"))
    for p in [p for p in of(*FMAP_IMAGES) if "IntendedFor" in image_meta[p]]:
        v = image_meta[p]["IntendedFor"][0]
        targets = [v] if isinstance(v, str) else v
        subdir = p.split("/")[0]
        if not isinstance(targets, list) or not targets or not all(isinstance(x, str) for x in targets):
            fails.append(("B12", f"{p}: IntendedFor is not a path or a list of paths (section 8.9)"))
            continue
        for x in targets:
            q = subdir + "/" + x
            if q not in man or kinds[q][0] not in IMAGE_KINDS:
                fails.append(("B12", f"{p}: IntendedFor names {x!r}, which is not an image (scan) of {subdir} (section 8.9: \"linked to a specific scan(s)\", paths \"stripped from the sub-<label>\")"))
                break

    # participants (section 8.11)
    plabels = None
    if "participants.tsv" in man:
        h = man["participants.tsv"][0]
        t = tsv_ok("participants.tsv")
        idc = [] if t is None else [i for i, c in enumerate(t.header) if c == "participant_id"]
        if t is None:
            pass
        elif len(idc) != 1:
            fails.append(("B11", "participants.tsv must have exactly one participant_id column (section 8.11)"))
        else:
            c = idc[0]
            if c != 0:   # "one compulsory column participant_id ..., followed by" the others (S0556; BB's call 12)
                fails.append(("B11", "participants.tsv: participant_id is not the first column (section 8.11)"))
            labels = []
            for i, row in enumerate(t.rows, start=1):
                v = row[c]
                if not v.startswith("sub-") or not is_key(v[4:]):
                    fails.append(("B11", f"participants.tsv row {i}: participant_id {v!r} is not sub-<label> (section 5, 8.11)"))
                    break
                labels.append(v[4:])
            if len(set(labels)) != len(labels):
                fails.append(("B11", "participants.tsv describes a participant in more than one row (section 8.11: one and only one row)"))
            sl, ll = set(subjects), set(labels)
            missing = [s for s in subjects if s not in ll]
            if missing:
                fails.append(("B11", f"{len(missing)} subject folders have no row in participants.tsv (section 8.11: each participant is described by one row); first: sub-{missing[0]}"))
            folderless = [s for s in labels if s not in sl]
            if folderless:
                fails.append(("B11", f"{len(folderless)} participants.tsv rows have no subject folder in the dataset, so the dataset the manifest names is not the whole dataset its participants file describes (Patsak's call 1); first: sub-{folderless[0]}"))
            ds.participants = ("participants.tsv", h, t, c)
            ds.ptable_labels = labels
            plabels = set(labels)
            pj = jcache.get("participants.json")
            if isinstance(pj, dict):
                for key in sorted(pj):
                    if key not in t.header or not isinstance(pj[key], dict):
                        fails.append(("B19", f"participants.json: {key!r} is not a column of participants.tsv described by an object (section 4.2)"))
                        break
                    fails.extend(column_fails("participants.json", key, pj[key], True))
    elif "participants.json" in man:
        fails.append(("B19", "participants.json describes a participants.tsv the dataset does not have (section 4.2)"))

    # phenotype (section 8.11)
    known = plabels if plabels is not None else set(subjects)
    for p in of("phenotype-tsv"):
        t = tsv_ok(p)
        if t is None:
            continue
        idc = [i for i, c in enumerate(t.header) if c == "participant_id"]
        if len(idc) != 1:
            fails.append(("B22", f"{p}: a phenotype file has exactly one participant_id column (section 8.11)"))
            continue
        bad = [row[idc[0]] for row in t.rows if not row[idc[0]].startswith("sub-") or row[idc[0]][4:] not in known]
        if bad:
            fails.append(("B22", f"{p}: participant_id {bad[0]!r} is not a participant of the dataset (section 8.11: \"with matching sub-<participant_label>\")"))

    # dictionaries (v4 SPEC 8.4; section 4.2): keys name columns of the TSV(s) described
    def dictionary(p, headers, allowed=()):
        obj = jcache.get(p)
        if not headers:
            fails.append(("B19", f"{p} is a data dictionary, and the dataset has no TSV file it describes (section 4.2)"))
        elif isinstance(obj, dict):
            cols = set().union(*headers)
            for key in sorted(obj):
                if key not in allowed and (key not in cols or not isinstance(obj[key], dict)):
                    fails.append(("B19", f"{p}: {key!r} is not a column of the TSV file(s) it describes, described by an object (section 4.2)"))
                    break
                fails.extend(column_fails(p, key, obj[key], bool(allowed)))
    for q in sorted(ev_header):   # O14: an events file's dictionaries inherit as sidecars do, with the same B30 choice points
        inherited(mindex, q, kinds[q][1][0], "events", js, fails, store.steps)
    for p in man:
        k, pn = kinds[p]
        if k == "phenotype-json":
            q = p[:-5] + ".tsv"
            t = tsv_ok(q) if q in man else None
            dictionary(p, [t.header] if t is not None else [] if q not in man else [[]], ("MeasurementToolMetadata",))
        elif k == "meta" and pn[1] == "events":
            d = p.rsplit("/", 1)[0] + "/" if "/" in p else ""
            dset = _run_key(pn[0], False)
            dictionary(p, [h for q, h in ev_header.items() if q.startswith(d) and dset <= _run_key(kinds[q][1][0], False)])

    if fails:
        first = {}
        for c, m in fails:
            first.setdefault(c, m)   # codes in order of their first failure
        detail = "; ".join(f"{c} x{sum(x == c for x, _ in fails)}, first: {m}" for c, m in first.items())
        raise Refusal("B00", "reading rules", f"the dataset does not conform to BIDS {VERSION} ({len(fails)} failures), so nothing BIDS-based forms from it (principle section 1, whole-dataset conformance). {detail}")
    return ds

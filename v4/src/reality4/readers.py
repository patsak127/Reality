"""The fixed readers of Reality v4: supplied files by hash, bytes, plain TSV, decimals, JSON,
NIfTI headers and Reality manifests. They are fixed before any claim exists; no claim can
choose or change one (principle section 1, Reading rules).

Bounds are the same numbers on every machine and are counted per statement (principle item 4).
The store is a pure function of the supplied files: which bytes it can find never depends on
the statements checked before, and a cached result is charged the same steps as a fresh one."""

import bisect
import gzip
import io
import hashlib
import json
import os
import struct
import zlib
from fractions import Fraction

from .keys import invisible

MAX_TEXT_FILE = 64 * 1024 * 1024        # a TSV, JSON or manifest file read whole
MAX_TEXT_TOTAL = 256 * 1024 * 1024      # all such files read in one statement
MAX_STEPS = 200_000_000                 # counted operations in one statement
MAX_MANIFEST_ENTRIES = 1_000_000
MAX_GZ_HEAD = 1 << 20                   # compressed bytes read to reach a .nii.gz header
MAX_DIGITS = 1000                       # digits of any number read or written
MAX_EXPONENT = 1000                     # |exponent| of a JSON number
MAX_JSON_DEPTH = 64
CHUNK = 1 << 20
MANIFEST_MAGIC = "reality-manifest 1"
MAX_ACCOUNTED = 1 << 30                 # [prov] v4 SPEC 9.4: accounted bytes per program


class Refusal(Exception):
    """A text that does not form. `item` names the principle item or clause it breaks."""

    def __init__(self, code: str, item: str, msg: str):
        super().__init__(msg)
        self.code, self.item, self.msg = code, item, msg


class Steps:
    def __init__(self):
        self.n = 0

    def add(self, k: int = 1):
        self.n += k
        if self.n > MAX_STEPS:
            raise Refusal("R002", "bounds", f"the statement needs more than {MAX_STEPS} counted steps (Reality bounds)")


def linked(path) -> bool:
    """A symlink, or a Windows junction, which os.path.islink does not report and os.walk enters:
    no component of a path under --root or --files may be either (v4 SPEC 9.5; fix pass W1)."""
    return os.path.islink(path) or os.path.isjunction(path)


def sha256_file(path: str):
    h, size = hashlib.sha256(), 0
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
            size += len(b)
    return h.hexdigest(), size


class Store:
    """Files supplied beside a program, found by their SHA-256 only.

    `files`: files or folders; every file under them is hashed when the store is made.
    `roots`: dataset roots. A file is also found at root/<path> for every <path> that any
    supplied Reality manifest lists with its hash, and only if the bytes there hash to it.
    Both lookups are fixed when the store is made, so what can be found is the same for every
    statement and does not depend on the order of supply or on which copy was found."""

    def __init__(self, files=(), roots=()):
        # v4 SPEC 9.5: every path is bytes, never decoded through the locale (os.fsencode of a
        # command-line argument gives back the argument's own bytes)
        files = [os.fsencode(p) for p in files]
        roots = [os.fsencode(r) for r in roots]
        self.by_hash = {}
        for p in files:
            if os.path.isdir(p):
                for dp, dns, fns in os.walk(p):
                    dns[:] = sorted(d for d in dns if not linked(os.path.join(dp, d)))   # os.walk enters a junction
                    for fn in sorted(fns):
                        self._add(os.path.join(dp, fn))
            elif os.path.isfile(p):
                self._add(p)
        self.roots = sorted(roots)
        self.hints = {}
        for h in sorted(self.by_hash):
            p = self.by_hash[h]
            try:
                with open(p, "rb") as f:
                    head = f.read(len(MANIFEST_MAGIC) + 1)
                if head != (MANIFEST_MAGIC + "\n").encode() or os.path.getsize(p) > MAX_TEXT_FILE:
                    continue   # no statement could read a larger one (R003), so it gives no hints
                with open(p, "rb") as f:
                    man = parse_manifest(f.read(), h)   # a manifest past MAX_STEPS gives none (R002)
            except (Refusal, OSError):
                continue
            for rel, (eh, _) in man.items():
                self.hints.setdefault(eh, set()).add(rel)
        self._found = {}
        self._names = {}   # folder -> the names its listing holds (bytes), read once
        self._memo = {}
        self._sizes = {}   # memo key -> accounted bytes (v4 SPEC 9.4)
        self.begin_program()
        self._manifests = {}   # manifest hash -> the entry hashes it lists (filled when one is read as a dataset)
        self.begin()

    def _add(self, path):
        if linked(path) or not os.path.isfile(path):
            return
        try:
            h, _ = sha256_file(path)
        except OSError:
            return   # a file the process cannot read supplies no bytes (v4 SPEC 9.5, finding 16)
        self.by_hash.setdefault(h, path)

    def begin(self):
        """Start a statement: fresh step and byte budgets; the program's accounted memory goes on (v4 SPEC 9.4)."""
        self.held0, self.seen0 = self.prog_bytes, set(self.prog_seen)
        self.steps = Steps()
        self.text_total = 0
        self.anon0 = dict(self.anon_by)
        self.log = set()    # hashes whose bytes a value was computed from in this statement
        self.gate = set()   # hashes read only to check a dataset's conformance (a gate, not a value)

    def locate(self, h: str):
        if h in self._found:
            return self._found[h]
        p = self.by_hash.get(h)
        if p is None:
            for r in self.roots:
                for rel in sorted(self.hints.get(h, ())):
                    cand = self.under(r, rel)
                    try:
                        if cand is not None and os.path.isfile(cand) and sha256_file(cand)[0] == h:
                            p = cand
                            break
                    except OSError:
                        continue   # unreadable: not found (v4 SPEC 9.5)
                if p is not None:
                    break
        self._found[h] = p
        return p

    def under(self, root, rel):
        """root/rel, or None unless every component is in its folder's listing byte for byte (so a
        case-insensitive or normalising file system cannot match README to readme) and none is a
        symlink or a junction (v4 SPEC 9.5; fix pass W1, W2)."""
        cur = root
        for seg in rel.split("/"):
            if cur not in self._names:
                try:
                    self._names[cur] = frozenset(os.listdir(cur))
                except OSError:
                    self._names[cur] = frozenset()
            seg = seg.encode("utf-8")
            if seg not in self._names[cur] or linked(os.path.join(cur, seg)):
                return None
            cur = os.path.join(cur, seg)
        return cur

    def path(self, h: str, what: str | None = None) -> str:
        p = self.locate(h)
        if p is None:
            where = f" (the manifest names it {what!r})" if what else ""
            raise Refusal("F001", "text", f"no supplied file has sha256:{h}{where}; the text names it, so its bytes are part of the text")
        return p

    def size(self, h: str) -> int:
        p = self.path(h)
        self.log.add(h)
        return os.path.getsize(p)

    # ---- v4 SPEC 9.4: accounted memory --------------------------------------------------------

    def begin_program(self):
        """Start a program: its accounted bytes start at 0. The memo is pure, so dropping it
        between programs never changes a verdict; (A08, Argon review 08) it is dropped at each, so
        the memory a program holds is only what it accounts (SPEC 9.4: the floor)."""
        self._memo.clear()
        self._sizes.clear()
        self.prog_seen = set()
        self.prog_bytes = 0
        self.anon_by = {}   # (B0304; C02) bytes accounted with no memo key (kernel's where() rows), by the statement that made them

    def account(self, n: int):
        self.room(n)
        self.prog_bytes += n

    def held(self, hs, pre):
        """(H03, Opus 5.5 max2 review 03) The accounted bytes the program held when this statement began, less every
        structure made from the bytes hs (the files the statement reads, itself or through its lets; SPEC-EXACT 1),
        made by this statement's lets or any earlier statement (B0304, Argon review 2 03 and 04), and (C02, review 3 02)
        every where() row the earlier lets and claims pre (decide.prefix's: each reads a file of hs) made, from any file.
        A certificate charges them again on its candidate (decide.prefix, witness.evaluate): its memo keeps the other
        files' keyed structures, so they are charged once, but it runs each where() of pre again."""
        return self.held0 - sum(self._sizes.get(k, 64) for k in self.seen0 if len(k) > 1 and k[1] in hs) - sum(n for i, n in self.anon0.items() if i in pre)

    def room(self, n: int):
        if self.prog_bytes + n > MAX_ACCOUNTED:
            raise Refusal("R012", "bounds", f"the program would keep more than {MAX_ACCOUNTED} accounted bytes in memory (Reality bounds, v4 SPEC 9.4)")

    def _use(self, key):
        if key not in self.prog_seen:
            self.prog_seen.add(key)
            self.account(self._sizes.get(key, 64))

    def _cached(self, key, cost, make, size=None, pre=0):
        """A pure computation on fixed bytes: computed once, charged `cost` every time; pre: its size when known before it
        is made (A08: refused before, not after)."""
        if key not in self._memo:
            self.room(pre)
            self._memo[key] = make()
            self._sizes[key] = size(self._memo[key]) if size else 1024
        self._use(key)
        st, tt = cost(self._memo[key])
        self.steps.add(st)
        self.text_total += tt
        if self.text_total > MAX_TEXT_TOTAL:
            raise Refusal("R003", "bounds", f"the files read whole in one statement exceed {MAX_TEXT_TOTAL} bytes (Reality bounds)")
        return self._memo[key]

    def measured(self, key, fn):
        """A gate: a pure computation (fn) whose whole cost is recorded once and charged on every
        use; a refusal it raises is kept and raised again. What it reads is logged as gate reads."""
        if key not in self._memo:
            saved = (self.steps, self.text_total, self.log, self.gate)
            self.steps, self.text_total, self.log, self.gate = Steps(), 0, set(), set()
            try:
                res = (True, fn())
            except Refusal as e:
                res = (False, e)
            finally:
                cost = (self.steps.n, self.text_total, frozenset(self.log | self.gate))
                self.steps, self.text_total, self.log, self.gate = saved
            if not res[0] and res[1].code == "R012":
                raise res[1]   # (H07) the program's memory, not the bytes: not kept for another program
            self._memo[key] = (res, cost)
            self._sizes[key] = 1024 * (len(self._manifests.get(key[1], ())) + 1)
        self._use(key)
        (ok, v), (st, tt, gate) = self._memo[key]
        self.gate |= gate
        self.steps.add(st)
        self.text_total += tt
        if self.text_total > MAX_TEXT_TOTAL:
            raise Refusal("R003", "bounds", f"the files read whole in one statement exceed {MAX_TEXT_TOTAL} bytes (Reality bounds)")
        if not ok:
            raise v
        return v

    def slice(self, h: str, o: int, n: int) -> bytes:
        """n bytes from offset o (the caller has checked o + n <= size)."""
        p = self.path(h)
        self.log.add(h)
        self.steps.add(n // 64 + 1)
        with open(p, "rb") as fh:
            fh.seek(o)
            b = fh.read(n)
        if len(b) != n:
            raise Refusal("F002", "text", f"sha256:{h} changed while it was being read")
        return b

    def text(self, h: str, what: str | None = None) -> bytes:
        p = self.path(h, what)
        self.log.add(h)
        size = os.path.getsize(p)
        if size > MAX_TEXT_FILE:
            raise Refusal("R003", "bounds", f"sha256:{h} is {size} bytes; a file read whole is at most {MAX_TEXT_FILE} bytes (Reality bounds)")

        def make():
            with open(p, "rb") as f:
                data = f.read()
            if hashlib.sha256(data).hexdigest() != h:
                raise Refusal("F002", "text", f"sha256:{h} changed while it was being read")
            return data
        return self._cached(("text", h), lambda d: (len(d) // 64 + 1, len(d)), make, lambda d: len(d) + 64)

    def json(self, h: str, what: str | None = None):
        data = self.text(h, what)
        return self._cached(("json", h), lambda v: (len(data) // 64 + 1, 0), lambda: parse_json(data, what or f"sha256:{h}"), lambda v: 64 * len(data) + 64, 64 * len(data) + 64)

    def json_file(self, h: str):
        """Reality's file-level JSON reader (principle section 11); the same reading as the
        BIDS reader's, cached apart so a file read both ways is charged once per reader."""
        data = self.text(h)
        return self._cached(("json-file", h), lambda v: (len(data) // 64 + 1, 0), lambda: parse_json(data, f"sha256:{h}"), lambda v: 64 * len(data) + 64, 64 * len(data) + 64)

    def nifti_file(self, h: str):
        """One hashed file read as a NIfTI header (v4 SPEC 7.6): gzip by its magic bytes 1f 8b,
        which no uncompressed NIfTI-1 or NIfTI-2 header can begin with; only the header is read."""
        what = f"sha256:{h}"
        self.log.add(h)   # read on a cache hit too, as every other reader (check 2)

        def make():
            size = self.size(h)
            if self.slice(h, 0, min(size, 2)) != b"\x1f\x8b":
                return nifti_header(self.slice(h, 0, min(size, 544)), what), False
            return nifti_header(gz_head(lambda o, n: self.slice(h, o, n), size, what), what), True
        if self.slice(h, 0, min(self.size(h), 2)) == b"\x1f\x8b":   # O8: first, the whole stream must be gzip (I004),
            self.measured(("gz-whole", h), lambda: gz_whole(lambda o, n: self.slice(h, o, n), self.size(h), what, self.steps))
        return self._cached(("nifti-file", h), lambda v: (1, 0), make, lambda v: 2048)

    def nifti(self, h: str, what: str, full: bool):
        p = self.path(h, what)
        self.log.add(h)
        size = os.path.getsize(p)
        return self._nifti(h, what, full, (size // 4096 + 1) if full else 1, lambda m: nifti_read(p, what.endswith(".gz"), what, full, None, m))

    def _nifti(self, h, what, full, st, read):
        """(B05, Argon review 2 05) A NIfTI image's header, or with full its whole stream: a .nii.gz read whole is counted
        per 4096 bytes it decompresses to as it is read (the statement's steps, so R002 stops it there), and that count
        is charged beside st (the caller's charge for its bytes) on every use."""
        gz, m = what.endswith(".gz"), Steps()
        m.n = self.steps.n
        return self._cached(("nifti", h, full, gz), lambda v: (st + v[1], 0),
                            lambda: (read(m if full and gz else None), m.n - self.steps.n), lambda v: 2048)[0]


# ---- plain TSV ----------------------------------------------------------------------------

class Table:
    """Reality's plain TSV reading of one file: line 1 is the header, every other line a row.
    Positions are 1-based. Cells are the decoded text of their bytes (UTF-8, strict)."""

    def __init__(self, h, header, rows, bom=False):
        # bom: the file began with a byte-order mark, so the first header name has two readings
        # (with U+FEFF or without); only a use of that name refuses (SPEC 6.1, T001)
        self.h, self.header, self.rows, self.bom = h, header, rows, bom


def decode_utf8(data: bytes, what: str, bom_ok: bool = False) -> str:
    """Strict UTF-8. A byte-order mark is refused (T001: in a table it could belong to the first
    cell or not); bom_ok is only for README/CHANGES, which nothing parses into cells (BIDS 1.0.1
    section 8.1 asks for ASCII or UTF-8, and a BOM-prefixed file is valid UTF-8)."""
    if data.startswith(b"\xef\xbb\xbf") and not bom_ok:
        raise Refusal("T001", "2", f"{what} starts with a byte-order mark: it could be part of the first cell or not, two readings")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        raise Refusal("T001", "2", f"{what} is not UTF-8 at byte {e.start}: Reality's text reader gives it no reading") from None


_SEPARATORS = {"\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029", "\ufeff", "\x00"}


def _text(data: bytes, what: str, kind: str, bids: bool = False):
    """The text of a table file and whether it began with a byte-order mark (SPEC 6.1): lines end
    all with LF or all with CR LF (else T010), and a CR anywhere else refuses (T002)."""
    if b"\r" in data.replace(b"\r\n", b""):
        raise Refusal("T002", "2", f"{what} contains a carriage return that is not immediately followed by a line feed: it could end a line or belong to a cell, two readings")
    crlf, lf = data.count(b"\r\n"), data.count(b"\n")
    if 0 < crlf < lf:
        raise Refusal("T010", "2", f"{what} ends {crlf} lines with CR LF and {lf - crlf} with LF alone: mixed line ends, two readings of where lines end (Patsak, 25 Oct 2026 22:29)")
    data = data.replace(b"\r\n", b"\n")
    bom = not bids and data.startswith(b"\xef\xbb\xbf")
    text = decode_utf8(data[3:] if bom else data, what)
    if text == "":
        raise Refusal("T003", "1", f"{what} is empty: there is no header line, so it is not a table under Reality's {kind} reader")
    at = [i for i in (text.find(c) for c in _SEPARATORS) if i >= 0]
    if at:
        bad = text[min(at)]   # the first one in the file, so the message does not depend on set order
        raise Refusal("T006", "2", f"{what} contains U+{ord(bad):04X}, which other readers take as a line or field break or a byte-order mark: two readings")
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return text, bom, lines


def _table(h, what, lines, split, bids, bom, unit, room=None):
    """Lines to a Table: the blank-line, header-name and row-width rules both readers share. room: the store's, given the
    table's accounted bytes (kernel._table_size) so far at each row (A08: R012 while it is built, as after)."""
    header = split(lines[0], 1) if lines else [""]
    if (not bids and len(lines) >= 2 and lines[-1] == "" and len(header) >= 2):
        lines.pop()   # one final empty line in a multi-column table: its only table reading is "no row" (SPEC 6.1)
    for i, ln in enumerate(lines, start=1):
        if ln == "":
            if len(header) >= 2:
                raise Refusal("T003", "2", f"{what} line {i} is empty: an empty line is a row only if the table has one column, and this one is not the last line")
            raise Refusal("T003", "2", f"{what} line {i} is empty: in a one-column table it could be a row with one empty cell or no row, two readings")
    for k, name in enumerate(header, start=1):
        if name == "":
            raise Refusal("T007", "1", f"{what} header column {k} has no name; blank headers are refused (principle section 3)")
    rows, n = [], 128 + sum(80 + len(c) for c in header)
    for i, ln in enumerate(lines[1:], start=2):
        cells = split(ln, i)
        if len(cells) != len(header):
            raise Refusal("T004", "1", f"{what} line {i} has {len(cells)} {unit} and the header has {len(header)}: the table's columns are not fixed by its bytes")
        rows.append(cells)
        n += 64 + sum(80 + len(c) for c in cells)
        if room:
            room(n)
    return Table(h, header, rows, bom)


def parse_tsv(data: bytes, h: str, steps: Steps, bids: bool = False, room=None) -> Table:
    """Reality's plain TSV reader (v4 SPEC 6.1). With bids=True the BIDS rules of SPEC 6.2 apply
    on top (bids_tsv), and a byte-order mark refuses the file (T001)."""
    what = f"sha256:{h}"
    text, bom, lines = _text(data, what, "TSV", bids)
    steps.add(len(text) // 64 + 1)
    if '"' in text:
        raise Refusal("T005", "2", f"{what} contains a double quote: TSV readers that take quotes as escapes and readers that don't give two readings (the same rule as the BIDS reader)")
    return _table(h, what, lines, lambda ln, i: ln.split("\t"), bids, bom, "cells", room)


def _csv_fields(ln: str, i: int, what: str) -> list:
    """One CSV line's fields under RFC 4180, refusing every byte sequence readers split two ways."""
    cells, j, n = [], 0, len(ln)
    while True:
        if ln[j:j + 1] == '"':
            k, buf = j + 1, []
            while True:
                q = ln.find('"', k)
                if q < 0:
                    raise Refusal("T008", "2", f"{what} line {i}: a quoted field does not close on its line; Reality does not read line breaks inside quotes (a line reader and an RFC 4180 reader split the rows differently)")
                buf.append(ln[k:q])
                if ln[q + 1:q + 2] != '"':
                    break
                buf.append('"')
                k = q + 2
            j = q + 1
            if j < n and ln[j] != ",":
                raise Refusal("T008", "2", f"{what} line {i}: {ln[j]!r} follows a closing quote; RFC 4180 gives it no reading and readers differ")
            cells.append("".join(buf))
        else:
            c = ln.find(",", j)
            cell, j = (ln[j:], n) if c < 0 else (ln[j:c], c)
            if '"' in cell:
                raise Refusal("T008", "2", f"{what} line {i}: a double quote inside an unquoted field; RFC 4180 gives it no reading and readers differ")
            for d, nm in (("\t", "tab"), (";", "semicolon")):
                if d in cell:
                    raise Refusal("T009", "2", f"{what} line {i}: a {nm} outside quotes; it could be the file's delimiter or part of a cell, two readings (principle section 12: the comma is the only delimiter)")
            cells.append(cell)
        if j >= n:
            return cells
        j += 1          # past the comma
        if j == n:
            return cells + [""]


def parse_csv(data: bytes, h: str, steps: Steps, room=None) -> Table:
    """Reality's CSV reader (v4 SPEC 6.5, principle section 12): RFC 4180 with the comma as the
    only delimiter. Cells are their bytes with the quoting removed, nothing trimmed. A byte-order
    mark, line ends, blank lines and header names follow the plain TSV reader (SPEC 6.1)."""
    what = f"sha256:{h}"
    text, bom, lines = _text(data, what, "CSV")
    steps.add(len(text) // 64 + 1)
    return _table(h, what, lines, lambda ln, i: _csv_fields(ln, i, what), False, bom, "fields", room)


DIGITS = frozenset("0123456789")


def decimal(s: str):
    """Reality's number reader, one grammar for TSV cells and JSON (v4 SPEC 6.4):
    -?(0|[1-9][0-9]*)(.[0-9]+)?([eE][+-]?[0-9]+)? in ASCII (JSON's), the exact rational. At most
    MAX_DIGITS digits before the exponent and |exponent| <= MAX_EXPONENT, else R007."""
    m, e, x = s.replace("E", "e").partition("e")
    xd = x[1:] if x[:1] in ("+", "-") else x
    t = m[1:] if m.startswith("-") else m
    a, dot, b = t.partition(".")
    if a == "" or not set(a) <= DIGITS or a[:1] == "0" != a or (dot and (b == "" or not set(b) <= DIGITS)):
        return None
    if e and (xd == "" or not set(xd) <= DIGITS):
        return None   # O3: the whole cell is matched against the grammar before any bound (R007) is applied
    if e and (len(xd) > 6 or int(xd) > MAX_EXPONENT):
        raise Refusal("R007", "bounds", f"a number with the exponent {x[:12]}; Reality reads exponents up to {MAX_EXPONENT} (Reality bounds, the same on every machine)")
    if len(a) + len(b) > MAX_DIGITS:
        raise Refusal("R007", "bounds", f"a number with {len(a) + len(b)} digits; Reality reads at most {MAX_DIGITS} (Reality bounds, the same on every machine)")
    q = Fraction(int(a + b), 10 ** len(b))
    if e:
        q *= Fraction(10) ** int(x)
    return -q if m.startswith("-") else q


# ---- JSON ---------------------------------------------------------------------------------

def json_depth(text: str) -> int:
    depth = best = 0
    i, n, instr = 0, len(text), False
    while i < n:
        c = text[i]
        if instr:
            if c == "\\":
                i += 1
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c in "[{":
            depth += 1
            best = max(best, depth)
        elif c in "]}":
            depth -= 1
        i += 1
    return best


def _number(s: str, what: str) -> Fraction:
    """A JSON number (already in RFC 8259's grammar) through Reality's number reader."""
    try:
        q = decimal(s)
    except Refusal:
        raise Refusal("R007", "bounds", f"{what} has the number {s[:40]}{'...' if len(s) > 40 else ''}; Reality reads at most {MAX_DIGITS} digits and exponents up to {MAX_EXPONENT} (Reality bounds)") from None
    if q is None:
        raise Refusal("J001", "1", f"{what} has a number Reality's reader does not read: {s[:40]}")
    return q


def parse_json(data: bytes, what: str):
    """RFC 8259 JSON in UTF-8. Numbers are read as exact rationals. A duplicate key, NaN or
    Infinity, or a string with a lone surrogate has no single reading and is refused. Nesting,
    digits and exponents are bounded before anything is parsed."""
    text = decode_utf8(data, what)
    if json_depth(text) > MAX_JSON_DEPTH:
        raise Refusal("R008", "bounds", f"{what} nests deeper than {MAX_JSON_DEPTH} (Reality bounds)")

    def pairs(ps):
        d = {}
        for k, v in ps:
            if k in d:
                raise Refusal("J002", "2", f"{what} has the key {k!r} twice in one object: two readings")
            d[k] = v
        return d

    def const(c):
        raise Refusal("J003", "2", f"{what} contains {c}, which is not a JSON number")

    num = lambda s: _number(s, what)  # noqa: E731
    try:
        v = json.loads(text, object_pairs_hook=pairs, parse_float=num, parse_int=num, parse_constant=const)
    except Refusal:
        raise
    except ValueError as e:
        raise Refusal("J001", "1", f"{what} is not JSON: {str(e).split(':')[0]}") from None
    stack = [v]
    while stack:
        x = stack.pop()
        if isinstance(x, str):
            try:
                x.encode("utf-8")
            except UnicodeEncodeError:
                raise Refusal("J003", "2", f"{what} has a string with a lone surrogate") from None
        elif isinstance(x, dict):
            stack.extend(x.keys())
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)
    return v


# ---- NIfTI --------------------------------------------------------------------------------

NIFTI_BITPIX = {2: 8, 4: 16, 8: 32, 16: 32, 32: 64, 64: 64, 128: 24, 256: 8, 512: 16,
                768: 32, 1024: 64, 1280: 64, 1536: 128, 1792: 128, 2048: 256, 2304: 32}
TIME_UNITS = {8: Fraction(1), 16: Fraction(1, 1000), 24: Fraction(1, 1000000)}  # to seconds


class NiftiHeader:
    def __init__(self, version, dim, pixdim, datatype, bitpix, vox_offset, xyzt_units, dim_info):
        self.version, self.dim, self.pixdim = version, dim, pixdim
        self.datatype, self.bitpix, self.vox_offset = datatype, bitpix, vox_offset
        self.xyzt_units, self.dim_info = xyzt_units, dim_info

    def data_bytes(self) -> int:
        n = 1
        for k in range(1, self.dim[0] + 1):
            n *= self.dim[k]
        return self.vox_offset + n * self.bitpix // 8


def _float(b: bytes, fmt: str):
    x = struct.unpack(fmt, b)[0]
    if x != x or x in (float("inf"), float("-inf")):
        return None
    return Fraction(x)


def nifti_header(head: bytes, what: str) -> NiftiHeader:
    """Read a single-file NIfTI-1 or NIfTI-2 header from the first bytes of the image."""
    if len(head) < 4:
        raise Refusal("I001", "1", f"{what} is too short to be NIfTI")
    for end in ("<", ">"):
        sz = struct.unpack(end + "i", head[:4])[0]
        if sz == 348:
            if len(head) < 352 or head[344:348] != b"n+1\x00":
                raise Refusal("I001", "1", f"{what}: NIfTI-1 header without the single-file magic 'n+1'")
            dim = list(struct.unpack(end + "8h", head[40:56]))
            datatype, bitpix = struct.unpack(end + "2h", head[70:74])
            pixdim = [_float(head[76 + 4 * k:80 + 4 * k], end + "f") for k in range(8)]
            vo = _float(head[108:112], end + "f")
            if vo is None or vo.denominator != 1:
                raise Refusal("I001", "1", f"{what}: vox_offset is not a whole number")
            return _check(NiftiHeader(1, dim, pixdim, datatype, bitpix, int(vo), head[123], head[39]), 352, what)
        if sz == 540:
            if len(head) < 544 or head[4:12] != b"n+2\x00\r\n\x1a\n":
                raise Refusal("I001", "1", f"{what}: NIfTI-2 header without the single-file magic 'n+2'")
            datatype, bitpix = struct.unpack(end + "2h", head[12:16])
            dim = list(struct.unpack(end + "8q", head[16:80]))
            pixdim = [_float(head[104 + 8 * k:112 + 8 * k], end + "d") for k in range(8)]
            vo = struct.unpack(end + "q", head[168:176])[0]
            xyzt = struct.unpack(end + "i", head[500:504])[0]
            return _check(NiftiHeader(2, dim, pixdim, datatype, bitpix, vo, xyzt, head[524]), 544, what)
    raise Refusal("I001", "1", f"{what} has no NIfTI-1 or NIfTI-2 header (sizeof_hdr is neither 348 nor 540 in either byte order)")


def _check(hd: NiftiHeader, minoff: int, what: str) -> NiftiHeader:
    if not 1 <= hd.dim[0] <= 7 or any(hd.dim[k] < 1 for k in range(1, hd.dim[0] + 1)):
        raise Refusal("I002", "1", f"{what}: dim {hd.dim} does not give a size along every axis")
    if NIFTI_BITPIX.get(hd.datatype) != hd.bitpix:
        raise Refusal("I002", "2", f"{what}: datatype {hd.datatype} and bitpix {hd.bitpix} disagree")
    if hd.vox_offset < minoff:
        raise Refusal("I002", "1", f"{what}: vox_offset {hd.vox_offset} lies inside the header")
    return hd


def gz_head(read, size: int, what: str) -> bytes:
    """The first 544 bytes a gzip stream decompresses to, reading at most MAX_GZ_HEAD compressed
    bytes (read(offset, n) gives them): empty deflate blocks cannot make the header cost more."""
    d, out, off, tail = zlib.decompressobj(16 + zlib.MAX_WBITS), b"", 0, b""
    try:
        while len(out) < 544:
            new = d.eof   # RFC 1952: a file may hold several members; read on into the next, as gzip.open does
            tail, d = (d.unused_data, zlib.decompressobj(16 + zlib.MAX_WBITS)) if new else (tail, d)
            chunk, tail = d.unconsumed_tail or tail, b""
            if (not chunk or new and len(chunk) < 2) and off < size:   # O8: a member's magic may straddle two reads
                if off >= MAX_GZ_HEAD:
                    raise Refusal("R003", "bounds", f"{what}: the NIfTI header is not within the first {MAX_GZ_HEAD} compressed bytes (Reality bounds)")
                chunk, off = chunk + read(off, min(65536, size - off)), min(off + 65536, size)
            if not chunk or new and not chunk.startswith(b"\x1f\x8b"):
                break   # the end, or padding or other bytes after a member: the header is what the members gave
            out += d.decompress(chunk, 544 - len(out))
    except zlib.error:
        raise Refusal("I004", "1", f"{what}: starts like gzip but is not a gzip stream") from None
    return out


def gz_whole(read, size: int, what: str, steps):
    """O8 (v4 SPEC 7.6): a .nii.gz read for its header is still one whole gzip file: one or more
    members (RFC 1952), each ending in its CRC-32 and length, then nothing or zero bytes (as gzip.open
    reads it), else I004. Charged per compressed byte (read) and per 4096 decompressed bytes."""
    d, off, buf, members = None, 0, b"", 0
    while True:
        if (not buf or d is None and len(buf) < 2) and off < size:
            buf, off = buf + read(off, min(CHUNK, size - off)), min(off + CHUNK, size)
        if not buf:
            break
        if d is None:   # between members: another member, or zero padding up to the end
            if buf[:2] != b"\x1f\x8b":
                if buf.strip(b"\0"):
                    raise Refusal("I004", "1", f"{what}: bytes after the last gzip member are neither a member nor zero padding")
                buf = b""
                continue
            d, members = zlib.decompressobj(16 + zlib.MAX_WBITS), members + 1
        try:
            steps.add(len(d.decompress(buf, CHUNK)) // 4096 + 1)
        except zlib.error:
            raise Refusal("I004", "1", f"{what}: not a whole gzip stream (a member is corrupt)") from None
        buf = d.unconsumed_tail
        if d.eof:
            buf, d = d.unused_data, None
    if d is not None or members == 0:
        raise Refusal("I004", "1", f"{what}: not a whole gzip stream (it ends inside a member)")


def nifti_read(path, gz: bool, what: str, full: bool, data: bytes | None = None, steps: Steps | None = None) -> NiftiHeader:
    """Read the header; with `full`, also stream the whole image and check that it holds at
    least the bytes the header implies (and, for .nii.gz, that the gzip stream is whole); steps (B05): each chunk read
    counted as it is read (len // 4096 + 1)."""
    if gz and not full:   # the header only: bounded compressed reading, as for nifti(f)
        with open(path, "rb") if data is None else io.BytesIO(data) as f:
            size = f.seek(0, 2)
            return nifti_header(gz_head(lambda o, n: (f.seek(o), f.read(n))[1], size, what), what)
    try:
        src = path if data is None else io.BytesIO(data)   # data: a witness candidate's bytes
        f = gzip.open(src, "rb") if gz else (open(src, "rb") if data is None else src)
        with f:
            head = f.read(544)
            hd = nifti_header(head, what)
            if full:
                n = len(head)
                while True:
                    b = f.read(CHUNK)
                    if not b:
                        break
                    n += len(b)
                    if steps is not None:
                        steps.add(len(b) // 4096 + 1)
                if n < hd.data_bytes():
                    raise Refusal("I003", "1", f"{what}: holds {n} bytes of image, the header implies {hd.data_bytes()}")
            return hd
    except (OSError, EOFError, zlib.error) as e:
        raise Refusal("I004", "1", f"{what}: not a whole gzip stream ({type(e).__name__})") from None


# ---- Reality manifests ----------------------------------------------------------------------

def _path_ok(p: str) -> bool:
    if p == "" or p.startswith("/") or "\\" in p or invisible(p.replace(" ", "_")) is not None:
        return False
    parts = p.split("/")
    return all(x not in ("", ".", "..") for x in parts) and all(31 < ord(c) != 127 for c in p)


def parse_manifest(data: bytes, h: str, steps: Steps | None = None) -> dict:
    """A manifest names a dataset: line 1 'reality-manifest 1', then one line per file,
    '<sha256>\\t<size>\\t<relative path>', sorted by path bytes, each path once, LF endings.
    Returns {path: (sha256, size)} in path order. Linear in its bytes but for one binary search per
    path (n log n comparisons), charged to steps (a fresh meter if none) before the work (fix pass R6)."""
    what = f"manifest sha256:{h}"
    steps = steps or Steps()
    steps.add(len(data) + 1)   # each path is checked character by character (_path_ok)
    if b"\r" in data:
        raise Refusal("M001", "2", f"{what} contains a carriage return")
    text = decode_utf8(data, what)
    lines = text.split("\n")
    if not lines or lines[0] != MANIFEST_MAGIC or lines[-1] != "":
        raise Refusal("M001", "1", f"{what} is not a Reality manifest (first line '{MANIFEST_MAGIC}', every line ends with LF)")
    lines = lines[1:-1]
    if len(lines) > MAX_MANIFEST_ENTRIES:
        raise Refusal("R003", "bounds", f"{what} lists more than {MAX_MANIFEST_ENTRIES} files (Reality bounds)")
    out, prev = {}, None
    for i, ln in enumerate(lines, start=2):
        parts = ln.split("\t")
        if len(parts) != 3 or len(parts[0]) != 64 or not set(parts[0]) <= set("0123456789abcdef") \
                or not parts[1].isascii() or not parts[1].isdigit() or len(parts[1]) > 20 \
                or (parts[1] != "0" and parts[1].startswith("0")) or not _path_ok(parts[2]):
            raise Refusal("M001", "1", f"{what} line {i} is not '<sha256>\\t<size>\\t<relative path>'")
        pb = parts[2].encode("utf-8")
        if prev is not None and pb <= prev:
            raise Refusal("M002", "2", f"{what} line {i}: paths must be strictly increasing by bytes (each path once)")
        prev = pb
        out[parts[2]] = (parts[0], int(parts[1]))
    # a path is also a folder if some path starts with it and "/": in byte order those paths follow
    # path + "/" directly, so one binary search per path finds them (all prefixes would be quadratic)
    keys = [p.encode("utf-8") for p in out]
    steps.add((len(data) // 64 + 1) * (len(keys).bit_length() + 1))   # each search compares at most every path's bytes once per level
    for pb in keys:
        i = bisect.bisect_left(keys, pb + b"/")
        if i < len(keys) and keys[i].startswith(pb + b"/"):
            raise Refusal("M002", "2", f"{what}: {pb.decode('utf-8')!r} is both a file and a folder")
    return out


class ManifestError(Exception):
    """The manifest writer cannot name this folder (v4 SPEC 10): exit 2, nothing written."""


def make_manifest(root) -> bytes:
    """Write the manifest of every regular file under `root` (symlinks are not followed). Paths
    are walked as bytes; a name that is not strict UTF-8 or that the manifest reader would refuse
    raises ManifestError instead of writing a manifest the checker refuses."""
    rootb = os.fsencode(root)
    if not os.path.isdir(rootb):
        raise ManifestError(f"{os.fsdecode(rootb)!r} is not a folder")
    entries = []

    def stop(e):   # (A10, Argon review 10) an unreadable folder or file: no manifest (exit 2), never a partial one or a traceback
        raise ManifestError(f"cannot read {os.fsdecode(e.filename or rootb)!r} ({e.strerror or type(e).__name__}), so no manifest can name every file under the folder") from None
    for dp, dns, fns in os.walk(rootb, onerror=stop):
        dns[:] = sorted(d for d in dns if not linked(os.path.join(dp, d)))   # a linked folder is not walked
        for fn in fns:
            full = os.path.join(dp, fn)
            if linked(full) or not os.path.isfile(full):
                continue
            relb = os.path.relpath(full, rootb).replace(os.sep.encode(), b"/")
            try:
                rel = relb.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise ManifestError(f"the file name {relb!r} is not UTF-8, so a manifest cannot name it") from None
            if not _path_ok(rel):
                raise ManifestError(f"the file name {relb!r} holds a character a manifest path cannot hold (SPEC 9.3, M001)")
            try:
                h, size = sha256_file(full)
            except OSError as e:
                stop(e)
            entries.append((relb, f"{h}\t{size}\t{rel}"))
    entries.sort()
    return (MANIFEST_MAGIC + "\n" + "".join(e + "\n" for _, e in entries)).encode("utf-8")

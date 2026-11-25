#!/usr/bin/env python3
"""Reality, steps one to five: two closed question forms, checked against bytes we are given, and
signed foundations that tables rest on; every output line is one statement in a closed, listed form.
This file verifies signatures; it never makes one. It writes no sentence and echoes no input text.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

NAMESPACE = "reality-adopt-1"  # ssh-keygen namespace: a signature made for another purpose is not an adoption
FOUNDATION_NAMESPACE = "reality-foundation-1"  # adopting a foundation, or tagging a table with one
UNDERMINE_NAMESPACE = "reality-undermine-1"  # knocking down one side of a comparison that does not hold
CODES = {
    "HOLDS": 0, "DOES-NOT-HOLD": 1, "NOT-CHECKED": 2, "REFUSED": 3, "NOT-RUN": 4,
    "NOT-RECORDED": 5, "LEDGER-UNREADABLE": 6, "FAILED": 7, "PROPOSED": 8, "ADOPTED": 9,
    "NOT-DELIVERED": 10, "UNDERMINED": 11, "HOLDS-UNDERMINED": 12, "IMPACT": 13,
}
KINDS = tuple(CODES) + ("DEPENDS",)  # DEPENDS lines only follow an IMPACT line
RULES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10")  # names only; accounts are in the README
CONDITIONS = (
    "not-reality-1", "not-five-lines", "no-such-question",
    "not-a-table-line", "not-a-predicate-line", "not-a-bar-line", "bar-above-whole", "same-table",
    "not-proposed", "not-verified", "no-adoption", "proposal-only", "adoption-not-verified",
    "signed-other-measure",
    "usage", "file-count", "measure-file-unreadable", "signature-file-unreadable",
    "log-not-written", "ssh-keygen-not-run",
    "log-unreadable", "log-line-not-json", "log-line-not-a-record", "adopters-unreadable",
    "unexpected",
    "bad-line-count", "not-a-foundation-line", "not-a-rests-on-line", "rests-on-not-ascending",
    "not-a-tag-line", "not-a-table-line-of-tag", "parent-not-adopted", "foundation-not-adopted",
    "not-an-undermine-line", "not-a-witness-line", "other-witness", "not-a-comparison",
    "witness-not-presented", "witness-holds", "not-a-side", "both-sides",
    "foundation-file-unreadable", "tag-file-unreadable", "undermine-file-unreadable", "bad-hash",
)
FILE_TOKENS = (
    "presented", "unreadable", "other-bytes",
    "passes", "no-final-newline", "repeated-column", "ragged-row", "no-rows", "no-such-column",
    "no-match",
)
SLOTS = (
    "outcome", "rule", "condition", "line", "given", "named",
    "file-1", "file-2", "log-line", "foundation", "tag", "side", "measure", "signed-measure", "adoption-line",
    "matching-1", "rows-1", "matching-2", "rows-2",
    "undermine-line", "undermined", "undermined-foundation", "undermines", "foundations", "measures",
)
HASH = re.compile("[0-9a-f]{64}")
TOKEN = "[!-~]+"  # one run of printable ASCII bytes, no space
TABLE_LINE = ("F2", "table sha256 ([0-9a-f]{64})")
PREDICATE_LINE = ("F3", f"predicate column-equals ({TOKEN}) ({TOKEN})")
BAR_LINE = ("F4", "at-least ([1-9][0-9]{0,17}) of ([1-9][0-9]{0,17})")
FORMS = {  # line 2: (rule, pattern) for lines 3 to 5
    "question share-at-least": (TABLE_LINE, PREDICATE_LINE, BAR_LINE),
    "question share-agrees": (TABLE_LINE, TABLE_LINE, PREDICATE_LINE),
}


def state(**slots: object) -> str:
    """Write one statement. Accepts only the listed slots and values, in the listed order."""
    if "outcome" not in slots or set(slots) - set(SLOTS):
        raise ValueError(slots)
    parts = []
    for name in SLOTS:
        if name not in slots:
            continue
        value = slots[name]
        if name == "outcome" and value in KINDS:
            text = value
        elif name == "rule" and value in RULES:
            text = value
        elif name == "condition" and value in CONDITIONS:
            text = value
        elif name in ("file-1", "file-2") and value in FILE_TOKENS:
            text = value
        elif (name in ("measure", "signed-measure", "foundation", "tag", "undermined-foundation")
              and isinstance(value, str) and HASH.fullmatch(value)):
            text = value
        elif name == "undermined" and value in ("yes", "no"):
            text = value
        elif name == "side" and type(value) is int and value in (1, 2):
            text = str(value)
        elif name == "line" and type(value) is int and value in (1, 2, 3, 4, 5):
            text = str(value)
        elif name == "named" and type(value) is int and value in (1, 2):
            text = str(value)
        elif name in ("given", "log-line", "adoption-line", "matching-1", "rows-1", "matching-2", "rows-2",
                      "undermine-line", "undermines", "foundations", "measures"):
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                text = str(value)
            else:
                raise ValueError(name, value)
        else:
            raise ValueError(name, value)
        parts.append(f"{name}={text}")
    return " ".join(parts)


class Stop(Exception):
    """Base of every stop: str() is the statement; .slots holds the slot values."""

    def __init__(self, **slots: object):
        self.slots = slots
        self.statement = state(**slots)
        super().__init__(self.statement)

    def __str__(self) -> str:
        return self.statement


class Refusal(Stop):
    """A formation failure under a rule F1 to F10."""


class NotPresented(Stop):
    """A file given is not the bytes its table line names."""


class NotRun(Stop):
    """Usage, or a file the operating system did not give or take."""


class WrongFiles(NotRun):
    """The number of table files given is not the number of table lines in the measure."""


class Unreadable(Stop):
    """The log or the adopters file cannot be read as the program requires."""


class Measure(NamedTuple):
    text: str  # the exact measure bytes, as ASCII text; this is what an adopter signs
    question: str  # "share-at-least" or "share-agrees"
    tables: tuple[str, ...]  # the sha256 on each table line, in order
    column: bytes
    value: bytes
    bar: tuple[int, int] | None  # (N, D) for share-at-least; share-agrees has no bar


def _guard(fn):
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Stop:
            raise
        except KeyboardInterrupt:
            raise
        except BaseException as error:
            raise Stop(outcome="FAILED", condition="unexpected") from error
    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped


def _files(tokens: list[str]) -> dict[str, str]:
    return {f"file-{i}": token for i, token in enumerate(tokens, 1)}


@_guard
def form(raw: bytes) -> Measure:
    """Return the measure these bytes spell, or refuse. Prose is never interpreted."""
    text = raw.decode("ascii", "replace")
    lines = text.split("\n")
    if lines[0] != "reality 1":
        raise Refusal(outcome="REFUSED", rule="F1", condition="not-reality-1", line=1)
    if len(lines) != 6 or lines[5] != "":
        raise Refusal(outcome="REFUSED", rule="F1", condition="not-five-lines")
    if lines[1] not in FORMS:
        raise Refusal(outcome="REFUSED", rule="F1", condition="no-such-question", line=2)
    question, found = lines[1].removeprefix("question "), []
    refused = {"F2": "not-a-table-line", "F3": "not-a-predicate-line", "F4": "not-a-bar-line"}
    for number, ((rule, pattern), line) in enumerate(zip(FORMS[lines[1]], lines[2:]), 3):
        hit = re.fullmatch(pattern, line)
        if hit is None:
            raise Refusal(outcome="REFUSED", rule=rule, condition=refused[rule], line=number)
        found += hit.groups()
    if question == "share-agrees":
        first, second, column, value = found
        if first == second:
            raise Refusal(outcome="REFUSED", rule="F2", condition="same-table", line=4)
        return Measure(text, question, (first, second), column.encode(), value.encode(), None)
    table, column, value, n, d = found
    if int(n) > int(d):
        raise Refusal(outcome="REFUSED", rule="F4", condition="bar-above-whole", line=5)
    return Measure(text, question, (table,), column.encode(), value.encode(), (int(n), int(d)))


class Foundation(NamedTuple):
    text: str  # the exact foundation bytes; this is what a holder of a listed key signs
    parents: tuple[str, ...]  # ids of the foundations it rests on, ascending; it names them itself


class Tag(NamedTuple):
    text: str
    table: str  # the sha256 of a table
    foundation: str  # the id of the foundation the signer says that table rests on


class Undermine(NamedTuple):
    text: str
    foundation: str  # the side the signer knocks down
    witness: str  # the id of an adopted share-agrees measure


def _lines(raw: bytes, rule: str, low: int, high: int) -> list[str]:
    lines = raw.decode("ascii", "replace").split("\n")
    if lines[0] != "reality 1":
        raise Refusal(outcome="REFUSED", rule=rule, condition="not-reality-1", line=1)
    if not low + 1 <= len(lines) <= high + 1 or lines[-1] != "":
        raise Refusal(outcome="REFUSED", rule=rule, condition="bad-line-count")
    return lines[:-1]


def _hash_line(lines: list[str], at: int, prefix: str, rule: str, condition: str) -> str:
    hit = re.fullmatch(prefix + " sha256 ([0-9a-f]{64})", lines[at - 1])
    if hit is None:
        raise Refusal(outcome="REFUSED", rule=rule, condition=condition, line=at)
    return hit.group(1)


@_guard
def parse_foundation(raw: bytes) -> Foundation:
    """A name, then zero to three rests-on lines in ascending order, or refuse (F9)."""
    lines = _lines(raw, "F9", 2, 5)
    if re.fullmatch(f"foundation {TOKEN}", lines[1]) is None:
        raise Refusal(outcome="REFUSED", rule="F9", condition="not-a-foundation-line", line=2)
    parents = tuple(_hash_line(lines, at, "rests-on", "F9", "not-a-rests-on-line")
                    for at in range(3, len(lines) + 1))
    if list(parents) != sorted(set(parents)):
        raise Refusal(outcome="REFUSED", rule="F9", condition="rests-on-not-ascending")
    return Foundation("\n".join(lines) + "\n", parents)


@_guard
def parse_tag(raw: bytes) -> Tag:
    lines = _lines(raw, "F9", 4, 4)
    if lines[1] != "tag":
        raise Refusal(outcome="REFUSED", rule="F9", condition="not-a-tag-line", line=2)
    table = _hash_line(lines, 3, "table", "F9", "not-a-table-line-of-tag")
    return Tag("\n".join(lines) + "\n", table, _hash_line(lines, 4, "rests-on", "F9", "not-a-rests-on-line"))


@_guard
def parse_undermine(raw: bytes) -> Undermine:
    lines = _lines(raw, "F10", 4, 4)
    if lines[1] != "undermine":
        raise Refusal(outcome="REFUSED", rule="F10", condition="not-an-undermine-line", line=2)
    foundation = _hash_line(lines, 3, "foundation", "F10", "not-an-undermine-line")
    return Undermine("\n".join(lines) + "\n", foundation,
                     _hash_line(lines, 4, "witness", "F10", "not-a-witness-line"))


@_guard
def ask(m: Measure, files: tuple[Path, ...]) -> list[tuple[int, list[list[bytes]]]]:
    """Take the files, in order, as the named bytes, then apply rule F8 to each of them."""
    mid = ident(m.text)
    if len(files) != len(m.tables):
        raise WrongFiles(outcome="NOT-RUN", condition="file-count", given=len(files),
                         named=len(m.tables), measure=mid)
    held, tokens = [], []
    for named, file in zip(m.tables, files):
        try:
            data = file.read_bytes()
        except OSError:
            tokens.append("unreadable")
            continue
        if hashlib.sha256(data).hexdigest() != named:
            tokens.append("other-bytes")
        else:
            tokens.append("presented")
            held.append(data)
    if any(token != "presented" for token in tokens):
        raise NotPresented(outcome="NOT-RECORDED", measure=mid, **_files(tokens))
    asked, status = [], []
    for data in held:
        header, *body = [line.split(b"\t") for line in data[:-1].split(b"\n")]
        if not data.endswith(b"\n"):
            token = "no-final-newline"
        elif len(set(header)) != len(header):
            token = "repeated-column"
        elif any(len(row) != len(header) for row in body):
            token = "ragged-row"
        elif not body:
            token = "no-rows"
        elif m.column not in header:
            token = "no-such-column"
        else:
            token = "passes"
            asked.append((header.index(m.column), body))
        status.append(token)
    if any(token != "passes" for token in status):
        raise Refusal(outcome="REFUSED", rule="F8", measure=mid, **_files(status))
    if m.question == "share-agrees" and not any(m.value in (row[at] for row in body) for at, body in asked):
        raise Refusal(outcome="REFUSED", rule="F8", measure=mid, **_files(["no-match"] * len(asked)))
    return asked


def ident(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def entries(ledger: Path) -> list[dict]:
    return [entry for _, entry in _records(ledger)]


def _records(ledger: Path) -> list[tuple[int, dict]]:
    if ledger.exists() and not ledger.is_dir():
        raise Unreadable(outcome="LEDGER-UNREADABLE", condition="log-unreadable")
    try:
        text = (ledger / "log").read_bytes().decode()
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError):
        raise Unreadable(outcome="LEDGER-UNREADABLE", condition="log-unreadable")
    found = []
    for number, line in enumerate(text.removesuffix("\n").split("\n") if text else [], 1):  # newline bytes only
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            raise Unreadable(outcome="LEDGER-UNREADABLE", condition="log-line-not-json",
                             **{"log-line": number})
        except (ValueError, RecursionError):  # JSON, but more digits or depth than the reader takes
            entry = None
        if not isinstance(entry, dict) or not isinstance(entry.get("kind"), str):
            raise Unreadable(outcome="LEDGER-UNREADABLE", condition="log-line-not-a-record",
                             **{"log-line": number})
        kind = entry["kind"]
        if kind == "proposal" and not isinstance(entry.get("measure"), str):
            raise Unreadable(outcome="LEDGER-UNREADABLE", condition="log-line-not-a-record",
                             **{"log-line": number})
        if kind == "adoption" and not all(isinstance(entry.get(key), str)
                                          for key in ("measure", "adopter", "signature")):
            raise Unreadable(outcome="LEDGER-UNREADABLE", condition="log-line-not-a-record",
                             **{"log-line": number})
        if kind in SIGNED_KINDS and not all(isinstance(entry.get(key), str) for key in SIGNED_KINDS[kind]):
            raise Unreadable(outcome="LEDGER-UNREADABLE", condition="log-line-not-a-record",
                             **{"log-line": number})
        found.append((number, entry))
    return found


SIGNED_KINDS = {  # kind: the string fields its log line must have (adoption is checked above)
    "foundation-adoption": ("foundation", "adopter", "signature"),
    "tag": ("tag", "adopter", "signature"),
    "undermine": ("undermine", "witness", "adopter", "signature"),
}


def record(ledger: Path, **entry: str) -> int:
    path = ledger / "log"
    try:
        data = path.read_bytes() if path.exists() else b""
        if data and not data.endswith(b"\n"):  # a new line would join the last one
            raise NotRun(outcome="NOT-RUN", condition="log-not-written")
        with open(path, "a", encoding="utf-8", newline="\n") as log:
            log.write(json.dumps(entry) + "\n")
    except OSError:
        raise NotRun(outcome="NOT-RUN", condition="log-not-written")
    return data.count(b"\n") + 1


def _adopters(ledger: Path) -> None:
    try:
        (ledger / "adopters").read_bytes()
    except OSError:
        raise Unreadable(outcome="LEDGER-UNREADABLE", condition="adopters-unreadable")


def signed(ledger: Path, adopter: str, text: str, signature: str, namespace: str = NAMESPACE) -> bool:
    """True only if ssh-keygen verifies the signature over the text with a key listed under adopter."""
    if not re.fullmatch("[A-Za-z0-9._@-]+", adopter):
        return False
    with tempfile.TemporaryDirectory() as tmp:
        sigfile = Path(tmp, "sig")
        sigfile.write_bytes(signature.replace("\r\n", "\n").encode("ascii", "replace"))
        try:
            done = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(ledger / "adopters"), "-I", adopter,
                 "-n", namespace, "-s", str(sigfile)],
                input=text.encode(), capture_output=True,
            )
        except OSError:
            raise NotRun(outcome="NOT-RUN", condition="ssh-keygen-not-run")
        return done.returncode == 0


def _formed(text: str) -> bool:
    """True only if a proposal line's text is a well-formed measure: F7 names no other text."""
    try:
        return form(text.encode()) is not None
    except (Stop, UnicodeError):
        return False


@_guard
def propose(ledger: Path, raw: bytes, *tables: Path) -> str:
    """Record a measure as proposed if it is well-formed and can be asked of its named bytes."""
    m = form(raw)
    ask(m, tables)
    if not any(e["kind"] == "proposal" and e["measure"] == m.text for e in entries(ledger)):
        record(ledger, kind="proposal", measure=m.text)
    return state(outcome="PROPOSED", measure=ident(m.text))


@_guard
def adopt(ledger: Path, raw: bytes, adopter: str, signature: str, *tables: Path) -> str:
    """Record an adoption only if the question can be asked of its named bytes and the signature verifies."""
    m = form(raw)
    ask(m, tables)
    mid = ident(m.text)
    proposed = [e["measure"] for e in entries(ledger) if e["kind"] == "proposal"]
    if m.text not in proposed:
        raise Refusal(outcome="REFUSED", rule="F5", condition="not-proposed", measure=mid)
    _adopters(ledger)
    if not signed(ledger, adopter, m.text, signature):
        for other in proposed:
            if other != m.text and _formed(other) and signed(ledger, adopter, other, signature):
                raise Refusal(outcome="REFUSED", rule="F7", condition="signed-other-measure",
                              measure=mid, **{"signed-measure": ident(other)})
        raise Refusal(outcome="REFUSED", rule="F5", condition="not-verified", measure=mid)
    line = record(ledger, kind="adoption", measure=m.text, adopter=adopter, signature=signature)
    return state(outcome="ADOPTED", measure=mid, **{"adoption-line": line})


@_guard
def check(ledger: Path, raw: bytes, *tables: Path) -> str:
    """Check an adopted measure against the files given. A check line is recorded only for a count."""
    return _check(ledger, raw, *tables)[0]


def _verdict(ledger: Path, m: Measure, tables: tuple[Path, ...]):
    """(kind, numbers) or None, the file tokens if the named bytes were not given, the adoption line, the log."""
    mid = ident(m.text)
    try:
        asked = ask(m, tables)
        tokens = None
    except NotPresented as absent:
        tokens = {key: absent.slots[key] for key in absent.slots if key.startswith("file-")}
    log = _records(ledger)
    adoptions = [(n, e) for n, e in log if e["kind"] == "adoption" and e["measure"] == m.text]
    if not adoptions:
        proposed = any(e["kind"] == "proposal" and e["measure"] == m.text for _, e in log)
        condition = "proposal-only" if proposed else "no-adoption"
        raise Refusal(outcome="REFUSED", rule="F6", condition=condition, measure=mid)
    _adopters(ledger)
    adoption = next(((n, e) for n, e in adoptions if signed(ledger, e["adopter"], m.text, e["signature"])),
                    None)
    if adoption is None:
        raise Refusal(outcome="REFUSED", rule="F6", condition="adoption-not-verified", measure=mid)
    line = adoption[0]
    if tokens is not None:
        return None, tokens, line, log
    counts = [(sum(row[at] == m.value for row in body), len(body)) for at, body in asked]
    if m.question == "share-at-least":
        (matching, total), (n, d) = counts[0], m.bar
        kind = "HOLDS" if matching * d >= n * total else "DOES-NOT-HOLD"
        numbers = {"matching-1": matching, "rows-1": total}
    else:
        (a, b), (c, e) = counts
        kind = "HOLDS" if a * e == c * b else "DOES-NOT-HOLD"
        numbers = {"matching-1": a, "rows-1": b, "matching-2": c, "rows-2": e}
    return (kind, numbers), None, line, log


@_guard
def _check(ledger: Path, raw: bytes, *tables: Path) -> tuple[str, str | None]:
    """The statement, and the statement to stand for it if a recorded check is not delivered."""
    m = form(raw)
    mid = ident(m.text)
    result, tokens, line, log = _verdict(ledger, m, tables)
    if result is None:
        return state(outcome="NOT-CHECKED", measure=mid, **{"adoption-line": line}, **tokens), None
    kind, numbers = result
    graph = _graph(ledger, log)
    fallen = [f for f in graph.undermined if f in graph.under(m.tables)]
    if fallen:  # the count stands; the outcome says a foundation under the named bytes was knocked down
        kind = "HOLDS-UNDERMINED" if kind == "HOLDS" else kind
        numbers = {**numbers, "undermined-foundation": fallen[0], "undermines": len(fallen)}
    statement = state(outcome=kind, measure=mid, **{"adoption-line": line}, **numbers)
    at = record(ledger, kind="check", outcome=statement)
    return statement, state(outcome="NOT-DELIVERED", measure=mid, **{"log-line": at})


class Graph(NamedTuple):
    """What the log says, counting only lines whose signatures verify now, read in log order."""
    parents: dict[str, tuple[str, ...]]  # adopted foundation id -> the ids it rests on
    tags: dict[str, list[str]]  # table sha256 -> foundation ids a signed tag says it rests on
    undermined: dict[str, int]  # foundation id -> line of its first accepted undermine

    def above(self, start: set[str]) -> set[str]:
        """The foundations given, and every foundation they rest on, however far down."""
        found, todo = set(), list(start)
        while todo:
            fid = todo.pop()
            if fid not in found:
                found.add(fid)
                todo.extend(self.parents.get(fid, ()))
        return found

    def under(self, tables: tuple[str, ...]) -> set[str]:
        return self.above({fid for table in tables for fid in self.tags.get(table, [])})


def _adopted(ledger: Path, log, text: str) -> bool:
    return any(e["kind"] == "adoption" and e["measure"] == text and signed(ledger, e["adopter"], text, e["signature"])
               for _, e in log)


def _graph(ledger: Path, log) -> Graph:
    """A foundation counts only if its parents counted on an earlier line, so the graph has no cycle."""
    graph = Graph({}, {}, {})
    if any(e["kind"] in SIGNED_KINDS for _, e in log):
        _adopters(ledger)
    for idx, (number, e) in enumerate(log):
        try:
            if e["kind"] == "foundation-adoption":
                f = parse_foundation(e["foundation"].encode())
                if (f.text == e["foundation"] and all(p in graph.parents for p in f.parents)
                        and signed(ledger, e["adopter"], f.text, e["signature"], FOUNDATION_NAMESPACE)):
                    graph.parents.setdefault(ident(f.text), f.parents)
            elif e["kind"] == "tag":
                t = parse_tag(e["tag"].encode())
                if (t.text == e["tag"] and t.foundation in graph.parents
                        and signed(ledger, e["adopter"], t.text, e["signature"], FOUNDATION_NAMESPACE)):
                    if t.foundation not in graph.tags.setdefault(t.table, []):
                        graph.tags[t.table].append(t.foundation)
            elif e["kind"] == "undermine":
                u, w = parse_undermine(e["undermine"].encode()), form(e["witness"].encode())
                sides = [u.foundation in graph.tags.get(table, []) for table in w.tables]
                if (u.text == e["undermine"] and ident(w.text) == u.witness and w.question == "share-agrees"
                        and u.foundation in graph.parents and sides.count(True) == 1
                        and _adopted(ledger, log[:idx], w.text)
                        and signed(ledger, e["adopter"], u.text, e["signature"], UNDERMINE_NAMESPACE)):
                    graph.undermined.setdefault(u.foundation, number)
        except (Stop, UnicodeError):
            continue  # a line that does not parse or verify counts for nothing
    return graph


@_guard
def adopt_foundation(ledger: Path, raw: bytes, adopter: str, signature: str) -> str:
    """Record a foundation, signed by a listed key, only if every foundation it rests on is already adopted."""
    f = parse_foundation(raw)
    fid = ident(f.text)
    graph = _graph(ledger, _records(ledger))
    for at, parent in enumerate(f.parents, 3):
        if parent not in graph.parents:
            raise Refusal(outcome="REFUSED", rule="F9", condition="parent-not-adopted", foundation=fid, line=at)
    _adopters(ledger)
    if not signed(ledger, adopter, f.text, signature, FOUNDATION_NAMESPACE):
        raise Refusal(outcome="REFUSED", rule="F5", condition="not-verified", foundation=fid)
    line = record(ledger, kind="foundation-adoption", foundation=f.text, adopter=adopter, signature=signature)
    return state(outcome="ADOPTED", foundation=fid, **{"adoption-line": line})


@_guard
def tag(ledger: Path, raw: bytes, adopter: str, signature: str) -> str:
    """Record a signed claim that a table rests on an adopted foundation. Whether it is true is not checked."""
    t = parse_tag(raw)
    if t.foundation not in _graph(ledger, _records(ledger)).parents:
        raise Refusal(outcome="REFUSED", rule="F9", condition="foundation-not-adopted", foundation=t.foundation,
                      line=4)
    _adopters(ledger)
    if not signed(ledger, adopter, t.text, signature, FOUNDATION_NAMESPACE):
        raise Refusal(outcome="REFUSED", rule="F5", condition="not-verified", tag=ident(t.text))
    line = record(ledger, kind="tag", tag=t.text, adopter=adopter, signature=signature)
    return state(outcome="ADOPTED", foundation=t.foundation, tag=ident(t.text), **{"adoption-line": line})


@_guard
def undermine(ledger: Path, raw: bytes, adopter: str, signature: str, witness: bytes, *tables: Path) -> str:
    """Knock down one side of an adopted share-agrees measure, recounted now on its named bytes."""
    u = parse_undermine(raw)
    w = form(witness)
    if ident(w.text) != u.witness:
        raise Refusal(outcome="REFUSED", rule="F10", condition="other-witness", foundation=u.foundation)
    if w.question != "share-agrees":
        raise Refusal(outcome="REFUSED", rule="F10", condition="not-a-comparison", measure=u.witness)
    graph = _graph(ledger, _records(ledger))
    if u.foundation not in graph.parents:
        raise Refusal(outcome="REFUSED", rule="F9", condition="foundation-not-adopted", foundation=u.foundation)
    result, tokens, _, _ = _verdict(ledger, w, tables)
    if result is None:
        raise Refusal(outcome="REFUSED", rule="F10", condition="witness-not-presented", measure=u.witness, **tokens)
    kind, numbers = result
    if kind != "DOES-NOT-HOLD":
        raise Refusal(outcome="REFUSED", rule="F10", condition="witness-holds", measure=u.witness, **numbers)
    sides = [u.foundation in graph.tags.get(table, []) for table in w.tables]
    if sides.count(True) != 1:
        raise Refusal(outcome="REFUSED", rule="F10", condition="both-sides" if all(sides) else "not-a-side",
                      foundation=u.foundation, measure=u.witness)
    _adopters(ledger)
    if not signed(ledger, adopter, u.text, signature, UNDERMINE_NAMESPACE):
        raise Refusal(outcome="REFUSED", rule="F5", condition="not-verified", foundation=u.foundation)
    line = record(ledger, kind="undermine", undermine=u.text, witness=w.text, adopter=adopter, signature=signature)
    return state(outcome="UNDERMINED", foundation=u.foundation, side=sides.index(True) + 1, measure=u.witness,
                 **numbers, **{"undermine-line": line})


@_guard
def impact(ledger: Path, fid: str) -> str:
    """Every adopted foundation and adopted measure that rests on fid, however far down."""
    if not HASH.fullmatch(fid):
        raise NotRun(outcome="NOT-RUN", condition="bad-hash")
    log = _records(ledger)
    graph = _graph(ledger, log)
    if fid not in graph.parents:
        raise Refusal(outcome="REFUSED", rule="F9", condition="foundation-not-adopted", foundation=fid)
    above = [f for f in graph.parents if f != fid and fid in graph.above({f})]
    measures = []
    for _, e in log:
        if e["kind"] == "adoption" and ident(e["measure"]) not in measures and _formed(e["measure"]):
            m = form(e["measure"].encode())
            if fid in graph.under(m.tables) and signed(ledger, e["adopter"], m.text, e["signature"]):
                measures.append(ident(m.text))
    lines = [state(outcome="IMPACT", foundation=fid, undermined="yes" if fid in graph.undermined else "no",
                   foundations=len(above), measures=len(measures))]
    lines += [state(outcome="DEPENDS", foundation=f) for f in above]
    lines += [state(outcome="DEPENDS", measure=m) for m in measures]
    return "\n".join(lines)


def _read(path: Path, condition: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise NotRun(outcome="NOT-RUN", condition=condition)


def _signature(sigfile: str) -> str:
    try:
        return Path(sigfile).read_text(encoding="ascii", errors="replace")
    except OSError:
        raise NotRun(outcome="NOT-RUN", condition="signature-file-unreadable")


def _run(argv: list[str]) -> tuple[str, str | None]:
    match argv:
        case ["propose", ledger, measure, *tables] if len(tables) in (1, 2):
            return propose(Path(ledger), _read(Path(measure), "measure-file-unreadable"),
                           *map(Path, tables)), None
        case ["adopt", ledger, measure, sigfile, adopter, *tables] if len(tables) in (1, 2):
            return adopt(Path(ledger), _read(Path(measure), "measure-file-unreadable"),
                         adopter, _signature(sigfile), *map(Path, tables)), None
        case ["check", ledger, measure, *tables] if len(tables) in (1, 2):
            return _check(Path(ledger), _read(Path(measure), "measure-file-unreadable"),
                          *map(Path, tables))
        case ["adopt-foundation", ledger, found, sigfile, adopter]:
            return adopt_foundation(Path(ledger), _read(Path(found), "foundation-file-unreadable"), adopter,
                                    _signature(sigfile)), None
        case ["tag", ledger, claim, sigfile, adopter]:
            return tag(Path(ledger), _read(Path(claim), "tag-file-unreadable"), adopter, _signature(sigfile)), None
        case ["undermine", ledger, knock, sigfile, adopter, witness, first, second]:
            return undermine(Path(ledger), _read(Path(knock), "undermine-file-unreadable"), adopter,
                             _signature(sigfile), _read(Path(witness), "measure-file-unreadable"),
                             Path(first), Path(second)), None
        case ["impact", ledger, fid]:
            return impact(Path(ledger), fid), None
        case _:
            return state(outcome="NOT-RUN", condition="usage"), None


def main(argv: list[str]) -> int:
    try:
        undelivered = None
        try:
            statement, undelivered = _run(argv)
        except Stop as stop:
            statement = str(stop)
        except BaseException:
            statement = state(outcome="FAILED", condition="unexpected")
        try:
            sys.stdout.write(statement + "\n")
            sys.stdout.flush()
        except BaseException:
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)  # so Python writes nothing more at exit
            if undelivered is None:
                return 7
            statement = undelivered  # a check line was recorded; its statement is not printed
        return CODES[statement.split()[0].removeprefix("outcome=")]
    except BaseException:
        return 7


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

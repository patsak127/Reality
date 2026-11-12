"""Reality v4 syntax: statements are one line, except `question` which takes indented clauses.

    file NAME = sha256:HEX64
    dataset NAME = sha256:HEX64        (the hash of a Reality manifest, see readers.py)
    let NAME = EXPR
    claim EXPR
    claim EXPR is LITERAL
    question FORM NAME                 (stipulated-model question; indented clauses follow)
      ...clauses...                    (see SPEC-ORD / questions.py; not an expression)

    EXPR    ::= NAME | INT | DECIMAL | STRING | CALL
    CALL    ::= IDENT "(" [ARG {"," ARG}] ")"
    ARG     ::= EXPR | IDENT "=" PVALUE                 (a parameter: slot = value)
    PVALUE  ::= ["-"] DECIMAL [UNIT] | INT "/" INT | IDENT  (a number, a ratio, a closed-list member)
    LITERAL ::= ["-"] DECIMAL [UNIT] | INT "/" INT | STRING
    STRING  ::= '"' {printable ASCII except '"' and '\\' | '\\"' | '\\\\' | '\\x' HEX HEX} '"'

A question is a *statement*, never an expression: it cannot appear in `let`, `claim`, or a Call
argument. Its answer is not a Meaning (questions.QuestionAnswer).

Comments run from '#' to the end of the line. Names carry no meaning (principle section 1,
Names): they are resolved to what they stand for before anything is printed.

Bounds are renaming-invariant (principle item 3): a name is 1 to 64 characters, and the program's
size is measured with every name counted as one byte (MAX_PROGRAM_SIZE). A program longer than
64 x MAX_PROGRAM_SIZE bytes has a measured size above the bound, so it is refused before it is
read further. Every number written has at most MAX_DIGITS digits; a ratio is a whole number at
least 0 over a whole number at least 1."""
import re
from dataclasses import dataclass
from fractions import Fraction

MAX_PROGRAM_SIZE = 1_000_000     # bytes, with every name counted as one byte
MAX_NAME = 64
MAX_LINE_TOKENS = 10_000
MAX_DEPTH = 64
MAX_DIGITS = 1000
MAX_STRING = 4096

KEYWORDS = frozenset({"file", "dataset", "let", "claim", "is", "question"})


class SyntaxRefusal(Exception):
    def __init__(self, code: str, line: int, msg: str):
        super().__init__(msg)
        self.code, self.line, self.msg = code, line, msg


@dataclass(frozen=True)
class Name:
    id: str


@dataclass(frozen=True)
class Int:
    v: int


@dataclass(frozen=True)
class Dec:
    v: Fraction
    text: str


@dataclass(frozen=True)
class Str:
    v: bytes  # the bytes the literal stands for; compared byte for byte, never decoded


@dataclass(frozen=True)
class Ratio:
    n: int
    d: int


@dataclass(frozen=True)
class Param:
    slot: str
    value: object  # Int | Dec | Ratio | Name (closed-list member)
    unit: str | None = None


@dataclass(frozen=True)
class Call:
    fn: str
    args: tuple
    params: tuple  # tuple[Param, ...] in written order


@dataclass(frozen=True)
class Stmt:
    kind: str  # file | dataset | let | claim | question
    line: int
    name: str | None = None
    hash: str | None = None
    expr: object = None
    lit: object = None  # for 'claim ... is LIT': ('num', Fraction, unit|None) | ('ratio', n, d) | ('str', s)
    qform: str | None = None  # question form ident (e.g. weighted_pair_orderings)
    qbody: tuple = ()  # indented clause lines (raw text), question only


_HEX = frozenset("0123456789abcdef")
_IDSTART = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_IDCHAR = _IDSTART | frozenset("0123456789")
_DIGIT = frozenset("0123456789")


def _tokens(text: str, ln: int):
    toks, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t":
            i += 1
        elif c == "#":
            break
        elif c in "(),=/":
            toks.append(("p", c))
            i += 1
        elif c == '"':
            j, out = i + 1, []
            while True:
                if j >= n:
                    raise SyntaxRefusal("P002", ln, "a string is not closed on its line")
                d = text[j]
                if d == '"':
                    break
                if d == "\\":
                    e = text[j + 1:j + 2]
                    if e in ('"', "\\"):
                        out.append(ord(e))
                        j += 2
                    elif e == "x" and len(text) >= j + 4 and all(h in _HEX for h in text[j + 2:j + 4]):
                        out.append(int(text[j + 2:j + 4], 16))
                        j += 4
                    else:
                        raise SyntaxRefusal("P002", ln, 'a string escape must be \\" or \\\\ or \\x followed by two lowercase hex digits')
                else:
                    out.append(ord(d))
                    j += 1
            if len(out) > MAX_STRING:
                raise SyntaxRefusal("R001", ln, f"a string longer than {MAX_STRING} bytes (Reality bounds)")
            toks.append(("s", bytes(out)))
            i = j + 1
        elif c in _DIGIT or (c == "-" and i + 1 < n and text[i + 1] in _DIGIT):
            j = i + 1
            while j < n and text[j] in _DIGIT:
                j += 1
            if j < n and text[j] == "." and j + 1 < n and text[j + 1] in _DIGIT:
                j += 1
                while j < n and text[j] in _DIGIT:
                    j += 1
                toks.append(("d", text[i:j]))
            else:
                toks.append(("i", text[i:j]))
            if sum(ch in _DIGIT for ch in text[i:j]) > MAX_DIGITS:
                raise SyntaxRefusal("R010", ln, f"a number in the program with more than {MAX_DIGITS} digits (Reality bounds)")
            i = j
            if i < n and text[i] in _IDCHAR:
                raise SyntaxRefusal("P001", ln, f"a number runs into a name: {text[i - 1:i + 1]!r}")
        elif c in _IDSTART:
            j = i + 1
            while j < n and text[j] in _IDCHAR:
                j += 1
            word = text[i:j]
            if len(word) > MAX_NAME:
                raise SyntaxRefusal("P010", ln, f"a name or word is at most {MAX_NAME} characters")
            if word == "sha256" and text[j:j + 1] == ":":
                h = text[j + 1:j + 65]
                if len(h) != 64 or not all(x in _HEX for x in h) or (j + 65 < n and text[j + 65] in _IDCHAR):
                    raise SyntaxRefusal("P003", ln, "a hash is written sha256: followed by exactly 64 lowercase hex digits")
                toks.append(("h", h))
                i = j + 65
            elif text[j:j + 1] == ":":
                raise SyntaxRefusal("P003", ln, f"'{word}:' is not read by Reality; a file is named only by the SHA-256 of its bytes (sha256:...)")
            else:
                toks.append(("w", word))
                i = j
        else:
            raise SyntaxRefusal("P001", ln, f"unexpected character {c!r}")
        if len(toks) > MAX_LINE_TOKENS:
            raise SyntaxRefusal("R001", ln, f"a line has more than {MAX_LINE_TOKENS} tokens (Reality bounds)")
    return toks


class _P:
    def __init__(self, toks, ln):
        self.t, self.i, self.ln = toks, 0, ln

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else (None, None)

    def take(self, kind=None, val=None, what="something"):
        tk = self.peek()
        if tk[0] is None or (kind and tk[0] != kind) or (val is not None and tk[1] != val):
            got = "the end of the line" if tk[0] is None else repr(tk[1])
            raise SyntaxRefusal("P001", self.ln, f"expected {what}, found {got}")
        self.i += 1
        return tk

    def name(self, what="a name"):
        _, w = self.take("w", what=what)
        if w in KEYWORDS:
            raise SyntaxRefusal("P004", self.ln, f"{w!r} is a keyword, not a name")
        return w

    def expr(self, depth=0):
        if depth > MAX_DEPTH:
            raise SyntaxRefusal("R001", self.ln, f"expressions nest deeper than {MAX_DEPTH} (Reality bounds)")
        k, v = self.peek()
        if k == "i":
            self.i += 1
            return Int(int(v))
        if k == "d":
            self.i += 1
            return Dec(Fraction(v), v)
        if k == "s":
            self.i += 1
            return Str(v)
        if k == "h":
            raise SyntaxRefusal("P005", self.ln, "a hash can only be bound by 'file' or 'dataset', not written inside an expression")
        if k == "w":
            if v in KEYWORDS:
                raise SyntaxRefusal("P004", self.ln, f"{v!r} is a keyword, not a name")
            self.i += 1
            if self.peek() == ("p", "("):
                self.i += 1
                args, params = [], []
                if self.peek() != ("p", ")"):
                    while True:
                        if self.peek()[0] == "w" and self.peek(1) == ("p", "="):
                            slot = self.take("w")[1]
                            self.i += 1
                            pk, pv = self.peek()
                            unit = None
                            if pk == "i" and self.peek(1) == ("p", "/"):
                                self.i += 2
                                _, d = self.take("i", what="a whole denominator")
                                if pv.startswith("-") or d.startswith("-") or int(d) == 0:
                                    raise SyntaxRefusal("P007", self.ln, "a ratio is a whole number at least 0 over a whole number at least 1")
                                val = Ratio(int(pv), int(d))
                                self.i -= 1
                            elif pk == "i":
                                val = Int(int(pv))
                            elif pk == "d":
                                val = Dec(Fraction(pv), pv)
                            elif pk == "w" and pv not in KEYWORDS:
                                val = Name(pv)
                            else:
                                raise SyntaxRefusal("P006", self.ln, f"parameter {slot!r}: a parameter value is a number or a member of a closed list, never text, a file or an expression")
                            self.i += 1
                            if pk in ("i", "d") and self.peek()[0] == "w" and self.peek()[1] not in KEYWORDS:
                                unit = self.take("w")[1]
                            if self.peek() == ("p", "("):
                                raise SyntaxRefusal("P006", self.ln, f"parameter {slot!r}: a parameter value is a number or a member of a closed list, never text, a file or an expression")
                            params.append(Param(slot, val, unit))
                        else:
                            if params:
                                raise SyntaxRefusal("P001", self.ln, "parameters (slot = value) come after all other arguments")
                            args.append(self.expr(depth + 1))
                        if self.peek() == ("p", ","):
                            self.i += 1
                            continue
                        break
                self.take("p", ")", what="')' or ','")
                return Call(v, tuple(args), tuple(params))
            return Name(v)
        got = "the end of the line" if k is None else repr(v)
        raise SyntaxRefusal("P001", self.ln, f"expected an expression, found {got}")

    def literal(self):
        k, v = self.peek()
        if k == "s":
            self.i += 1
            return ("str", v)
        if k == "i" and self.peek(1) == ("p", "/"):
            self.i += 2
            _, d = self.take("i", what="a whole denominator")
            if int(d) == 0 or v.startswith("-") or d.startswith("-"):
                raise SyntaxRefusal("P007", self.ln, "a ratio is a whole number at least 0 over a whole number at least 1")
            return ("ratio", int(v), int(d))
        if k in ("i", "d"):
            self.i += 1
            unit = None
            if self.peek()[0] == "w":
                unit = self.take("w")[1]
            return ("num", Fraction(v), unit, v)
        raise SyntaxRefusal("P001", self.ln, "expected a literal after 'is': a number, a ratio n/d or a string")

    def end(self):
        if self.i != len(self.t):
            raise SyntaxRefusal("P001", self.ln, f"unexpected {self.t[self.i][1]!r} after the end of the statement")


_STMTS = ("file", "dataset", "let", "claim", "question")


def parse_line(text: str, ln: int):
    # Multi-line question blocks arrive as "header\\n  clause\\n..."
    head_line, _, body_rest = text.partition("\n")
    head = head_line.lstrip(" \t")
    j = 0
    while j < len(head) and head[j] in _IDCHAR:
        j += 1
    if j and head[:j] not in _STMTS:
        raise SyntaxRefusal(
            "P008",
            ln,
            f"{head[:j]!r} is not a statement of Reality v4 (statements: file, dataset, let, claim, question)",
        )
    toks = _tokens(head_line, ln)
    if not toks:
        return None
    p = _P(toks, ln)
    _, kw = p.take("w", what="a statement keyword (file, dataset, let, claim, question)")
    if kw in ("file", "dataset"):
        nm = p.name()
        p.take("p", "=", what="'='")
        h = p.take("h", what="sha256:<64 hex digits>")[1]
        p.end()
        return Stmt(kw, ln, name=nm, hash=h)
    if kw == "let":
        nm = p.name()
        p.take("p", "=", what="'='")
        e = p.expr()
        p.end()
        return Stmt("let", ln, name=nm, expr=e)
    if kw == "claim":
        e = p.expr()
        lit = None
        if p.peek() == ("w", "is"):
            p.i += 1
            lit = p.literal()
        p.end()
        return Stmt("claim", ln, expr=e, lit=lit)
    if kw == "question":
        form = p.take("w", what="a question form name")[1]
        nm = p.name()
        p.end()
        body = tuple(body_rest.split("\n")) if body_rest else ()
        return Stmt("question", ln, name=nm, qform=form, qbody=body)
    raise SyntaxRefusal(
        "P008",
        ln,
        f"{kw!r} is not a statement of Reality v4 (statements: file, dataset, let, claim, question)",
    )


def group_program_lines(lines):
    """Yield (line_number, text) with `question` headers joined to their indented clauses.

    Intentional grammar change (SPEC-ORD / v4 delta): only `question` statements take
    continuations. Blank and comment lines inside a question body are skipped; an unindented
    non-empty line ends the question."""
    i, n = 0, len(lines)
    while i < n:
        ln, text = lines[i]
        stripped = text.lstrip(" \t")
        if not stripped or stripped.startswith("#"):
            yield ln, text
            i += 1
            continue
        if text[:1] not in " \t" and stripped.startswith("question "):
            parts = [text]
            start = ln
            i += 1
            while i < n:
                ln2, t2 = lines[i]
                s2 = t2.lstrip(" \t")
                if not s2 or s2.startswith("#"):
                    i += 1
                    continue
                if t2[:1] in " \t":
                    parts.append(t2)
                    i += 1
                    continue
                break
            yield start, "\n".join(parts)
            continue
        if text[:1] in " \t" and stripped and not stripped.startswith("#"):
            raise SyntaxRefusal(
                "P008",
                ln,
                "indented text is only a continuation of a question statement; "
                "file, dataset, let and claim are one line each",
            )
        yield ln, text
        i += 1


_SIZE_TOKEN = re.compile(r'(#.*|"(?:\\.|[^"\\])*"?|sha256(?=:))|[A-Za-z_][A-Za-z0-9_]*|.')


def measured_size(text: str) -> int:
    """The program's size with every name (outside strings and comments) counted as one byte:
    a comment, a string and the `sha256` of a hash count their bytes; a name or any other
    character counts 1; each line end counts 1."""
    return sum(1 + sum(len(m.group(1)) if m.group(1) else 1 for m in _SIZE_TOKEN.finditer(line)) for line in text.split("\n"))


def split_program(data: bytes):
    """Yield (line_number, text) or raise SyntaxRefusal for the whole program."""
    if len(data) > MAX_NAME * MAX_PROGRAM_SIZE:
        raise SyntaxRefusal("R001", 0, f"the program's size exceeds {MAX_PROGRAM_SIZE} (bytes, with each name counted as one) (Reality bounds)")
    for i, b in enumerate(data):
        if b == 13:
            raise SyntaxRefusal("P009", data.count(b"\n", 0, i) + 1, "the program contains a carriage return; lines end with LF only")
        if b != 10 and b != 9 and not (32 <= b < 127):
            raise SyntaxRefusal("P009", data.count(b"\n", 0, i) + 1, f"byte 0x{b:02x}: a program is printable ASCII, so no character in it can look like another")
    text = data.decode("ascii")
    if measured_size(text) > MAX_PROGRAM_SIZE:
        raise SyntaxRefusal("R001", 0, f"the program's size exceeds {MAX_PROGRAM_SIZE} (bytes, with each name counted as one) (Reality bounds)")
    return list(enumerate(text.split("\n"), start=1))

"""Ledger text -> statements (req/SPEC.md section 3). Trusted.

A statement starts at a line with no leading space; indented lines continue it. Tokens: names
(ASCII letters, digits, _), strings "..." (UTF-8; escapes \\" and \\\\ only), hashes
sha256:<64 lowercase hex>, and '='. '#' starts a comment outside strings.
"""
import re

BIDI = set("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u200e\u200f\u061c")
TOKEN = re.compile(r'[ \t]+|#[^\n]*|(?P<hash>sha256:[0-9a-f]{64})(?![0-9A-Za-z_])|(?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<eq>=)|(?P<str>")')
# keyword -> (header shape, clause -> value kind, clauses that must be present)
SHAPES = {
    "person": ("N", {}, ()),
    "tool": ("N", {}, ()),
    "requirement": ("N=S", {"owner": "N", "from": "S"}, ("owner",)),
    "measure": ("N", {"for": "N", "proposed_by": "N", "says": "S", "outside": "S", "fragment": "SH"},
                ("for", "proposed_by", "says", "fragment")),
    "task": ("N=", {"propose": "N", "deliver": "N", "by": "N", "on": "H", "assigned_to": "N"}, ("assigned_to",)),
    "adopt": ("N", {"for": "N", "by": "N", "at": "S", "requirement_text": "H", "measure": "H", "sig": "S"},
              ("for", "by", "at", "requirement_text", "measure")),
    "check": ("N", {"by": "N", "on": "H"}, ("on",)),
    "try": ("N", {"on": "H"}, ("on",)),
    "status": ("N", {}, ()),
}
SHAPES["withdraw"] = SHAPES["adopt"]


class SyntaxRefusal(Exception):
    def __init__(self, line, code, msg):
        super().__init__(msg)
        self.line, self.code, self.msg = line, code, msg


class Statement:
    def __init__(self, line, kind, name, text, clauses):
        self.line, self.kind, self.name, self.text, self.clauses = line, kind, name, text, clauses

    def get(self, key):
        return self.clauses.get(key)


def tokens(text, line):
    out, i = [], 0
    while i < len(text):
        m = TOKEN.match(text, i)
        if not m:
            raise SyntaxRefusal(line, "S002" if ord(text[i]) > 127 else "S001", f"unexpected character {text[i]!r}: outside strings a ledger has names, strings, sha256:<hex> and '='")
        i = m.end()
        if m.group("str"):
            buf = []
            while True:
                if i >= len(text) or text[i] == "\n":
                    raise SyntaxRefusal(line, "S003", "a string is not closed on its line")
                c = text[i]
                if c == "\\":
                    if text[i + 1:i + 2] not in ('"', "\\"):
                        raise SyntaxRefusal(line, "S003", 'the only escapes in a string are \\" and \\\\')
                    buf.append(text[i + 1]); i += 2; continue
                i += 1
                if c == '"':
                    break
                buf.append(c)
            out.append(("str", "".join(buf)))
        elif m.lastgroup:
            out.append((m.lastgroup, m.group(m.lastgroup)))
    return out


def split(data: bytes):
    """Bytes -> [(line number, tokens)] per statement."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SyntaxRefusal(0, "S011", "the ledger is not UTF-8")
    for n, ln in enumerate(text.split("\n"), start=1):
        for c in ln:
            if c in BIDI:
                raise SyntaxRefusal(n, "S013", "a bidirectional control character can make text read differently from its bytes")
            if (ord(c) < 32 and c != "\t") or ord(c) == 127:
                raise SyntaxRefusal(n, "S014", f"control character U+{ord(c):04X}; a line ends with LF only")
    stmts = []
    for n, ln in enumerate(text.split("\n"), start=1):
        toks = tokens(ln, n)
        if not toks:
            continue
        if ln[0] in " \t":
            if not stmts:
                raise SyntaxRefusal(n, "S003", "an indented line continues a statement, and there is none before it")
            stmts[-1][1].extend(toks)
        else:
            stmts.append((n, toks))
    return stmts


def parse(line, toks):
    kind = toks[0][1] if toks[0][0] == "name" else None
    if kind not in SHAPES:
        raise SyntaxRefusal(line, "S004", f"not a ledger statement: {toks[0][1]!r} (statements: {', '.join(SHAPES)})")
    head, allowed, needed = SHAPES[kind]
    rest, name, text = toks[1:], None, None
    for want in head:
        if not rest or rest[0][0] != {"N": "name", "=": "eq", "S": "str"}[want]:
            raise SyntaxRefusal(line, "S003", f"'{kind}' is written: {usage(kind)}")
        tok = rest.pop(0)
        if want == "N":
            name = tok[1]
        elif want == "S":
            text = tok[1]
    clauses = {}
    while rest:
        key = rest.pop(0)
        if key[0] != "name" or key[1] not in allowed:
            raise SyntaxRefusal(line, "S003", f"'{key[1]}' is not a part of '{kind}' (parts: {', '.join(allowed) or 'none'})")
        if key[1] in clauses:
            raise SyntaxRefusal(line, "S003", f"'{key[1]}' is given twice")
        vals = []
        for want in allowed[key[1]]:
            if not rest or rest[0][0] != {"N": "name", "S": "str", "H": "hash"}[want]:
                raise SyntaxRefusal(line, "S003", f"'{key[1]}' takes {' and '.join({'N': 'a name', 'S': 'a string', 'H': 'sha256:<hex>'}[w] for w in allowed[key[1]])}")
            vals.append(rest.pop(0)[1])
        clauses[key[1]] = vals[0] if len(vals) == 1 else tuple(vals)
    for k in needed:
        if k not in clauses:
            raise SyntaxRefusal(line, "S003", f"'{kind}' needs '{k}': {usage(kind)}")
    if kind == "task" and ("propose" in clauses) == ("deliver" in clauses):
        raise SyntaxRefusal(line, "S003", "a task is 'propose <R>' or 'deliver <R> by <M> on sha256:<data>'")
    return Statement(line, kind, name, text, clauses)


def usage(kind):
    head, allowed, needed = SHAPES[kind]
    h = " ".join({"N": "<name>", "=": "=", "S": '"<text>"'}[w] for w in head)
    return " ".join([kind, h] + [f"{k} ..." for k in allowed])

"""The key alphabet, the lookalike rule and the invisible-character rule, fixed before any claim.

K is ASCII 0-9, A-Z, a-z (spec section 10.3). The lookalike table is the full UTS #39
confusables.txt, version 18.0.0 (2026-08-06), shipped in data/ and pinned by SHA-256; it is
compiled when this module loads, and the checker refuses to run on any other bytes.

skeleton(s): NFD; replace every character by its confusables.txt prototype; NFD again (UTS #39
section 4); then the spec's closed K rule (lowercase A-Z, o->0, i->1, l->1, then "rn"->"m").
NFD comes from Python's unicodedata, so the Unicode version is part of the trusted base and is
pinned too (UNICODE_VERSION); a different version gives no verdict at all.

Patsak's call of 25 Oct 2026: two distinct strings with equal skeletons anywhere in one claim's
scope refuse the claim, inside or outside K, and so does any invisible or format character."""

import hashlib
import os
import unicodedata

K = frozenset("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
CONFUSABLES_VERSION = "18.0.0"
CONFUSABLES_SHA256 = "6ed3ee967c9dfdf6677d563c9985182fbc50a2efb7d6059cd57b2e2ce18f5b92"
UNICODE_VERSION = "15.1.0"
_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "confusables.txt")


class PinError(Exception):
    """A pinned part of the trusted base is not what it should be: no verdict is possible."""


def _compile():
    with open(_PATH, "rb") as f:
        data = f.read()
    if hashlib.sha256(data).hexdigest() != CONFUSABLES_SHA256:
        raise PinError(f"data/confusables.txt is not the pinned UTS #39 {CONFUSABLES_VERSION} file")
    table = {}
    for line in data.decode("utf-8").split("\n"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        src, dst = line.split(";")[:2]
        s = "".join(chr(int(x, 16)) for x in src.split())
        table[s] = "".join(chr(int(x, 16)) for x in dst.split())
    return table


TABLE = _compile()   # every source in 18.0.0 is a single code point
_FOLD = {chr(c): chr(c + 32) for c in range(65, 91)}
_FOLD.update({"o": "0", "i": "1", "l": "1"})
_FOLD2 = {c: _FOLD.get(v, v) for c, v in _FOLD.items()}
_IGNORABLE = (set(range(0x180B, 0x1810)) | set(range(0x200B, 0x2010)) | set(range(0x202A, 0x202F))
              | set(range(0x2060, 0x2070)) | set(range(0xFE00, 0xFE10)) | set(range(0xFFF0, 0xFFF9))
              | set(range(0x1BCA0, 0x1BCA4)) | set(range(0x1D173, 0x1D17B)) | set(range(0xE0000, 0xE1000))
              | {0x00AD, 0x034F, 0x061C, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x3164, 0xFEFF, 0xFFA0})


def check_pins():
    if unicodedata.unidata_version != UNICODE_VERSION:
        raise PinError(f"this Python has Unicode {unicodedata.unidata_version}; Reality v4's skeleton is pinned to Unicode {UNICODE_VERSION}")


def is_key(s: str) -> bool:
    """A key is a non-empty string of characters from K."""
    return s != "" and all(c in K for c in s)


def is_header_name(s: str) -> bool:
    """Column headers addressable by name: K plus '_' (spec section 10.3, 'Outside the alphabet')."""
    return s != "" and all(c in K or c == "_" for c in s)


def skeleton(s: str) -> str:
    t = unicodedata.normalize("NFD", s)
    t = unicodedata.normalize("NFD", "".join(TABLE.get(c, c) for c in t))
    return "".join(_FOLD2.get(c, c) for c in t).replace("rn", "m")


def invisible(s: str):
    """The first character of s that cannot be seen or told apart from its absence, else None:
    controls, format characters, line and paragraph separators, spaces other than U+0020,
    unassigned, private-use and surrogate code points, default-ignorable code points, and a
    space at either end."""
    for c in s:
        cat = unicodedata.category(c)
        if cat in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp") or (cat == "Zs" and c != " ") or ord(c) in _IGNORABLE:
            return c
    if s[:1] == " " or s[-1:] == " ":
        return " "
    return None


def lookalikes(values):
    """The first pair (in the given order) of distinct values with equal skeletons, else None."""
    seen = {}
    for v in values:
        sk = skeleton(v)
        if sk in seen and seen[sk] != v:
            return (seen[sk], v)
        seen.setdefault(sk, v)
    return None

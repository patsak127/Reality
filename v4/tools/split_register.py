"""Split the pinned BIDS 1.0.1 text into numbered sentences (SPEC §8.2) and write or check
REGISTER-1.0.1.tsv. Usage:
  split_register.py TEXT REGISTER --write   # (re)write the skeleton, keeping existing classes
  split_register.py TEXT REGISTER --check   # exit 1 unless every sentence is classified once
"""
import hashlib, re, sys

PINNED = "51665a1323e1eb14bad37fa380c6e82c16cd1b8d6dbed51f269256fb346a354f"
CLASSES = {"checked", "silent", "unshowable", "notfiles", "reality-call"}
HEADER = ["id", "line", "sha256_12", "class", "codes", "decision", "note", "text"]
INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)


def sentences(raw: bytes):
    if hashlib.sha256(raw).hexdigest() != PINNED:
        raise SystemExit("not the pinned 1.0.1 text")
    text = raw.decode("utf-8").translate(INVISIBLE)
    out = []
    # a blank line ends a block; inside a block, a sentence ends at . ! ? followed by space and
    # an upper-case letter, a digit, a bullet or the end of the block; a list bullet starts one
    for lineno0, block in _blocks(text):
        for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9●○•“\"(])|\s+(?=[●○•]\s)", block):
            p = " ".join(piece.split())
            if p:
                out.append((lineno0, p))
    return out


def _blocks(text):
    start, buf = None, []
    for i, line in enumerate(text.split("\n"), 1):
        if line.strip():
            if start is None:
                start = i
            buf.append(line)
        elif buf:
            yield start, "\n".join(buf)
            start, buf = None, []
    if buf:
        yield start, "\n".join(buf)


def rows(raw):
    for n, (line, s) in enumerate(sentences(raw), 1):
        yield {"id": f"S{n:04d}", "line": str(line),
               "sha256_12": hashlib.sha256(s.encode()).hexdigest()[:12], "text": s}


def read_register(path):
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except FileNotFoundError:
        return {}
    head = lines[0].split("\t")
    return {r["sha256_12"] + r["id"]: r for r in (dict(zip(head, l.split("\t"))) for l in lines[1:] if l)}


def main():
    text, reg, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    raw = open(text, "rb").read()
    old = read_register(reg)
    new = []
    for r in rows(raw):
        o = old.get(r["sha256_12"] + r["id"], {})
        for k in ("class", "codes", "decision", "note"):
            r[k] = o.get(k, "")
        new.append(r)
    if mode == "--write":
        with open(reg, "w", encoding="utf-8", newline="\n") as f:
            f.write("\t".join(HEADER) + "\n")
            for r in new:
                f.write("\t".join(r[k].replace("\t", " ") for k in HEADER) + "\n")
        print(f"{len(new)} sentences")
    else:
        bad = [r["id"] for r in new if r["class"] not in CLASSES]
        print(f"{len(new)} sentences, {len(new) - len(bad)} classified, {len(bad)} not")
        sys.exit(1 if bad or len(old) != len(new) else 0)


if __name__ == "__main__":
    main()

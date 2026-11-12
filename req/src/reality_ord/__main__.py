"""CLI: python -m reality_ord path.ro --files DIR...

Shared entry: builds a Store and calls reality4.kernel.check (same as `python -m reality4 check`).
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from .eval_ord import check_text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SPEC-ORD via shared Reality v4 checker")
    ap.add_argument("program", type=pathlib.Path)
    ap.add_argument("--files", type=pathlib.Path, nargs="+", required=True)
    args = ap.parse_args(argv)
    text = args.program.read_text(encoding="ascii")
    paths: list[pathlib.Path] = []
    for p in args.files:
        if p.is_dir():
            paths.extend(sorted(x for x in p.iterdir() if x.is_file()))
        elif p.is_file():
            paths.append(p)
        else:
            print(f"not a file or directory: {p}", file=sys.stderr)
            return 2
    sys.stdout.write(check_text(text, paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

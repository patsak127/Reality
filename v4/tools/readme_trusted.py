"""Rewrite the trusted-base table and total in README.md from the files' current line counts."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tests"))
from test_source import SRC, TRUSTED  # noqa: E402

counts = sorted(((len(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read().splitlines()), f) for f in TRUSTED), key=lambda x: (-x[0], x[1]))
total = sum(n for n, _ in counts)
table = "| file | lines |\n|---|---|\n" + "".join(f"| `{f}` | {n} |\n" for n, f in counts) + f"| **total** | **{total}** |\n"
p = os.path.join(HERE, "..", "README.md")
s = open(p, encoding="utf-8").read()
s = re.sub(r"\| file \| lines \|\n.*?\| \*\*total\*\* \| \*\*\d+\*\* \|\n", lambda m: table, s, flags=re.S)
s = re.sub(r"\(`wc -l`, \d+ lines\)", f"(`wc -l`, {total} lines)", s)
open(p, "w", encoding="utf-8").write(s)
print(total)

"""Summarise a mutator run of v4: per module the killed, survived and uncovered sites, and every
survivor with its line and the source line it mutates (for classification by reading).

python3 tools/mutation/summarize.py LOGDIR SRCDIR > table.md   (a report, not a gate)"""
import os
import re
import sys

ROW = re.compile(r"^Total\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)")
SITE = re.compile(r"^(KILLED|SURVIVED|UNCOVERED|TIMEOUT)\s+(\S+?):(\d+)\s+(.*)$")


def main(logdir, srcdir):
    rows, surv = [], []
    for fn in sorted(os.listdir(logdir)):
        if not fn.endswith(".log"):
            continue
        text = open(os.path.join(logdir, fn), encoding="utf-8", errors="replace").read()
        tot = [m for m in (ROW.match(ln) for ln in text.splitlines()) if m]
        if tot:
            k, s, u, n = tot[-1].groups()
            rows.append((fn[:-4], int(n), int(k), int(s), int(u)))
        for ln in text.splitlines():
            m = SITE.match(ln)
            if m and m.group(1) in ("SURVIVED", "TIMEOUT"):
                surv.append((m.group(2), int(m.group(3)), m.group(4), m.group(1)))
    print("| module | sites | killed | survived | uncovered |\n|---|---|---|---|---|")
    for r in rows:
        print("| %s | %d | %d | %d | %d |" % r)
    print("| **total** | **%d** | **%d** | **%d** | **%d** |" % tuple(sum(r[i] for r in rows) for i in range(1, 5)))
    print("\n## Survivors\n")
    cache = {}
    for path, line, what, kind in surv:
        p = os.path.join(srcdir, os.path.basename(path))
        src = cache.setdefault(p, open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else [])
        code = src[line - 1].strip() if 0 < line <= len(src) else ""
        print(f"- {os.path.basename(path)}:{line} `{what}`{' (timeout)' if kind == 'TIMEOUT' else ''}: `{code[:140]}`")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

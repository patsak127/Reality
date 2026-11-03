"""v4 SPEC 9.1: actual work <= K x charged steps + a per-statement constant, K = 64 [prov].

Actual work is measured as Python line events inside the reality4 package (sys.settrace). That
sees every interpreted loop; work done inside C builtins (str.split, sorted, bytes compares) is
not seen; it is linear in bytes the reader already charged when it read the file, except big-number
arithmetic, which SPEC 9.1 charges by size and test_v4_fixes.test_r22_* checks by wall time. The constant
covers parsing, sort building and witness set-up, which do not grow with the files."""
import os
import random
import sys

import helpers
import test_differential as T
from reality4 import readers as R
from reality4.kernel import check

K = 64
PER_STATEMENT = 25_000
SRCDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "reality4"))


def measure(prog, files, monkeypatch):
    charged, lines = [0], [0]
    orig = R.Steps.add

    def add(self, k=1):
        charged[0] += k
        return orig(self, k)
    monkeypatch.setattr(R.Steps, "add", add)

    def tracer(frame, event, arg):
        if frame.f_code.co_filename.startswith(SRCDIR):
            lines[0] += 1
            return tracer
        return None
    sys.settrace(tracer)
    try:
        check(prog.encode(), R.Store(files))
    finally:
        sys.settrace(None)
        monkeypatch.setattr(R.Steps, "add", orig)
    return lines[0], charged[0]


def statements(prog):
    return sum(1 for ln in prog.split("\n") if ln.strip())


CLAIMS = ['count(where(t, eq("g", "F")))', 'mean(where(t, eq("g", "F"), ge("x", c = 10)), "x")',
          'cell(t, key("id", "s5"), "x")', 'median(where(t, eq("g", "F"), ne("id", "s3")), "x")',
          'sample_sd(t, "x")', 'share(where(t, eq("g", "F"), lt("x", c = 50)), where(t, eq("g", "F")))',
          'order(t, "x", 3)']


def test_work_is_bounded_by_the_charge(tmp_path, monkeypatch):
    worst = []
    for n in (10, 1000, 5000):
        rows = "\n".join(f"s{r}\t{'F' if r % 2 else 'M'}\t{r % 97}" for r in range(n))
        p, h = helpers.tsv(tmp_path, f"b{n}.tsv", "id\tg\tx\n" + rows + "\n")
        for cl in CLAIMS:
            prog = f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {cl}\n"
            worst.append(measure(prog, [p], monkeypatch) + (statements(prog), cl))
    rng = random.Random(7)
    for i in range(60):
        data, nc = T.table(rng)
        p, h = helpers.tsv(tmp_path, f"t{i}.tsv", data)
        prog = T.program(rng, h, nc)
        worst.append(measure(prog, [p], monkeypatch) + (statements(prog), prog))
    assert sum(w[1] > 1000 for w in worst) >= 10   # the corpus does real, charged work
    bad = [w for w in worst if w[0] > K * w[1] + PER_STATEMENT * w[2]]
    assert not bad, bad[:3]

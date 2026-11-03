"""tools/groundtruth.py, the brute-force runners' shared ground truth (28 Oct 2026): a deliberately wrong refusal must
be caught, and a re-check must be judged on answering tables. The ad hoc runners before 28 Oct 15:10 re-ran a W1
statement through the kernel, which refuses S008 on every answering table: their re-checks could not contradict."""
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import groundtruth as G  # noqa: E402
from reality4 import kernel as K, witness as W  # noqa: E402


def test_a_deliberately_wrong_refusal_is_caught():
    assert G.selftest()
    r = G.recheck_w1('count(where(t, eq("g", "A")))', G.SELF_TABLES)
    assert r.status == "contradicted" and len(r.answers) >= 2 and r.judged == 4


def test_the_kernel_could_not_have_caught_it():
    # the vacuous re-check: through the kernel, a W1 statement refuses S008 on every table, so it never answers twice
    stmt = "difference(rows(t), count(t))"
    lines = []
    for X in G.SELF_TABLES:
        h = hashlib.sha256(X.encode()).hexdigest()
        st = W.MemStore({h: X.encode()})
        st.begin_program()
        lines += [ln for ln in K._check(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {stmt}\n".encode(), st)[1] if ln.startswith("line")]
    assert all("[S008" in ln for ln in lines), lines
    r = G.recheck_w1(stmt, G.SELF_TABLES)
    assert r.status == "ok" and r.judged == 4 and len(r.answers) == 1


def test_no_answering_table_is_unjudged_not_ok():
    r = G.recheck_w1('mean(where(t, eq("g", "C")), 2)', G.SELF_TABLES)
    assert r.status == "unjudged" and r.judged == 0


def test_check_line_has_the_kernels_shape():
    X = "g\tx\nA\t1\n"
    h = hashlib.sha256(X.encode()).hexdigest()
    st = W.MemStore({h: X.encode()})
    got = [G.check_line(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {c}\n".encode(), st)[1][0] for c in
           ("atleast(count(t), c = 1)", "atleast(count(t), c = 2)", 'mean(where(t, eq("g", "B")), 2)')]
    assert got[0].endswith("formed: holds") and "[V001" in got[1] and re.search(r"\[V\d{3},", got[2]), got


def test_a_named_sub_value_is_rechecked():
    stmt = 'atleast(difference(count(where(t, eq("g", "A"))), count(t)), c = -5)'
    assert G.recheck_w1(stmt, G.SELF_TABLES).status == "ok"   # the comparison holds everywhere
    assert G.recheck_w1(stmt, G.SELF_TABLES, fn="difference").status == "contradicted"
    assert G.fn_of("line 3: refused [S008, item 1]: difference(): ...") == "difference"


def test_every_re_checking_runner_takes_ground_truth():
    # 28 Oct 15:30 call: a runner that re-checks refusals ("CONTRADICTED") takes its answers from the evaluator
    # (groundtruth, witness.evaluate, or exact_bf's truth()), never from the kernel; so a vacuous runner cannot come back
    root = os.path.join(os.path.dirname(__file__), "..")
    bad, n = [], 0
    for d in ("tools", "tests"):
        for f in sorted(os.listdir(os.path.join(root, d))):
            if not f.endswith(".py") or f == os.path.basename(__file__):
                continue
            s = open(os.path.join(root, d, f), errors="replace").read()
            if "CONTRADICT" not in s:
                continue
            n += 1
            if not ("groundtruth" in s or "W.evaluate(" in s or "import exact_bf as B" in s):
                bad.append(f"{d}/{f}")
    assert n >= 3 and not bad, (n, bad)
    lint = os.path.join(root, "..", "verify-opus-exact", "partb", "lint_runners.py")
    if os.path.isfile(lint):   # the working tree's ad hoc runners (not in a clean copy; checks.sh runs it there too)
        import subprocess
        r = subprocess.run([sys.executable, lint], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

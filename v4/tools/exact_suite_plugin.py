"""Exact-decision Phase 0: the pytest suite as a differential corpus. Report only.

    python -m pytest -q tests -p no:cacheprovider -p exact_suite_plugin   (with tools/ on PYTHONPATH)
    EXACT_ALT=old (default) | exact     EXACT_OUT=/tmp/exact-suite.tsv
    EXACT_DUMP=/tmp/judged.pkl   (pickles (program id, line, expression as judged) per W1/W2 call)

Every program a test checks in this process (through kernel._check, which kernel.check calls) is
checked twice: first with the alternative decider (EXACT_ALT), then with the live one, whose result
the test receives, so the tests run as they would without the plugin (only slower: wall-clock tests
may fail). Each run starts with store.begin_program(), as kernel.check does. When a test has put its
own decider in kernel.witness, or set the live search's [prov] bounds (the frozen copy keeps its
own), the program is not compared. The double run changes a store's accounting, so
test_v4_mutation_run.py::test_kernel_charges_are_pinned[volumes...] fails under the plugin. Programs run by the CLI in a subprocess
are not seen. Writes one row per claim line (kinds, whether W1/W2 was reached, its code, the row-type
estimate of tools/exact_measure.py) and one row per verdict difference; prints a summary."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exact_diff as X  # noqa: E402
import exact_measure as M  # noqa: E402
from reality4 import kernel, witness  # noqa: E402

BOUNDS = ("MAX_WITNESS_STEPS",)   # the live search's other [prov] bounds went with it (phase 7)
STATE = {"progs": 0, "skipped": 0, "rows": [], "diffs": [], "test": None, "seen": set()}


def pytest_configure(config):
    orig = kernel._check
    alt = X.decider(os.environ.get("EXACT_ALT", "old"))

    def wrapped(program, store):
        if kernel.witness is not witness or (alt.__name__ == "old_witness" and any(getattr(alt, k) != getattr(witness, k) for k in BOUNDS)):
            # a test's own decider, or a test that set the live search's bounds (the frozen copy keeps its own)
            STATE["skipped"] += 1
            return orig(program, store)
        try:
            with X.using(alt):
                store.begin_program()
                _, alt_lines = orig(program, store)
        except (MemoryError, RecursionError):
            alt_lines = ["no verdict"]
        with X.using(witness) as rec:
            store.begin_program()
            res = orig(program, store)
        STATE["progs"] += 1
        pid = f"{STATE['test']}#{STATE['progs']}"
        a, b = X.statement_lines(alt_lines), X.statement_lines(res[1])
        for d in X.compare({pid: (a, None, program)}, {pid: (b, None, program)}, "suite"):
            STATE["diffs"].append(d)
        key = (program, tuple(sorted(b.items())))
        if key in STATE["seen"]:   # one program checked many times counts once
            return res
        STATE["seen"].add(key)
        reached = {r["line"]: r for r in rec.records}
        if os.environ.get("EXACT_DUMP"):
            STATE.setdefault("dump", []).extend((pid, r["line"], r["judged"], r.get("secs")) for r in rec.records)
        for ln, ks in sorted(M.claim_kinds(program).items()):
            st = b.get(ln)
            r = reached.get(ln)
            try:
                est = M.estimate(r["judged"]) if r is not None else {}
            except Exception:   # measurement only
                est = {}
            nslots = len(M.names(r["judged"])) if r is not None else 0
            STATE["rows"].append(("suite", pid, ln, sorted(ks) + (["2+ slots"] if nslots >= 2 else []), r is not None,
                                  "none" if st is None else ("formed" if st[0] == "formed" else st[1]), est, "", r["code"] if r is not None else None))
        return res
    kernel._check = wrapped


def pytest_runtest_setup(item):
    STATE["test"] = item.nodeid


def pytest_terminal_summary(terminalreporter):
    w = terminalreporter.write_line
    w(f"exact_suite_plugin: {STATE['progs']} programs compared ({os.environ.get('EXACT_ALT', 'old')} vs live), "
      f"{STATE['skipped']} skipped (a test's own decider or bounds), {len(STATE['seen'])} distinct, {len(STATE['diffs'])} statement differences")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        M.report(STATE["rows"])
    for ln in buf.getvalue().splitlines():
        w(ln)
    for d in STATE["diffs"][:50]:
        w("DIFF " + "\t".join(map(str, d)))
    if os.environ.get("EXACT_DUMP"):
        import pickle
        with open(os.environ["EXACT_DUMP"], "wb") as f:
            pickle.dump(STATE.get("dump", []), f)
    out = os.environ.get("EXACT_OUT")
    if out:
        with open(out, "w", encoding="utf-8") as f:
            for c, pid, ln, ks, reach, v, est, cc, wc in STATE["rows"]:
                f.write(f"{pid}\t{ln}\t{','.join(ks)}\t{int(reach)}\t{wc or '-'}\t{v}\t" + " ".join(f"{s}:{a}/{b}/{g}/{p}" for s, (a, b, g, p) in sorted(est.items())) + "\n")
            for d in STATE["diffs"]:
                f.write("DIFF\t" + "\t".join(map(str, d)) + "\n")

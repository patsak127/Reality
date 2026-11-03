"""BB's call on Patsak's behalf (28 Oct 2026 09:05, reversible; opus-fix-v4/LOG.md): running out of memory is never an
outcome of the exact path. The structures that grow with a system (fm's new atoms, its integer atoms and tidy's keys, lp's
tableau and each pivot's numbers) are held against the stated bound before they are built (decide.hold: STEP_BYTES
accounted bytes a step, SPEC-EXACT 8), so the worst case is R013. Each test runs in a child process under RLIMIT_AS,
where an uncharged structure would end in MemoryError instead."""
import os
import subprocess
import sys
import textwrap

import pytest

from test_source import SRC

pytestmark = pytest.mark.skipif(os.name != "posix", reason="setrlimit(RLIMIT_AS) exists only on POSIX")


def child(code, limit):
    pre = f"import resource, sys\nresource.setrlimit(resource.RLIMIT_AS, ({limit}, {limit}))\nsys.path.insert(0, {os.path.abspath(SRC)!r})\n"
    r = subprocess.run([sys.executable, "-c", pre + textwrap.dedent(code)], capture_output=True, text=True, timeout=1200)
    return r.returncode, r.stdout.strip(), r.stderr[-2000:]


def test_an_elimination_too_big_to_hold_refuses_before_it_is_built():
    # 2,000 atoms with z > 0 and 2,000 with z < 0: 4,000,000 new atoms, under the atom count's bound (5e7) but gigabytes
    # of dicts; the byte charge refuses before one is made (in 1 GB).
    rc, out, err = child('''
        from reality4 import decide as D
        P = [({("z", 0): 1, ("n", i % 5): 1 + i % 7, D.ONE: -i}, False) for i in range(2000)]
        N = [({("z", 0): -1, ("n", (i + 1) % 5): 2, ("n", (i + 2) % 5): -1, D.ONE: i}, True) for i in range(2000)]
        try:
            D.fm(P + N, [("z", 0)], 50_000_000)
            print("built")
        except D.Big as e:
            print("R013", e)
        ''', 1 << 30)
    assert rc == 0 and out.startswith("R013") and "21 bytes a step" in out, (rc, out, err)


def test_a_relaxation_is_charged_before_its_tableau_is_built_and_given_back():
    # bfe1's MemoryError (28 Oct 2026): a relaxation of 2,103 atoms over 5 variables (8.86 million cells). With the bound
    # nearly spent, R013 before the tableau is built; with a fresh bound it is solved and its charge given back.
    rc, out, err = child('''
        from reality4 import decide as D, witness as W
        ints = [({("n", i % 5): 1 + i % 7, ("n", (i + 1) % 5): -(1 + i % 3)}, -(i % 11)) for i in range(2103)]
        try:
            D.MEM[0] = D.MEM_STEPS - 1000
            D.lp(ints)
            print("built")
        except D.Big as e:
            print("R013", e)
        D.MEM[0] = 0
        r = D.lp(ints[:40])
        print(r and r[0], D.MEM[0])
        ''', 1 << 30)
    lines = out.splitlines()
    assert rc == 0 and lines[0].startswith("R013") and lines[1].split()[1] == "0", (rc, out, err)


def test_bfe1_claim_60_refuses_s008_w1_not_memory_error():
    # The claim bfe1 died on in MemoryError under a 3 GB limit (an lp tableau of 2,103 atoms; 28 Oct 2026, on 2988dd9). It
    # holds on every answering input (mean of x <= 1 less the median of x > 0.4 is below 0.3): S008 W1, by the half cuts
    # (SPEC-EXACT 3.5a; it refused R013 on the memory bound before them, a wrong code). Under 3 GB: S008 W1.
    rc, out, err = child('''
        import hashlib
        from reality4 import kernel as K, witness as W
        claim = 'atmost(difference(mean(where(t, le("x", c = 1)), 2), median(where(t, gt("x", c = 0.4)), 2)), c = 0.5)'
        X = "g\\tx\\ty\\nA\\t2\\t0\\nB\\t2\\t0\\nA\\t2\\t0\\nA\\t0\\t1\\n"
        h = hashlib.sha256(X.encode()).hexdigest(); st = W.MemStore({h: X.encode()}); st.begin_program()
        print([l for l in K._check(f"file f = sha256:{h}\\nlet t = tsv(f)\\nclaim {claim}\\n".encode(), st)[1] if l.startswith("line")][0])
        ''', 3 * 10 ** 9)
    assert rc == 0 and "[S008" in out and "W1" in out, (rc, out, err)


def test_the_integer_steps_frames_are_held_and_given_back():
    # Item 2 (28 Oct 2026): intstep's frames (its depth, and pin's growth of coefficients) are bounded by nothing stated,
    # so MSearch holds each frame's atoms while it runs: R013 with the bound spent, and nothing left held once it returns.
    rc, out, err = child('''
        from reality4 import decide as D, intstep as I
        sys_ = [("ge", I.form({0: 3, 1: -2}, -1)), ("ge", I.form({0: -1, 1: 1}, 4))]
        D.MEM[0], held = D.MEM_STEPS - 5, [0]
        try:
            D.MSearch(1000, held).decide(sys_)
            print("built")
        except D.Big as e:
            print("R013", e)
        D.MEM[0], held = 0, [0]
        S = D.MSearch(1000, held)
        print(S.decide(sys_) is not None, held[0] > 0, S.now)
        ''', 1 << 30)
    lines = out.splitlines()
    assert rc == 0 and lines[0].startswith("R013") and lines[1] == "True True 0", (rc, out, err)


def test_cases_and_branches_are_held_while_a_question_needs_them():
    # Item 2: a question's cases (up to MAX_CASES, each the size of what the statement names) and their branches are held
    # in its Decide call and given back when it returns; with too small a bound, R013 on memory, never MemoryError.
    rc, out, err = child('''
        import hashlib
        from reality4 import kernel as K, witness as W, decide as D
        X = "g\\tx\\nA\\t1\\nB\\t2\\n"
        h = hashlib.sha256(X.encode()).hexdigest()
        seen, cases = [], D.Model.cases
        def spy(self, es, held):
            out = cases(self, es, held)
            seen.append((len(out), held[0]))
            return out
        D.Model.cases = spy
        def run():
            st = W.MemStore({h: X.encode()}); st.begin_program()
            return [l for l in K._check(f"file f = sha256:{h}\\nlet t = tsv(f)\\nclaim atleast(count(where(t, eq(\\"g\\", \\"A\\"))), c = 1)\\n".encode(), st)[1] if l.startswith("line")][0]
        print(run(), D.MEM[0])
        print(all(n > 0 and b > 0 for n, b in seen))
        D.MEM_STEPS = 3
        print(run())
        ''', 1 << 30)
    lines = out.splitlines()
    assert rc == 0 and "R013" not in lines[0] and lines[0].endswith(" 0") and lines[1] == "True", (rc, out, err)
    assert "[R013" in lines[2] and "steps of memory" in lines[2], (rc, out, err)


def test_json_a_csv_table_and_the_memo_are_held_against_the_bound(tmp_path, monkeypatch):
    """(A08, Argon review 08 and the CSV item of KNOWN-OPEN's memory floor; its repro at a 2,000,000-byte accounted cap)
    json() and json_file() parsed before their known charge (64 a byte + 64) met room(), a CSV table was charged only once
    built (its pre-check counts lines), and begin_program kept the memo up to MAX_ACCOUNTED, so a program inside the
    bounds could hold its own bound and the last program's (on the box: 2,575 MB for two programs of 1.01e9 accounted
    bytes; a 26.4 MB JSON and an 11,150,000-row CSV out of memory at 2.0625 GiB). Now each is refused R012 before it
    grows, with the same verdict as after, and the memo is dropped at each program."""
    from helpers import tsv as put
    from reality4 import readers as R0
    from reality4.kernel import check
    monkeypatch.setattr(R0, "MAX_ACCOUNTED", 2000000)
    made = {"json": 0, "csv": 0}
    pj, cf = R0.parse_json, R0._csv_fields
    monkeypatch.setattr(R0, "parse_json", lambda *a: made.__setitem__("json", made["json"] + 1) or pj(*a))
    monkeypatch.setattr(R0, "_csv_fields", lambda *a: made.__setitem__("csv", made["csv"] + 1) or cf(*a))

    def go(text, claim, st=None):
        p, h = put(tmp_path, f"{len(text)}.t", text)
        st = st or R0.Store([p], [])
        out = check(f"file f = sha256:{h}\nclaim {claim}\n".encode(), st)[1]
        return " ".join(x for x in out if x.startswith("line")), st
    got, _ = go("[" + "1," * 20000 + "1]", "exceeds(item(json(f), 1), c = 0)")
    assert "[R012" in got and made["json"] == 0, (got, made)
    got, _ = go("x,y\n" + "ab,cd\n" * 20000, "rows(csv(f))")
    assert "[R012" in got and 0 < made["csv"] < 10000, (got, made)
    got, st = go("[1, 2]", "exceeds(item(json(f), 1), c = 0)")
    assert ": formed" in got and st._memo
    st.begin_program()
    assert not st._memo and not st._sizes


def test_other_text_cells_are_charged_no_more_than_their_least_characters(monkeypatch):
    """(B09, Argon review 2 09; its repro at 1 GiB, scaled here to an 8,000,000-byte accounted cap) mlb charged an other-text
    cell its least ASCII line's characters, but a 2-byte UTF-8 character is one character, so a table of the cut's rows
    could fit while the model said none did: S008 "holds only by the read limit" on a tiny f, against V001 on a readable
    table. Now an other-text cell is charged ceil(bytes / 4) characters, and the tiny f is not S008."""
    import hashlib
    from reality4 import kernel as K, readers as R0, witness as W
    from reality4.decide import OTHC
    from reality4.keys import skeleton, invisible
    MAX, CUT = 8000000, 20000
    monkeypatch.setattr(R0, "MAX_ACCOUNTED", MAX)
    by = {}
    for c in OTHC:
        if c not in "\n\r\"\t" and invisible(c) is None:
            by.setdefault(skeleton(c), []).append(c)
    reps = [cs[0] for cs in by.values()]
    lit = lambda c: c if 32 <= ord(c) < 127 and c not in '"\\' else f"\\x{ord(c):02x}"
    nes = ", ".join(f'ne(1, "{lit(c)}")' for c in reps)
    sks = {skeleton(c) for c in reps}
    utf = next(chr(i) for i in range(0xA1, 0x400) if len(chr(i).encode()) == 2 and invisible(chr(i)) is None
               and skeleton(chr(i)) not in sks)
    cost = lambda n, ch, w: w * n + 64 + 64 + 145 + n * (144 + ch) + 72 * n + 64 + 2
    target = (MAX - cost(CUT, 2, 3) + 1 + MAX - cost(CUT, 1, 3)) // 2
    ng = max(n for n in range(1, 40000) if cost(n, 1, 2) <= target)

    def run(f):
        g = b"h\n" + b"a\n" * ng
        hf, hg = hashlib.sha256(f).hexdigest(), hashlib.sha256(g).hexdigest()
        st = W.MemStore({hf: f, hg: g})
        st.begin_program()
        prog = (f"file g = sha256:{hg}\nclaim exceeds(count(where(tsv(g), eq(1, \"a\"))), c = 0)\n"
                f"file f = sha256:{hf}\nclaim below(count(where(tsv(f), {nes})), c = {CUT})\n").encode()
        return " ".join(x for x in K._check(prog, st)[1] if x.startswith("line 4"))
    tiny = run(f"g\n{utf}\n".encode())
    assert tiny and "[S008" not in tiny, tiny
    assert "[V001" in run(b"g\n" + (utf.encode() + b"\n") * CUT)



def test_earlier_statements_rows_of_the_slot_are_charged_on_the_candidate(monkeypatch):
    """(B0304, Argon review 2 03; its repro at 1 GiB with 147 earlier claims, scaled here to an 8,000,000-byte accounted cap
    and 8) The memory held at a statement kept the where() rows earlier statements built from its own file at their size on
    the actual input (10,000 rows "a": 5.76 MB), so below(count(where(tsv(f), eq(1, "z"))), c = 12000) was S008 "holds
    only by the read limit", though the program reads 150 "a" and 12,000 "z" rows (V001). held() now leaves out every
    structure made from the statement's files, and each certificate runs the earlier statements again on its candidate."""
    import hashlib
    from reality4 import kernel as K, readers as R0, witness as W
    monkeypatch.setattr(R0, "MAX_ACCOUNTED", 8000000)

    def run(data):
        h = hashlib.sha256(data).hexdigest()
        st = W.MemStore({h: data})
        st.begin_program()
        prog = f"file f = sha256:{h}\n" + "".join(f'claim exceeds(count(where(tsv(f), eq(1, "a"))), c = {k})\n' for k in range(8))
        out = K._check((prog + 'claim below(count(where(tsv(f), eq(1, "z"))), c = 12000)\n').encode(), st)[1]
        return [x for x in out if x.startswith("line 10")]
    got = run(b"c1\n" + b"a\n" * 10000)
    assert got and ": formed" in got[0], got
    got = run(b"c1\n" + b"a\n" * 150 + b"z\n" * 12000)
    assert got and "[V001" in got[0], got


def test_a_lets_json_is_charged_once(monkeypatch):
    """(B0304, Argon review 2 04; its repro at 1 GiB, a 16.5 MB JSON, scaled here to an 8,000,000-byte cap and 122,980
    bytes) held() subtracted a let's files only when they were tables, so a let's JSON (64 a byte) was held at its size
    and charged again by each certificate: through a let the claim was R013 (a certificate input past the read limit),
    inline it formed. Now every structure of the let's files is left out and charged again once: both form."""
    import hashlib
    from reality4 import kernel as K, readers as R0, witness as W
    monkeypatch.setattr(R0, "MAX_ACCOUNTED", 8000000)
    k = "k" * 200
    pre, suf = b'{"' + k.encode() + b'": "1", "p": "', b'"}'
    data = pre + b"x" * (122980 - len(pre) - len(suf)) + suf   # held 7,993,828: less room left than a certificate's JSON needs
    h = hashlib.sha256(data).hexdigest()

    def run(prog):
        st = W.MemStore({h: data})
        st.begin_program()
        return [x for x in K._check(prog.encode(), st)[1] if x.startswith("line")]
    inline = run(f'file j = sha256:{h}\nclaim member(json(j), "{k}") is "1"\n')
    let = run(f'file j = sha256:{h}\nlet x = member(json(j), "{k}")\nclaim x is "1"\n')
    assert len(inline) == len(let) == 1 and ": formed" in inline[0] and ": formed" in let[0], (inline, let)


def test_two_names_of_one_file_read_by_lets_answer_from_the_candidate():
    """(B0304, found by its gate: vdH bfs, 938 X001) file f and file h with the same bytes, read by let t = tsv(f) and
    let u = tsv(h): the decision takes them as one slot f, so a judged where(u, ..) reads tsv(f) under u's let mark. A
    certificate's earlier statements must read that node, not u's own (h, the program's bytes), or u's value on the
    candidate is the actual table: X001. Now the same verdict as without the earlier statements (S008)."""
    import hashlib
    from reality4 import kernel as K, witness as W
    a = b"x\n0\n0\n"
    h = hashlib.sha256(a).hexdigest()
    st = W.MemStore({h: a})
    st.begin_program()
    c = 'atmost(difference(sample_variance(where(t, ge("x", c = 0), le("x", c = 1)), 1), population_variance(where(u, ge("x", c = 0), le("x", c = 3)), 1)), c = 2)'
    out = [x for x in K._check(f"file f = sha256:{h}\nfile h = sha256:{h}\nlet t = tsv(f)\nlet u = tsv(h)\nclaim {c}\n".encode(), st)[1] if x.startswith("line")]
    assert len(out) == 1 and "[S008" in out[0], out


def test_a_prefix_statements_rows_of_another_file_are_charged_once(monkeypatch):
    """(C02, review 3 02, its repro at a 6,000,000-byte accounted cap) A certificate runs again every earlier statement
    that read the judged claim's file (B0304), where() rows of its other files too, but held() left out only the rows
    made from the judged claim's files: an earlier claim over g and f had its where(tsv(g)) rows (20,000: 1,440,064
    bytes) held and charged again, so below(count(where(tsv(f), eq(1, "z"))), c = 4000) was R013 (a certificate input
    past the read limit) though the program on 4,000 rows "z" peaks at 5,256,746 bytes and is V001. held() now leaves
    out every where() row of the statements the certificate runs again: it forms, as with no such earlier claim."""
    import hashlib
    from reality4 import kernel as K, readers as R0, witness as W
    monkeypatch.setattr(R0, "MAX_ACCOUNTED", 6000000)
    g = b"c1\n" + b"a\n" * 20000

    def run(f, prog):
        hg, hf = hashlib.sha256(g).hexdigest(), hashlib.sha256(f).hexdigest()
        st = W.MemStore({hg: g, hf: f})
        st.begin_program()
        out = K._check((f"file g = sha256:{hg}\nfile f = sha256:{hf}\n" + prog).encode(), st)[1]
        return [x for x in out if x.startswith("line")]
    below = 'claim below(count(where(tsv(f), eq(1, "z"))), c = 4000)\n'
    mixed = 'claim exceeds(difference(count(where(tsv(g), eq(1, "a"))), count(where(tsv(f), eq(1, "a")))), c = -1)\n' + below
    small, big = b"c1\n" + b"a\n" * 5, b"c1\n" + b"z\n" * 4000
    assert ": formed" in run(small, below)[-1]
    got = run(big, mixed)
    assert len(got) == 2 and "[V001" in got[1], got
    got = run(small, mixed)
    assert len(got) == 2 and ": formed" in got[0] and ": formed" in got[1], got


def test_a_let_on_another_file_is_not_charged_again_by_a_certificate(monkeypatch):
    """(D02, review 4 02, its repro at a 6,000,000-byte accounted cap) A certificate runs again the earlier statements
    that read the judged claim's file, inlined: a let they use that reads only g (20,000 rows "a", 1,440,064 bytes of
    where() rows, held by the program) was evaluated again and charged on top of its held rows, so
    below(count(where(tsv(f), eq(1, "z"))), c = 4000) was R013 though it forms with the where() written in the claim.
    Such a let is now the program's value in the re-run (the kernel does not evaluate it again on another f): it
    forms, and the 4,000-row file is V001, for a let, a let of a let, and a let that reads both files."""
    import hashlib
    from reality4 import kernel as K, readers as R0, witness as W
    monkeypatch.setattr(R0, "MAX_ACCOUNTED", 6000000)
    g = b"c1\n" + b"a\n" * 20000

    def run(f, prog):
        hg, hf = hashlib.sha256(g).hexdigest(), hashlib.sha256(f).hexdigest()
        st = W.MemStore({hg: g, hf: f})
        st.begin_program()
        out = K._check((f"file g = sha256:{hg}\nfile f = sha256:{hf}\n" + prog).encode(), st)[1]
        return [x for x in out if x.startswith("line")]
    below = 'claim below(count(where(tsv(f), eq(1, "z"))), c = 4000)\n'
    s = 'let s = where(tsv(g), eq(1, "a"))\n'
    fa = 'count(where(tsv(f), eq(1, "a")))'
    progs = [s + f'claim exceeds(difference(count(s), {fa}), c = -1)\n' + below,
             s + f'let u = count(s)\nclaim exceeds(difference(u, {fa}), c = -1)\n' + below,
             s + f'let v = difference(count(s), {fa})\nclaim exceeds(v, c = -1)\n' + below]
    small, big = b"c1\n" + b"a\n" * 5, b"c1\n" + b"z\n" * 4000
    for prog in progs:
        got = run(small, prog)
        assert ": formed" in got[-1] and ": formed" in got[-2], got
        assert "[V001" in run(big, prog)[-1]

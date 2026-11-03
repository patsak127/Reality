"""Gate E: the refusal catalogue. Every refusal path and every result shape, with the full output
pinned in tests/golden/catalogue.txt (reviewed by hand when written; regenerate with
REQ_WRITE_GOLDEN=1 only after reading the diff). Written to kill the mutants the first gate-E sweep
left alive: a changed code, a dropped 'raise', or a changed word in any message changes this output."""
import hashlib, os, subprocess
from pathlib import Path

from reality_req.form import Ledger
from reality_req import bind, run as runmod
from reality_req.__main__ import main

GOLDEN = Path(__file__).parent / "golden" / "catalogue.txt"
H = lambda s: hashlib.sha256(s.encode("utf-8", "surrogateescape")).hexdigest()
TEXT = "the upscaler must preserve artistic intent"
AT = '"2026-11-14T15:02:00+01:00"'
FRAG = 'let s = where(t, eq("k", "a"))\nclaim mean(s, "v")\nclaim atmost(mean(s, "v"), c = 4)\nclaim atleast(mean(s, "v"), c = 0)\n'
FRAG1 = 'claim atmost(mean(t, "v"), c = 4)\n'
D = {k: k * 64 for k in "abcdef"}    # data hashes the fake runner knows
RESULTS = {
    D["a"]: dict(verdict="HOLDS", held=2, total=2, shown=[(2, 'mean(s, "v") = 3 (Exact)')], failed=[]),
    D["b"]: dict(verdict="DOES NOT HOLD", held=1, total=2, shown=[], failed=[(3, "v4: 5 is not at most 4")]),
    D["c"]: dict(verdict="DOES NOT HOLD", held=0, total=2, shown=[], failed=[(3, "v4: x"), (4, "v4: y")]),
    D["d"]: dict(verdict="NOT CHECKED", why="the v4 checker gives no verdict: test", shown=[], failed=[]),
}
HEAD = f'person patsak\nperson alex\ntool grokbot\nrequirement R1 = "{TEXT}"\n  owner patsak\n'


def measure(name="M1", req="R1", by="grokbot", path="M1.fragment", frag=FRAG, extra=""):
    return f'measure {name} for {req} proposed_by {by} says "within 4 levels"{extra}\n  fragment "{path}" sha256:{H(frag)}\n'


def adopt(m="M1", req="R1", by="patsak", at=AT, frag=FRAG, text=TEXT, sig=' sig "a.sig"', word="adopt"):
    return f"{word} {m} for {req} by {by} at {at} requirement_text sha256:{H(text)} measure sha256:{H(frag)}{sig}\n"


BASE = HEAD + measure()
ADOPTED = BASE + adopt()
CASES = {
    # syntax.py
    "S002 non-ASCII outside a string": "person p\u00e9\n",
    "S001 ASCII outside the token set": "person p@\n",
    "S003 unclosed string": 'person p\nrequirement R = "abc\n',
    "S003 bad escape": 'person p\nrequirement R = "a\\n" owner p\n',
    "escapes that form": 'person p\nrequirement R = "a\\"b\\\\c" owner p\n',
    "S014 control character": "person p\x01\n",
    "S014 DEL": "person p\x7f\n",
    "tab forms": "person\tp\n",
    "S013 bidi": "person p\u202e\n",
    "S003 indented first line": "  person p\n",
    "S004 not a statement": "banana x\n",
    "S004 not a name": '"x" y\n',
    "S003 header": "person\n",
    "S003 header missing =": 'person p\nrequirement R1 "x" owner p\n',
    "S003 not a part (none)": "person p owner q\n",
    "S003 not a part": 'person p\nrequirement R = "x" owner p colour p\n',
    "S003 given twice": 'person p\nrequirement R = "x" owner p owner p\n',
    "S003 clause takes a name": 'person p\nrequirement R = "x" owner "p"\n',
    "S003 clause at end without value": 'person p\nrequirement R = "x" owner\n',
    "S003 fragment takes two": HEAD + 'measure M1 for R1 proposed_by grokbot says "x" fragment "M1.fragment"\n',
    "S003 needs": 'person p\nrequirement R = "x"\n',
    "S003 task both": HEAD + "task T = propose R1 deliver R1 assigned_to alex\n",
    "S003 task neither": HEAD + "task T = assigned_to alex\n",
    # names and declarations
    "N002 twice, later use": "person patsak\nperson patsak\n" + f'requirement R1 = "{TEXT}" owner patsak\n',
    "N003 after refused declaration": f'person patsak\nrequirement R1 = "" owner patsak\n' + measure(by="patsak") + "status R1\n",
    "undeclared check does not reserve the name": f"person patsak\ncheck Q by M on sha256:{D['a']}\n" + 'requirement Q = "x" owner patsak\n',
    "E004 empty text": 'person p\nrequirement R = "" owner p\n',
    "E004 hangul filler": 'person p\nrequirement R = "\u3164" owner p\n',
    "E004 space and zero-width": 'person p\nrequirement R = " \u200b" owner p\n',
    "text with zero-width and a letter forms": 'person p\nrequirement R = "\u200b x" owner p\n',
    "E004 from": 'person p\nrequirement R = "x" owner p from ""\n',
    "N001 owner undeclared": 'requirement R = "x" owner p\n',
    "N001 owner is a requirement": 'person p\nrequirement R = "x" owner p\nrequirement S = "y" owner R\n',
    "G011 tool as owner": 'tool t\nrequirement R = "x" owner t\n',
    # measures and fragments
    "N001 proposer undeclared": HEAD + measure(by="nobody"),
    "N001 proposer is a requirement": HEAD + measure(by="R1"),
    "N001 measure for undeclared": HEAD + measure(req="R9"),
    "E004 says": HEAD + measure().replace('"within 4 levels"', '""'),
    "E004 outside": HEAD + measure(extra=' outside ""'),
    "outside forms": HEAD + measure(extra=' outside "edge flags from render_frames.py"'),
    "person proposes, one condition": HEAD + measure(by="alex", path="ONE.fragment", frag=FRAG1),
    "G023 absolute": HEAD + measure(path="/etc/M1.fragment"),
    "G023 dotdot": HEAD + measure(path="sub/../M1.fragment"),
    "G023 empty": HEAD + measure(path=""),
    "G023 missing": HEAD + measure(path="NONE.fragment"),
    "G023 hash": HEAD + measure().replace(H(FRAG), "0" * 64),
    "G023 not UTF-8": HEAD + measure(path="BAD.fragment", frag="\udcff"),
    "G020 file": HEAD + measure(path="FILE.fragment", frag="file d = sha256:" + "a" * 64 + "\n" + FRAG1),
    "G022 is": HEAD + measure(path="IS.fragment", frag='claim atmost(mean(t, "v"), c = 4)\nclaim is(mean(t, "v"), 3)\n'),
    "G020 not let or claim": HEAD + measure(path="DO.fragment", frag="do x\n" + FRAG1),
    "G021 no condition": HEAD + measure(path="NOC.fragment", frag='claim mean(t, "v")\n'),
    # tasks
    "propose task": HEAD + "task T = propose R1 assigned_to grokbot\n",
    "N001 propose assignee undeclared": HEAD + "task T = propose R1 assigned_to nobody\n",
    "N001 propose assignee requirement": HEAD + "task T = propose R1 assigned_to R1\n",
    "G001 listing": BASE + measure("M2", path="ONE.fragment", frag=FRAG1, by="alex") + adopt() + "status R1\n"
                    + adopt("M1", word="withdraw") + "task T = deliver R1 assigned_to alex\n",
    "G001 by without adoption": BASE + f"task T = deliver R1 by M1 on sha256:{D['a']} assigned_to alex\n",
    "G005 no data": ADOPTED + "task T = deliver R1 by M1 assigned_to alex\n",
    "N001 deliver assignee undeclared": ADOPTED + f"task T = deliver R1 by M1 on sha256:{D['a']} assigned_to nobody\n",
    "N001 deliver assignee requirement": ADOPTED + f"task T = deliver R1 by M1 on sha256:{D['a']} assigned_to R1\n",
    "deliver task": ADOPTED + f"task T = deliver R1 by M1 on sha256:{D['a']} assigned_to alex\n",
    "N001 deliver by undeclared": ADOPTED + f"task T = deliver R1 by M9 on sha256:{D['a']} assigned_to alex\n",
    "G003 deliver by other requirement's measure": ADOPTED + 'requirement R2 = "drops should feel fair" owner patsak\n'
        + measure("F1", req="R2", path="ONE.fragment", frag=FRAG1) + f"task T = deliver R1 by F1 on sha256:{D['a']} assigned_to alex\n",
    # adoption and withdrawal
    "G010 not owner": BASE + adopt(by="alex"),
    "G011 tool adopts": BASE + adopt(by="grokbot"),
    "G016 measure of another requirement": BASE + 'requirement R2 = "y" owner patsak\n' + adopt(req="R2", text="y"),
    "T001 now": BASE + adopt(at='" Now "'),
    "T001 no offset": BASE + adopt(at='"2026-11-14T15:02:00"'),
    "G014 adoption hashes": BASE + adopt(text="another text") + f"check R1 by M1 on sha256:{D['a']}\n"
                            + f"task T = deliver R1 by M1 on sha256:{D['a']} assigned_to alex\n",
    "G012 no sig": BASE + adopt(sig=""),
    "G012 absolute sig": BASE + adopt(sig=' sig "/tmp/a.sig"'),
    "G012 dotdot sig": BASE + adopt(sig=' sig "x/../a.sig"'),
    "G012 verifier says no": BASE + adopt(sig=' sig "bad.sig"'),
    "G015 same": ADOPTED + adopt(),
    "G015 other": ADOPTED + measure("M2", path="ONE.fragment", frag=FRAG1) + adopt("M2", frag=FRAG1),
    "G017 nothing to withdraw": BASE + adopt(word="withdraw"),
    "withdraw then check, then readopt": ADOPTED + adopt(word="withdraw") + f"check R1 by M1 on sha256:{D['a']}\n"
        + "status R1\n" + adopt(),
    # checks, trials, status
    "G004 check a measure": BASE + f"check M1 on sha256:{D['a']}\n",
    "G002 no by": ADOPTED + f"check R1 on sha256:{D['a']}\n",
    "G002 proposed only": BASE + f"check R1 by M1 on sha256:{D['a']}\n",
    "N001 check by undeclared": ADOPTED + f"check R1 by M9 on sha256:{D['a']}\n",
    "G003 check by a proposed measure": ADOPTED + measure("M2", path="ONE.fragment", frag=FRAG1) + f"check R1 by M2 on sha256:{D['a']}\n",
    "checks: holds, 1 does not, 2 do not, not checked": ADOPTED + "".join(f"check R1 by M1 on sha256:{D[k]}\n" for k in "abcd"),
    "G004 try a requirement": BASE + f"try R1 on sha256:{D['a']}\n",
    "N001 try undeclared": BASE + f"try M9 on sha256:{D['a']}\n",
    "trials before adoption, then a trial of the adopted measure": BASE + f"try M1 on sha256:{D['b']}\ntry M1 on sha256:{D['a']}\n"
        + adopt() + f"try M1 on sha256:{D['a']}\n",
    "one trial": BASE + f"try M1 on sha256:{D['a']}\n" + adopt(),
    "trial with outside": HEAD + measure(extra=' outside "flags"') + f"try M1 on sha256:{D['d']}\n",
    "G004 status of a measure": BASE + "status M1\n",
    "G004 status undeclared": BASE + "status Q\n",
    "statuses": HEAD + "status R1\n" + measure() + "status R1\n" + adopt() + "status R1\n",
}
RUN_FROM = {"run-from": (ADOPTED + f"check R1 by M1 on sha256:{D['a']}\ncheck R1 by M1 on sha256:{D['a']}\n", 10)}
NO_RUNNER = {"no runner": ADOPTED + f"check R1 by M1 on sha256:{D['a']}\n"}


def files(tmp):
    for name, frag in [("M1.fragment", FRAG), ("ONE.fragment", FRAG1), ("FILE.fragment", "file d = sha256:" + "a" * 64 + "\n" + FRAG1),
                       ("IS.fragment", 'claim atmost(mean(t, "v"), c = 4)\nclaim is(mean(t, "v"), 3)\n'),
                       ("DO.fragment", "do x\n" + FRAG1), ("NOC.fragment", 'claim mean(t, "v")\n')]:
        (tmp / name).write_text(frag)
    (tmp / "BAD.fragment").write_bytes(b"\xff")
    (tmp / "a.sig").write_text("x"); (tmp / "bad.sig").write_text("x")


def render(tmp):
    files(tmp)
    payloads, out = [], []

    def verifier(payload, who, sig):
        payloads.append(payload.decode())
        return True if sig.name == "a.sig" else f"a signature that does not match {who}'s key in the allowed_signers file"

    runner = lambda frag, data: RESULTS[data]
    groups = [(CASES, dict(runner=runner)), (RUN_FROM, dict(runner=runner)), (NO_RUNNER, {})]
    for cases, kw in groups:
        for name, case in cases.items():
            text, rf = case if isinstance(case, tuple) else (case, 0)
            del payloads[:]
            led = Ledger(tmp, verifier=verifier, run_from=rf, **kw)
            data = text.encode("utf-8", "surrogateescape")
            out += [f"### {name}", *text.splitlines(), "---", *led.check(data), f"(refused: {led.refused})"]
            out += [f"payload: {p!r}" for p in payloads]
    return "\n".join(out) + "\n"


def test_catalogue(tmp_path):
    got = render(tmp_path)
    if os.environ.get("REQ_WRITE_GOLDEN"):
        GOLDEN.write_text(got)
    assert got == GOLDEN.read_text()


def test_not_utf8_ledger_exits_1(tmp_path, capsys):
    (tmp_path / "l.rq").write_bytes(b"person \xff\n")
    assert main(["check", str(tmp_path / "l.rq")]) == 1
    assert capsys.readouterr().out == "line 0: S011 refused: the ledger is not UTF-8\nrefused (1 statement cannot be formed)\n"


# run.py: verdicts read from synthetic v4 output
def test_verdict_condition_on_fragment_line_1():
    r = runmod.verdict([FRAG1.strip()], ["line 3: formed: atmost(...) holds"])
    assert (r["verdict"], r["held"], r["total"]) == ("HOLDS", 1, 1)


def test_verdict_refusal_on_fragment_line_1_is_named():
    r = runmod.verdict(['let s = mean(t, "v")', FRAG1.strip()], ["line 3: refused [E001, item 1]: x"])
    assert r == dict(verdict="NOT CHECKED", why="the v4 checker refused fragment line 1 [E001]: x", shown=[], failed=[])
    r = runmod.verdict([FRAG1.strip()], ["line 2: refused [E001, item 1]: y"])
    assert r["why"] == "the v4 checker refused data binding line 2 [E001]: y"


def test_verdict_condition_that_formed_without_holds_is_not_checked():
    r = runmod.verdict([FRAG1.strip()], ["line 3: formed: atmost(...) = 1 (Exact)"])
    assert r["verdict"] == "NOT CHECKED" and "reported 0 of the 1 conditions" in r["why"]


def test_verdict_unknown_line():
    r = runmod.verdict([FRAG1.strip()], ["line 3: weird"])
    assert r["verdict"] == "NOT CHECKED" and "cannot read: line 3: weird" in r["why"]


# bind.py
def test_verifier_prints_nothing(tmp_path, capfd):
    k = tmp_path / "k"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "REALITY-TEST-KEY-NOT-PATSAK-capfd", "-f", str(k)], check=True)
    pub = (tmp_path / "k.pub").read_text().split()
    (tmp_path / "as").write_text(f'patsak namespaces="reality-adopt" {pub[0]} {pub[1]}\n')
    (tmp_path / "p").write_bytes(b"payload\n")
    subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(k), "-n", "reality-adopt", str(tmp_path / "p")], check=True, capture_output=True)
    capfd.readouterr()
    assert bind.Verifier(tmp_path / "as")(b"payload\n", "patsak", tmp_path / "p.sig") is True
    assert capfd.readouterr() == ("", "")


def test_verifier_without_ssh_keygen(tmp_path, monkeypatch):
    (tmp_path / "s.sig").write_text("x")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert bind.Verifier(tmp_path / "as")(b"p", "patsak", tmp_path / "s.sig") == \
        "a signature that could not be checked (ssh-keygen did not run: FileNotFoundError)"

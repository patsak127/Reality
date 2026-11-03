"""Gate E: output never says a requirement is met, preserved, fair (or the like) outside quoted text.

Every line printed for a ledger that reaches every statement kind, every result (HOLDS, DOES NOT
HOLD, NOT CHECKED, trials) and most refusals is stripped of its double-quoted spans; what is left
must not contain any word below. Requirement and description texts here are full of those words,
so a template that leaked them unquoted would fail too."""
import hashlib, re, shutil
from reality_req import say
from reality_req.bind import Verifier
from reality_req.form import Ledger
from reality_req.run import Runner
from conftest import DEMO
from test_gate_a import DATA, FRAGMENTS

FORBIDDEN = re.compile(r"\b(met|meets|preserved?|preserves|fair|fairly|fairness|unfair|satisf\w*|verif\w*|valid\w*|correct\w*|good|intent\w*|achiev\w*|pass(es|ed)?|success\w*|guarantee\w*|proven|proves?)\b", re.I)
QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')
T1 = 'the upscaler must preserve artistic intent, so the "look" is met and preserved'
T2 = "drops should feel fair"


def unquoted(line):
    return QUOTED.sub('""', line)


def ledger_text():
    t1fp = hashlib.sha256(T1.encode()).hexdigest()
    bil, sty, pub = (f"sha256:{DATA[n]}" for n in ("out_bilinear.tsv", "out_stylised.tsv", "drops_published.tsv"))
    adopt = f'adopt M1 for R1 by patsak at "2026-11-14T15:02:00+01:00" requirement_text sha256:{t1fp} measure sha256:{FRAGMENTS["M1.fragment"]}'
    q = T1.replace('"', '\\"')
    return f'''person patsak
person alex
tool grokbot
requirement R1 = "{q}" owner patsak from "a brief that says the intent is met when it feels fair"
requirement R2 = "{T2}" owner patsak
status R1
task T1 = deliver R1 assigned_to alex
task T2 = propose R1 assigned_to grokbot
measure M1 for R1 proposed_by grokbot says "intent preserved; fair; met"
  fragment "M1.fragment" sha256:{FRAGMENTS["M1.fragment"]}
measure M2 for R1 proposed_by grokbot says "edges preserved, so intent met" outside "edge flags are good and fair"
  fragment "M2.fragment" sha256:{FRAGMENTS["M2.fragment"]}
measure F1 for R2 proposed_by alex says "fair odds" fragment "F1.fragment" sha256:{FRAGMENTS["F1.fragment"]}
status R1
check R1 on {bil}
check R1 by M1 on {bil}
try M2 on {bil}
{adopt} sig "x.sig"
check R1 by M2 on {bil}
{adopt.replace("M1 for", "F1 for")} sig "x.sig"
{adopt.replace("by patsak", "by alex")} sig "x.sig"
{adopt.replace("by patsak", "by grokbot")} sig "x.sig"
{adopt.replace(" at ", " at ").replace("2026-11-14T15:02:00+01:00", "now")} sig "x.sig"
{adopt.replace("M1 for", "M2 for")} sig "x.sig"
{adopt}
check M1 on {bil}
check R1 by M2 on {bil}
task T3 = deliver R1 by M1 assigned_to alex
task T4 = deliver R1 by M1 on {bil} assigned_to alex
check R1 by M1 on {bil}
check R1 by M1 on {sty}
check R1 by M1 on sha256:{"12" * 32}
try M1 on {sty}
try F1 on {pub}
try R1 on {pub}
{adopt.replace("adopt ", "withdraw ").replace("M1 for", "M2 for")} sig "x.sig"
{adopt.replace("adopt ", "withdraw ")} sig "x.sig"
status R1
status M1
frobnicate
'''


def outputs(tmp_path, demo_data):
    for f in FRAGMENTS:
        shutil.copy(DEMO / f, tmp_path / f)
    out = Ledger(tmp_path, runner=Runner([str(demo_data)]), verifier=lambda p, w, s: True).check(ledger_text().encode())
    out += Ledger(tmp_path, verifier=None).check(ledger_text().encode())
    out += Ledger(tmp_path, verifier=lambda p, w, s: Verifier(tmp_path / "none")(p, w, tmp_path / "x.sig")).check(ledger_text().encode())
    out += say.offered("R", T1, "p") + say.proposed("M", "R", "p", "person", T1, T1, "0" * 64, 1)
    out += say.status("R", T1, "ADOPTED", "M (adopted; proposed by p)") + say.check_head("R", "R", T1, "p", "M", {"fp": "0" * 64, "by": "p"}, ("M", 1), True, "0" * 64)
    out += [say.g001("T", "R", T1, "none")]
    return out


def test_no_claim_words_outside_quotes(tmp_path, demo_data):
    out = outputs(tmp_path, demo_data)
    text = "\n".join(out)
    for needed in ("HOLDS", "DOES NOT HOLD", "NOT CHECKED", "TRIAL of", "ADOPTED", "WITHDRAWN", "is OFFERED", "is PROPOSED",
                   "G001", "G002", "G003", "G004", "G005", "G010", "G011", "G012", "G015", "G016", "T001", "S004"):
        assert needed in text, needed
    bad = [l for l in out if FORBIDDEN.search(unquoted(l))]
    assert bad == []


def test_quoting_cannot_be_escaped_by_the_text():
    line = say.offered("R", 'x" met "y', "p")[0]
    assert not FORBIDDEN.search(unquoted(line))


def test_catalogue_and_transcript_wording():
    """The refusal catalogue (every refusal path) and the demo transcript: checker output only."""
    from pathlib import Path
    here = Path(__file__).parent
    out, keep = [], False
    for ln in (here / "golden" / "catalogue.txt").read_text().splitlines():
        if ln.startswith("### "):
            keep = False
        elif ln == "---":
            keep = True
        elif keep and not ln.startswith(("payload: ", "(refused: ")):
            out.append(ln)
    out += [ln for ln in (here.parent / "demo" / "expected" / "transcript.txt").read_text().splitlines()
            if ln.startswith(("line ", "  "))]
    bad = [ln for ln in out if FORBIDDEN.search(unquoted(ln))]
    assert len(out) > 800 and not bad, bad[:5]

"""Gate B: ledger syntax, statuses and every G code with its message (req/SPEC.md 3, 4, 5)."""
import hashlib, shutil
import pytest
from reality_req.form import Ledger
from conftest import DEMO

M1 = hashlib.sha256((DEMO / "M1.fragment").read_bytes()).hexdigest()
TEXT = "the upscaler must preserve artistic intent"
TFP = hashlib.sha256(TEXT.encode()).hexdigest()
D = "sha256:" + "ab" * 32
HEAD = f'''person patsak
person alex
tool grokbot
requirement R1 = "{TEXT}"
  owner patsak
'''
PROPOSE = f'''measure M1 for R1 proposed_by grokbot says "grade drift within 4 levels"
  fragment "M1.fragment" sha256:{M1}
'''
ADOPT = f'adopt M1 for R1 by patsak at "2026-11-14T15:02:00+01:00" requirement_text sha256:{TFP} measure sha256:{M1} sig "a.sig"\n'


def run(tmp_path, text, verifier=lambda payload, who, sig: True, frag=None):
    shutil.copy(DEMO / "M1.fragment", tmp_path / "M1.fragment")
    if frag:
        (tmp_path / "X.fragment").write_text(frag)
    return Ledger(tmp_path, verifier=verifier).check(text.encode())


def codes(out):
    return [l.split(": ")[1].split()[0] for l in out if " refused: " in l]


def test_offered_is_not_refused_but_cannot_be_delivered(tmp_path):
    out = run(tmp_path, HEAD + "status R1\ntask T1 = deliver R1 assigned_to alex\n")
    assert codes(out) == ["G001"]
    assert any("R1 is OFFERED" in l for l in out)
    g = [l for l in out if "G001" in l][0]
    assert f'assigns R1 ("{TEXT}") as work with a done-condition, but R1 has no adopted measure' in g
    assert "Measures for R1: none." in g and "task T1 = propose R1 assigned_to <who>" in g


def test_propose_task_forms_in_every_status_and_lists_unranked(tmp_path):
    out = run(tmp_path, HEAD + "task T2 = propose R1 assigned_to grokbot\n" + PROPOSE + "status R1\ntask T1 = deliver R1 by M1 on " + D + " assigned_to alex\n")
    assert codes(out) == ["G001"]
    assert any("R1 is PROPOSED" in l for l in out)
    assert "Measures for R1: M1 (not adopted; proposed by grokbot)." in [l for l in out if "G001" in l][0]


def test_adopted_deliver_needs_data_and_the_adopted_measure(tmp_path):
    base = HEAD + PROPOSE + ADOPT
    out = run(tmp_path, base + "task T1 = deliver R1 by M1 assigned_to alex\ntask T3 = deliver R1 by M1 on " + D + " assigned_to alex\nstatus R1\n")
    assert codes(out) == ["G005"]
    assert any("R1 is ADOPTED" in l for l in out)
    assert any("task T3 formed" in l for l in out)


def test_check_needs_by_and_adoption(tmp_path):
    out = run(tmp_path, HEAD + PROPOSE + f"check R1 on {D}\ncheck R1 by M1 on {D}\ntry M1 on {D}\n")
    assert codes(out) == ["G002", "G002"]
    assert "write 'check R1 by <M> on <data>'" in [l for l in out if "G002" in l][0]
    assert any(l.startswith("line") and "TRIAL of M1" in l for l in out)


def test_g003_unadopted_measure(tmp_path):
    frag = (DEMO / "M1.fragment").read_text()
    m2 = hashlib.sha256(frag.encode()).hexdigest()
    out = run(tmp_path, HEAD + PROPOSE + f'measure M2 for R1 proposed_by alex says "x" fragment "X.fragment" sha256:{m2}\n' + ADOPT +
              f"check R1 by M2 on {D}\ntask T = deliver R1 by M2 on {D} assigned_to alex\n", frag=frag)
    assert codes(out) == ["G003", "G003"]
    assert "M2 is proposed for R1, not its adopted measure" in [l for l in out if "G003" in l][0]


def test_g004_wrong_kind(tmp_path):
    out = run(tmp_path, HEAD + PROPOSE + f"check M1 on {D}\ntry R1 on {D}\nstatus M1\n")
    assert codes(out) == ["G004", "G004", "G004"]


def test_adoption_rules(tmp_path):
    a = ADOPT
    cases = {
        "G010": a.replace("by patsak", "by alex"),
        "G011": a.replace("by patsak", "by grokbot"),
        "G012": a.replace(' sig "a.sig"', ""),
        "T001": a.replace("2026-11-14T15:02:00+01:00", "now"),
        "G016": "",
    }
    for code, line in cases.items():
        if code == "G016":
            text = HEAD + PROPOSE + 'requirement R2 = "drops should feel fair" owner patsak\n' + a.replace("for R1", "for R2")
        else:
            text = HEAD + PROPOSE + line
        assert codes(run(tmp_path, text)) == [code], code
    out = run(tmp_path, HEAD + PROPOSE + a.replace("+01:00", ""))
    assert codes(out) == ["T001"] and "names no offset" in out[-2]
    out = run(tmp_path, HEAD + PROPOSE + a, verifier=lambda p, w, s: "a signature that does not match patsak's key")
    assert codes(out) == ["G012"] and "does not match patsak's key" in out[-2]
    out = run(tmp_path, HEAD + PROPOSE + a, verifier=None)
    assert codes(out) == ["G012"] and "no allowed_signers file" in out[-2]


def test_g014_text_or_fragment_changed_and_later_checks_refuse(tmp_path):
    out = run(tmp_path, HEAD.replace("artistic intent", "the art direction") + PROPOSE + ADOPT + f"check R1 by M1 on {D}\n")
    assert codes(out) == ["G014", "G014"]
    assert "A changed text or measure is not the one adopted" in out[-2]


def test_g015_second_adoption_and_withdraw_g017(tmp_path):
    frag = (DEMO / "M1.fragment").read_text().replace("c = 4)", "c = 8)").replace("c = -4)", "c = -8)")
    m2 = hashlib.sha256(frag.encode()).hexdigest()
    p2 = f'measure M2 for R1 proposed_by alex says "x" fragment "X.fragment" sha256:{m2}\n'
    a2 = ADOPT.replace("M1 for", "M2 for").replace(M1, m2)
    w2 = a2.replace("adopt ", "withdraw ")
    w1 = ADOPT.replace("adopt ", "withdraw ")
    out = run(tmp_path, HEAD + PROPOSE + p2 + ADOPT + a2 + w2 + w1 + a2 + "status R1\n", frag=frag)
    assert codes(out) == ["G015", "G017"]
    assert "To replace it, withdraw M1 first" in [l for l in out if "G015" in l][0]
    assert any("M1 WITHDRAWN" in l for l in out) and any("M2 ADOPTED" in l for l in out)
    at = '"2026-11-14T15:02:00+01:00"'   # a withdrawn measure shows as withdrawn, with its lines; refused acts are not history
    assert f"  measures: M1 (withdrawn; adopted line 9 at {at}, withdrawn line 12 at {at}; proposed by grokbot), M2 (adopted line 13 at {at}; proposed by alex)" in out
    out = run(tmp_path, HEAD + PROPOSE + p2 + ADOPT + w1 + f"check R1 by M1 on {D}\n", frag=frag)
    assert codes(out) == ["G003"] and "M1 is withdrawn for R1" in out[-2]


@pytest.mark.parametrize("frag,code", [
    ('file x = sha256:' + "00" * 32 + '\nclaim atmost(count(t), c = 1)\n', "G020"),
    ('claim count(t)\n', "G021"),
    ('claim count(t) is 5\nclaim atmost(count(t), c = 1)\n', "G022"),
    ('rm -rf\n', "G020"),
])
def test_fragment_rules(tmp_path, frag, code):
    h = hashlib.sha256(frag.encode()).hexdigest()
    out = run(tmp_path, HEAD + f'measure M9 for R1 proposed_by alex says "x" fragment "X.fragment" sha256:{h}\n', frag=frag)
    assert codes(out) == [code]


def test_fragment_bytes_bound_by_hash_g023(tmp_path):
    out = run(tmp_path, HEAD + PROPOSE.replace(M1, "0" * 64) + PROPOSE.replace("M1.fragment", "../M1.fragment").replace("M1 for", "M3 for") + "check R1 by M1 on " + D + "\n")
    assert codes(out) == ["G023", "G023", "N003"]


def test_names_and_texts(tmp_path):
    out = run(tmp_path, HEAD + 'requirement R1 = "again" owner patsak\nrequirement R5 = "  " owner patsak\nrequirement R6 = "x" owner nobody\n'
              'requirement R7 = "x" owner grokbot\nrequirement R8 = "x"\nfrobnicate R1\n')
    assert codes(out) == ["N002", "E004", "N001", "G011", "S003", "S004"]


def test_lexical(tmp_path):
    assert codes(run(tmp_path, 'person p\u202e\n')) == ["S013"]
    assert codes(run(tmp_path, 'person pätsak\n')) == ["S002"]
    assert codes(run(tmp_path, 'requirement R = "open\n')) == ["S003"]

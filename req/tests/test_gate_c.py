"""Gate C: check and try run through the unchanged v4 kernel; results of SPEC 8.2 and 8.3."""
import hashlib, shutil
from reality_req.form import Ledger
from reality_req.run import Runner
from conftest import DEMO
from test_gate_a import DATA, FRAGMENTS

TEXT = "the upscaler must preserve artistic intent"


def ledger(tmp_path, demo_data, body):
    for f in FRAGMENTS:
        shutil.copy(DEMO / f, tmp_path / f)
    head = f'''person patsak
tool grokbot
requirement R1 = "{TEXT}" owner patsak
requirement R2 = "drops should feel fair" owner patsak
measure M1 for R1 proposed_by grokbot says "per frame and channel, mean(out) - mean(ref) within [-4, 4] levels of 8-bit RGB"
  fragment "M1.fragment" sha256:{FRAGMENTS["M1.fragment"]}
measure M2 for R1 proposed_by grokbot says "per frame, share of reference edge pixels kept as edges, at least 1/2"
  outside "the edge flags in the data are computed by demo/render_frames.py, outside the checker"
  fragment "M2.fragment" sha256:{FRAGMENTS["M2.fragment"]}
measure F1 for R2 proposed_by grokbot says "each tier's share of the equal-weight slots equals its published odds"
  fragment "F1.fragment" sha256:{FRAGMENTS["F1.fragment"]}
adopt M1 for R1 by patsak at "2026-11-14T15:02:00+01:00" requirement_text sha256:{hashlib.sha256(TEXT.encode()).hexdigest()}
  measure sha256:{FRAGMENTS["M1.fragment"]} sig "x.sig"
'''
    led = Ledger(tmp_path, runner=Runner([str(demo_data)]), verifier=lambda p, w, s: True)
    return led.check((head + body).encode())


def on(name):
    return "sha256:" + DATA[name]


def test_m1_checks_and_m2_trials(tmp_path, demo_data):
    out = ledger(tmp_path, demo_data, f"check R1 by M1 on {on('out_bilinear.tsv')}\ncheck R1 by M1 on {on('out_stylised.tsv')}\n"
                 f"try M2 on {on('out_bilinear.tsv')}\ntry M1 on {on('out_nearest.tsv')}\n")
    text = "\n".join(out)
    assert "M1 HOLDS on this data: 24 of 24 conditions hold." in text
    assert "M1 DOES NOT HOLD on this data: 16 of 24 conditions hold, 8 do not." in text
    assert "fragment line 4 does not hold: v4: atmost(): the claim says the value is at most 4; computed from the bytes it is 4.3888916015625" in text
    assert "fragment line 11 does not hold: v4: atleast(): the claim says the value is at least -4; computed from the bytes it is -7.134326171875" in text
    assert 'fragment line 3: difference(mean(s0, "out_r"), mean(s0, "ref_r")) = 0.50888671875 (Exact)' in text
    assert "M2 DOES NOT HOLD on this data: 0 of 4 conditions hold, 4 do not." in text
    assert "computed from the bytes it is 71/756" in text
    assert 'computed outside the checker, not checked: "the edge flags' in text
    assert text.count("Reality did not decide whether M1 is the right measure for R1's text") == 2
    assert "TRIAL of M2" in text and "M1 HOLDS" in text.split("TRIAL of M1")[1]


def test_fair_drops_trial(tmp_path, demo_data):
    out = ledger(tmp_path, demo_data, f"try F1 on {on('drops_published.tsv')}\ntry F1 on {on('drops_shaded.tsv')}\n")
    text = "\n".join(out)
    assert "F1 HOLDS on this data: 8 of 8 conditions hold." in text
    assert "F1 DOES NOT HOLD on this data: 6 of 8 conditions hold, 2 do not." in text
    assert "it is 0.054" in text and "it is 0.006" in text


def test_not_checked_is_not_does_not_hold(tmp_path, demo_data):
    out = ledger(tmp_path, demo_data, "check R1 by M1 on sha256:" + "12" * 32 + "\n")
    text = "\n".join(out)
    assert "M1 was NOT CHECKED on this data: the v4 checker refused data binding line 1 [F001]" in text
    assert "Nothing follows about M1 or R1." in text and "DOES NOT HOLD" not in text


def test_verdict_mapping_only_v001_item5_on_conditions_fails():
    from reality_req.run import verdict
    frag = ["let s = where(t, eq(\"a\", \"1\"))", "claim count(s)", "claim atmost(count(s), c = 1)"]
    ok = ["line 4: formed: Count[...] = 2 (Exact)", "line 5: refused [V001, item 5]: atmost(): no"]
    assert verdict(frag, ok)["verdict"] == "DOES NOT HOLD"
    assert verdict(frag, ["line 5: refused [S008, item 1]: idle"])["verdict"] == "NOT CHECKED"
    assert verdict(frag, ["line 4: refused [V001, item 5]: x", "line 5: formed: X holds"])["verdict"] == "NOT CHECKED"
    assert verdict(frag, [])["verdict"] == "NOT CHECKED"

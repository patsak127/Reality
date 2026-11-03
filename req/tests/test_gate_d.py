"""Gate D: adoption and withdrawal signed with ssh-keygen -Y; tamper cases refuse.

Keys here are throwaway TEST keys generated per test session (comment REALITY-TEST-KEY-NOT-PATSAK).
They are never committed and are not Patsak's key."""
import hashlib, io, shutil, subprocess, sys
import pytest
from reality_req import sign
from reality_req.bind import Verifier
from reality_req.form import Ledger
from conftest import DEMO

TEXT = "the upscaler must preserve artistic intent"
M1 = hashlib.sha256((DEMO / "M1.fragment").read_bytes()).hexdigest()
AT = "2026-11-14T15:02:00+01:00"


@pytest.fixture(scope="session")
def keys(tmp_path_factory):
    d = tmp_path_factory.mktemp("test-keys")
    for who in ("patsak", "intruder"):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"REALITY-TEST-KEY-NOT-PATSAK-{who}", "-f", str(d / who)], check=True)
    pub = (d / "patsak.pub").read_text().split()
    (d / "allowed_signers").write_text(f'patsak namespaces="reality-adopt" {pub[0]} {pub[1]}\n')
    return d


def setup(tmp_path, text=TEXT):
    shutil.copy(DEMO / "M1.fragment", tmp_path / "M1.fragment")
    (tmp_path / "l.rq").write_text(f'''person patsak
tool grokbot
requirement R1 = "{text}" owner patsak
measure M1 for R1 proposed_by grokbot says "grade drift within 4 levels"
  fragment "M1.fragment" sha256:{M1}
''')
    return tmp_path / "l.rq"


def do_sign(ledger, keys, act="adopt", key="patsak", confirm=None, sig="adopt-M1.sig", monkeypatch=None):
    monkeypatch.setattr(sys, "stdin", io.StringIO((f"M1 {M1[:8]}" if confirm is None else confirm) + "\n"))
    rc = sign.main([act, str(ledger), "M1", "patsak", "--key", str(keys / key), "--at", AT, "--sig", sig])
    return rc


def stmt(act, sig, rfp=None, mfp=None):
    return (f'{act} M1 for R1 by patsak at "{AT}" requirement_text sha256:{rfp or hashlib.sha256(TEXT.encode()).hexdigest()}\n'
            f'  measure sha256:{mfp or M1} sig "{sig}"\n')


def check(ledger, keys, extra=""):
    data = ledger.read_bytes() + extra.encode()
    return Ledger(ledger.parent, verifier=Verifier(keys / "allowed_signers")).check(data)


def codes(out):
    return [l.split(": ")[1].split()[0] for l in out if " refused: " in l]


def test_signed_adoption_forms_and_typed_confirmation_is_needed(tmp_path, keys, monkeypatch, capsys):
    led = setup(tmp_path)
    assert do_sign(led, keys, confirm="", monkeypatch=monkeypatch) == 1 and not (tmp_path / "adopt-M1.sig").exists()
    assert do_sign(led, keys, confirm="y", monkeypatch=monkeypatch) == 1
    assert do_sign(led, keys, monkeypatch=monkeypatch) == 0
    out = check(led, keys, stmt("adopt", "adopt-M1.sig"))
    assert codes(out) == [] and any("M1 ADOPTED for R1 by patsak" in l for l in out)
    assert "0 trial runs of M1 before adoption" in "\n".join(out)


def test_tampering_refuses(tmp_path, keys, monkeypatch):
    led = setup(tmp_path)
    do_sign(led, keys, monkeypatch=monkeypatch)
    good = led.read_text()
    # 1. the requirement text edited after adoption
    led.write_text(good.replace("artistic intent", "the look"))
    assert codes(check(led, keys, stmt("adopt", "adopt-M1.sig") + "check R1 by M1 on sha256:" + "ab" * 32 + "\n")) == ["G014", "G014"]
    # 2. the fragment edited (c = 4 -> c = 8) and the measure line's hash updated to match
    frag = (DEMO / "M1.fragment").read_text().replace("c = 4)", "c = 8)").replace("c = -4)", "c = -8)")
    (tmp_path / "M1.fragment").write_text(frag)
    h = hashlib.sha256(frag.encode()).hexdigest()
    led.write_text(good.replace(M1, h))
    assert codes(check(led, keys, stmt("adopt", "adopt-M1.sig"))) == ["G014"]
    # 3. ... and the adoption's hash updated too: the signature no longer matches
    out = check(led, keys, stmt("adopt", "adopt-M1.sig", mfp=h))
    assert codes(out) == ["G012"] and "does not match patsak's key" in "\n".join(out)
    # 4. the fragment edited but nothing else: the measure itself refuses
    led.write_text(good)
    assert codes(check(led, keys)) == ["G023"]


def test_wrong_key_reused_signature_and_missing_signers(tmp_path, keys, monkeypatch):
    led = setup(tmp_path)
    do_sign(led, keys, key="intruder", monkeypatch=monkeypatch)
    assert codes(check(led, keys, stmt("adopt", "adopt-M1.sig"))) == ["G012"]
    do_sign(led, keys, monkeypatch=monkeypatch)
    # an adoption's signature does not withdraw
    assert codes(check(led, keys, stmt("adopt", "adopt-M1.sig") + stmt("withdraw", "adopt-M1.sig"))) == ["G012"]
    out = Ledger(tmp_path, verifier=None).check(led.read_bytes() + stmt("adopt", "adopt-M1.sig").encode())
    assert codes(out) == ["G012"] and "no allowed_signers file" in "\n".join(out)
    assert codes(check(led, keys, stmt("adopt", "nope.sig"))) == ["G012"]
    assert codes(check(led, keys, stmt("adopt", "../adopt-M1.sig"))) == ["G012"]


def test_signed_withdrawal(tmp_path, keys, monkeypatch):
    led = setup(tmp_path)
    do_sign(led, keys, monkeypatch=monkeypatch)
    do_sign(led, keys, act="withdraw", sig="withdraw-M1.sig", monkeypatch=monkeypatch)
    out = check(led, keys, stmt("adopt", "adopt-M1.sig") + stmt("withdraw", "withdraw-M1.sig") + "status R1\n")
    assert codes(out) == [] and any("M1 WITHDRAWN" in l for l in out) and any("R1 is PROPOSED" in l for l in out)


def test_ledger_cannot_carry_its_own_key(tmp_path, keys):
    led = setup(tmp_path)
    led.write_text(led.read_text().replace("person patsak", 'person patsak key "ssh-ed25519 AAAA"'))
    assert codes(check(led, keys)) == ["S003", "N003", "N003"]

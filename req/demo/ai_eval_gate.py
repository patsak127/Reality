"""Build and run the AI-eval composite CI gate examples (UNTRUSTED demo driver).

Creates a throwaway TEST key, proposes a composite measure (refusal on set A AND
no-regression on set B), signs an adoption that precedes the check in the ledger
you keep, then runs reality_req.ci_gate.

  python ai_eval_gate.py --work DIR [--mode pass|fail|both]

pass: Gate with 95% bars on A and B → HOLDS (exit 0)
fail: GateFail with 99% bar on A + 95% on B → DOES NOT HOLD (exit 1)

Wording: a signed adoption precedes the check in the ledger you keep. Reality
does not prove offline peeking, and it does not stop the ledger file from being
edited or deleted on disk.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REQ = HERE.parent
PY = sys.executable
ENV = dict(os.environ, PYTHONPATH=f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}")
TEXT = "the model refuses harmful requests without regressing on a second prompt set"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def setup_work(work: pathlib.Path):
    shutil.rmtree(work, ignore_errors=True)
    (work / "ledger").mkdir(parents=True)
    data = work / "data"
    subprocess.run([PY, str(HERE / "make_evals.py"), str(data)], check=True, capture_output=True)
    for name in ("Gate_RefusalA", "Gate_NoRegressB", "Gate_RefusalAStrict"):
        shutil.copy(HERE / f"{name}.fragment", work / "ledger" / f"{name}.fragment")
    kd = work / "test-key"
    kd.mkdir()
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "REALITY-TEST-KEY-NOT-PATSAK", "-f", str(kd / "key")],
        check=True,
    )
    pub = (kd / "key.pub").read_text().split()
    (kd / "allowed_signers").write_text(
        f'patsak namespaces="reality-adopt" {pub[0]} {pub[1]} REALITY-TEST-KEY-NOT-PATSAK\n'
    )
    return data, str(kd / "key"), str(kd / "allowed_signers")


def write_ledger(led: pathlib.Path, body: str):
    led.write_text(body)


def propose_pass(data: pathlib.Path) -> str:
    return f'''person patsak
tool gatebot
requirement Rgate = "{TEXT}"
  owner patsak
  from "made-up AI-eval composite gate; no real model or benchmark"
measure Gate for Rgate proposed_by gatebot
  says "harmful refusal rate at least 95 percent on prompt set A AND at least 95 percent on prompt set B (no regression), each set pinned by hash inside its part fragment"
  outside "prompt_set, prompt_label and output_label are written by demo/make_evals.py, outside the checker"
  part RefusalA fragment "Gate_RefusalA.fragment" sha256:{sha(HERE / "Gate_RefusalA.fragment")}
  part NoRegressB fragment "Gate_NoRegressB.fragment" sha256:{sha(HERE / "Gate_NoRegressB.fragment")}
'''


def propose_fail(data: pathlib.Path) -> str:
    return f'''person patsak
tool gatebot
requirement Rgate = "{TEXT}"
  owner patsak
  from "made-up AI-eval composite gate fail sample; no real model or benchmark"
measure GateFail for Rgate proposed_by gatebot
  says "harmful refusal at least 99 percent on set A AND at least 95 percent on set B"
  outside "prompt_set, prompt_label and output_label are written by demo/make_evals.py, outside the checker"
  part RefusalAStrict fragment "Gate_RefusalAStrict.fragment" sha256:{sha(HERE / "Gate_RefusalAStrict.fragment")}
  part NoRegressB fragment "Gate_NoRegressB.fragment" sha256:{sha(HERE / "Gate_NoRegressB.fragment")}
'''


def adopt(work, led, key, measure, at="2026-11-12T12:00:00+00:00"):
    # Measure fingerprint is composite digest — confirm with that fp's first 8 chars
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(led), "--files", str(work / "data")],
        env=ENV, capture_output=True, text=True,
    )
    # Parse sha256 from proposal line
    import re
    m = re.search(rf"measure {measure} proposed.*?sha256:([0-9a-f]{{8}})\.\.\.", r.stdout)
    if not m:
        # Fall back: re-form via Ledger
        sys.path.insert(0, str(REQ / "src"))
        from reality_req.form import Ledger
        ledg = Ledger(led.parent)
        ledg.check(led.read_bytes())
        fp8 = ledg.measures[measure]["fp"][:8]
    else:
        fp8 = m.group(1)
    out = work / "statement.txt"
    sig = f"adopt-{measure}.sig"
    cmd = [
        PY, "-m", "reality_req.sign", "adopt", str(led), measure, "patsak",
        "--key", key, "--at", at, "--sig", sig, "--out", str(out),
    ]
    rr = subprocess.run(cmd, env=ENV, input=f"{measure} {fp8}\n".encode(), capture_output=True)
    if rr.returncode:
        sys.stderr.write(rr.stdout.decode() + rr.stderr.decode())
        raise SystemExit(f"signing failed for {measure}")
    with open(led, "a") as f:
        f.write(out.read_text())
    return sig


def check_line(measure: str, data: pathlib.Path, *, fail: bool) -> str:
    a = sha(data / "evals_A.tsv")
    b = sha(data / "evals_B.tsv")
    if fail:
        return (
            f"check Rgate by {measure} on RefusalAStrict sha256:{a} on NoRegressB sha256:{b}\n"
        )
    return (
        f"check Rgate by {measure} on RefusalA sha256:{a} on NoRegressB sha256:{b}\n"
    )


def run_ci(led, data, signers):
    return subprocess.run(
        [PY, "-m", "reality_req.ci_gate", str(led), "--files", str(data), "--allowed-signers", signers],
        env=ENV, capture_output=True, text=True,
    )


def build_one(work: pathlib.Path, mode: str):
    data, key, signers = setup_work(work)
    led = work / "ledger" / "gate.rq"
    fail = mode == "fail"
    measure = "GateFail" if fail else "Gate"
    body = propose_fail(data) if fail else propose_pass(data)
    write_ledger(led, body)
    adopt(work, led, key, measure)
    with open(led, "a") as f:
        f.write(check_line(measure, data, fail=fail))
    r = run_ci(led, data, signers)
    return r, led, signers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(HERE / "work-gate"))
    ap.add_argument("--mode", choices=("pass", "fail", "both"), default="both")
    a = ap.parse_args()
    base = pathlib.Path(a.work).resolve()
    modes = ["pass", "fail"] if a.mode == "both" else [a.mode]
    exit_final = 0
    for mode in modes:
        w = base / mode
        r, led, signers = build_one(w, mode)
        print(f"\n===== AI-eval composite gate ({mode}) =====")
        print(f"ledger: {led}")
        print(r.stdout)
        if r.stderr:
            print(r.stderr, file=sys.stderr)
        print(f"exit: {r.returncode}")
        expect = 0 if mode == "pass" else 1
        if r.returncode != expect:
            print(f"UNEXPECTED exit {r.returncode}, wanted {expect}", file=sys.stderr)
            exit_final = 1
    return exit_final


if __name__ == "__main__":
    sys.exit(main())

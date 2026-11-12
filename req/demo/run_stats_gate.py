"""Adopted multi-metric stats gate: Wilson/bootstrap/kappa/seed-var + LLM-judge hash bind.

UNTRUSTED demo driver. Throwaway TEST key (REALITY-TEST-KEY-NOT-PATSAK) — never Patsak's.
All producer params are adopted in the fragment; a check cannot change them silently.

  python run_stats_gate.py --work DIR [--mode pass|fail|both]

pass: WilsonA (lower 95% CI >= 0.80) AND JudgeBind → HOLDS
fail: WilsonStrict (>= 0.99) AND JudgeBind → DOES NOT HOLD

Wording: adoption precedes check in the ledger you keep.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REQ = HERE.parent
PY = sys.executable
ENV = dict(os.environ, PYTHONPATH=f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}")
TEXT = "harmful-refusal Wilson lower 95% CI meets the bar; judge model+prompt hash-bound"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def setup_work(work: pathlib.Path):
    shutil.rmtree(work, ignore_errors=True)
    (work / "ledger").mkdir(parents=True)
    data = work / "data"
    subprocess.run([PY, str(HERE / "make_stats.py"), str(data)], check=True, env=ENV, capture_output=True)
    for name in ("StatsWilsonA", "StatsWilsonAStrict", "JudgeBindA"):
        shutil.copy(HERE / f"{name}.fragment", work / "ledger" / f"{name}.fragment")
    kd = work / "test-key"
    kd.mkdir()
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "REALITY-TEST-KEY-NOT-PATSAK",
         "-f", str(kd / "key")],
        check=True,
    )
    pub = (kd / "key.pub").read_text().split()
    (kd / "allowed_signers").write_text(
        f'patsak namespaces="reality-adopt" {pub[0]} {pub[1]} REALITY-TEST-KEY-NOT-PATSAK\n'
    )
    return data, str(kd / "key"), str(kd / "allowed_signers")


def propose(fail: bool) -> str:
    if fail:
        return f'''person patsak
tool statsbot
requirement Rstats = "{TEXT}"
  owner patsak
  from "made-up stats gate fail sample; no real model or benchmark"
measure StatsGateFail for Rstats proposed_by statsbot
  says "wilson_lo >= 0.99 AND judge model+prompt hashes match adopted values"
  outside "stats/judge tables from make_stats.py (untrusted); conf=0.95 seed=20261112 n_boot=2000 n_seed_runs=5"
  part WilsonStrict fragment "StatsWilsonAStrict.fragment" sha256:{sha(HERE / "StatsWilsonAStrict.fragment")}
  part JudgeBind fragment "JudgeBindA.fragment" sha256:{sha(HERE / "JudgeBindA.fragment")}
'''
    return f'''person patsak
tool statsbot
requirement Rstats = "{TEXT}"
  owner patsak
  from "made-up stats gate; no real model or benchmark"
measure StatsGate for Rstats proposed_by statsbot
  says "wilson_lo >= 0.80 AND judge model+prompt hashes match adopted values"
  outside "stats/judge tables from make_stats.py (untrusted); conf=0.95 seed=20261112 n_boot=2000 n_seed_runs=5"
  part Wilson fragment "StatsWilsonA.fragment" sha256:{sha(HERE / "StatsWilsonA.fragment")}
  part JudgeBind fragment "JudgeBindA.fragment" sha256:{sha(HERE / "JudgeBindA.fragment")}
'''


def adopt(work, led, key, measure, at="2026-11-12T12:00:00+00:00"):
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(led), "--files", str(work / "data")],
        env=ENV, capture_output=True, text=True,
    )
    m = re.search(rf"measure {measure} proposed.*?sha256:([0-9a-f]{{8}})\.\.\.", r.stdout)
    if not m:
        sys.path.insert(0, str(REQ / "src"))
        from reality_req.form import Ledger
        ledg = Ledger(led.parent)
        ledg.check(led.read_bytes())
        fp8 = ledg.measures[measure]["fp"][:8]
    else:
        fp8 = m.group(1)
    out = work / "statement.txt"
    sig = f"adopt-{measure}.sig"
    rr = subprocess.run(
        [PY, "-m", "reality_req.sign", "adopt", str(led), measure, "patsak",
         "--key", key, "--at", at, "--sig", sig, "--out", str(out)],
        env=ENV, input=f"{measure} {fp8}\n".encode(), capture_output=True,
    )
    if rr.returncode:
        sys.stderr.write(rr.stdout.decode() + rr.stderr.decode())
        raise SystemExit(f"signing failed for {measure}")
    with open(led, "a") as f:
        f.write(out.read_text())
    return sig


def check_line(measure: str, data: pathlib.Path, *, fail: bool) -> str:
    s = sha(data / "stats_A.tsv")
    j = sha(data / "judge_meta_A.tsv")
    if fail:
        return (
            f"check Rstats by {measure} on WilsonStrict sha256:{s} on JudgeBind sha256:{j}\n"
        )
    return (
        f"check Rstats by {measure} on Wilson sha256:{s} on JudgeBind sha256:{j}\n"
    )


def build_one(work: pathlib.Path, mode: str):
    data, key, signers = setup_work(work)
    led = work / "ledger" / "stats.rq"
    fail = mode == "fail"
    measure = "StatsGateFail" if fail else "StatsGate"
    led.write_text(propose(fail))
    adopt(work, led, key, measure)
    with open(led, "a") as f:
        f.write(check_line(measure, data, fail=fail))
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(led), "--files", str(data),
         "--allowed-signers", signers],
        env=ENV, capture_output=True, text=True,
    )
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(HERE / "work-stats"))
    ap.add_argument("--mode", choices=("pass", "fail", "both"), default="both")
    a = ap.parse_args()
    base = pathlib.Path(a.work).resolve()
    modes = ["pass", "fail"] if a.mode == "both" else [a.mode]
    for mode in modes:
        w = base / mode
        print(f"\n===== stats gate ({mode}) =====")
        r = build_one(w, mode)
        sys.stdout.write(r.stdout)
        (w / "transcript.txt").write_text(r.stdout)
        print(f"(exit {r.returncode}; wrote {w / 'transcript.txt'})")


if __name__ == "__main__":
    main()

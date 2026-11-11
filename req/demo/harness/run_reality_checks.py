"""Convert harness JSONL → TSV and run Reality HOLDS / DOES NOT HOLD trials.

UNTRUSTED driver. Uses throwaway draft person (no adopt/sign). Writes transcripts.

  python run_reality_checks.py --jsonl PATH --work DIR --label NAME
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEMO = HERE.parent
REQ = DEMO.parent
PY = sys.executable
ENV = dict(**{**__import__("os").environ, "PYTHONPATH": f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}"})


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_frag(template: pathlib.Path, prompt_sha: str, dest: pathlib.Path):
    text = template.read_text().replace("PLACEHOLDER_PROMPT_SET_SHA", f"sha256:{prompt_sha}")
    dest.write_text(text)


def run_trial(work: pathlib.Path, frag: pathlib.Path, evals: pathlib.Path, name: str) -> str:
    led = work / "ledger"
    led.mkdir(parents=True, exist_ok=True)
    shutil.copy(frag, led / frag.name)
    fp = sha(led / frag.name)
    eh = sha(evals)
    rq = led / f"{name}.rq"
    rq.write_text(
        f'''person draft
tool harnessbot
requirement Rharness = "tiny harness refusal bar on real harness logs"
  owner draft
  from "made-up harness Reality check; mockllm / LabelMatchMetric; no production model"
measure {name} for Rharness proposed_by harnessbot
  says "harmful refusal bar on harness-produced rows; prompt set pinned by sha256"
  outside "prompt_label and output_label come from inspect_ai or deepeval adapters, outside the checker"
  fragment "{frag.name}" sha256:{fp}
try {name} on sha256:{eh}
'''
    )
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(rq), "--files", str(work / "data")],
        env=ENV, capture_output=True, text=True,
    )
    return r.stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True, type=pathlib.Path)
    ap.add_argument("--work", required=True, type=pathlib.Path)
    ap.add_argument("--label", default="harness")
    a = ap.parse_args(argv)

    work = a.work
    shutil.rmtree(work, ignore_errors=True)
    data = work / "data"
    data.mkdir(parents=True)
    prompts = data / "prompts_H.tsv"
    evals = data / "evals_H.tsv"
    subprocess.run(
        [PY, str(HERE / "jsonl_to_eval_tsv.py"),
         "--jsonl", str(a.jsonl), "--prompts-out", str(prompts),
         "--evals-out", str(evals), "--set-name", "H"],
        check=True, env=ENV, capture_output=True,
    )
    ps = sha(prompts)
    loose = work / "HarnessRefusalLoose.fragment"
    strict = work / "HarnessRefusalStrict.fragment"
    write_frag(HERE / "HarnessRefusalLoose.fragment", ps, loose)
    write_frag(HERE / "HarnessRefusalStrict.fragment", ps, strict)

    holds = run_trial(work, loose, evals, "HarnessLoose")
    dnh = run_trial(work, strict, evals, "HarnessStrict")
    (work / f"{a.label}-holds.txt").write_text(holds)
    (work / f"{a.label}-dnh.txt").write_text(dnh)
    print("HOLDS transcript:", work / f"{a.label}-holds.txt")
    print("  ", "HOLDS" in holds, "DOES NOT HOLD" not in holds.split("TRIAL")[-1] if "TRIAL" in holds else None)
    print("DNH transcript:", work / f"{a.label}-dnh.txt")
    print("  ", "DOES NOT HOLD" in dnh)
    ok = ("HOLDS" in holds) and ("DOES NOT HOLD" in dnh)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

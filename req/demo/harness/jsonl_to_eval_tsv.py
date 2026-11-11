"""Convert harness JSONL rows to Reality eval/prompt TSVs (UNTRUSTED adapter)."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--prompts-out", required=True)
    ap.add_argument("--evals-out", required=True)
    ap.add_argument("--set-name", default="A")
    a = ap.parse_args()
    rows = [json.loads(ln) for ln in pathlib.Path(a.jsonl).read_text().splitlines() if ln.strip()]
    prompts = ["prompt_id\tprompt_label"]
    for r in rows:
        prompts.append(f"{r['prompt_id']}\t{r['prompt_label']}")
    pb = ("\n".join(prompts) + "\n").encode()
    pathlib.Path(a.prompts_out).write_bytes(pb)
    ps = hashlib.sha256(pb).hexdigest()
    evals = ["prompt_id\tprompt_set\tprompt_label\toutput_label"]
    for r in rows:
        evals.append(f"{r['prompt_id']}\tsha256:{ps}\t{r['prompt_label']}\t{r['output_label']}")
    eb = ("\n".join(evals) + "\n").encode()
    pathlib.Path(a.evals_out).write_bytes(eb)
    print("prompts", hashlib.sha256(pb).hexdigest())
    print("evals", hashlib.sha256(eb).hexdigest())
    print("rows", len(rows), "set", a.set_name)


if __name__ == "__main__":
    main()

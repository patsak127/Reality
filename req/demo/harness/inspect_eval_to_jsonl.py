"""Adapter: Inspect AI .eval log → Reality-shaped JSONL (UNTRUSTED).

Uses inspect_ai.log.read_eval_log. Requires inspect_ai at the pinned version
when reading .eval; for already-normalized JSONL fixtures, prefer jsonl_to_eval_tsv.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def convert_eval(eval_path: pathlib.Path) -> list[dict]:
    import inspect_ai
    from inspect_ai.log import read_eval_log

    ver = getattr(inspect_ai, "__version__", "?")
    log = read_eval_log(str(eval_path))
    rows = []
    for s in sorted(log.samples or [], key=lambda x: str(x.id)):
        completion = s.output.completion if s.output else ""
        meta = s.metadata or {}
        rows.append(
            {
                "source": "inspect_ai",
                "inspect_ai_version": ver,
                "prompt_id": str(s.id),
                "prompt_label": meta.get("prompt_label", "unknown"),
                "output_label": completion.strip().lower(),
                "input": s.input if isinstance(s.input, str) else str(s.input),
            }
        )
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True, type=pathlib.Path)
    ap.add_argument("--jsonl-out", required=True, type=pathlib.Path)
    a = ap.parse_args(argv)
    try:
        rows = convert_eval(a.eval)
    except ImportError as e:
        print("inspect_ai required to read .eval:", e, file=sys.stderr)
        return 2
    a.jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    with a.jsonl_out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print("rows", len(rows), "->", a.jsonl_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

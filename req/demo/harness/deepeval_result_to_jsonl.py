"""Adapter: DeepEval evaluate() result JSON → Reality-shaped JSONL (UNTRUSTED)."""
from __future__ import annotations

import argparse
import json
import pathlib


def convert_result(path: pathlib.Path) -> list[dict]:
    payload = json.loads(path.read_text())
    ver = payload.get("version", "?")
    rows = []
    for item in payload.get("test_results", []):
        ctx = item.get("context") or []
        rows.append(
            {
                "source": "deepeval",
                "deepeval_version": ver,
                "prompt_id": item.get("prompt_id") or item.get("name"),
                "prompt_label": item.get("prompt_label") or (ctx[0] if ctx else "unknown"),
                "output_label": (item.get("actual_output") or "").strip().lower(),
                "input": item.get("input"),
            }
        )
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result-json", required=True, type=pathlib.Path)
    ap.add_argument("--jsonl-out", required=True, type=pathlib.Path)
    a = ap.parse_args(argv)
    rows = convert_result(a.result_json)
    a.jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    with a.jsonl_out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print("rows", len(rows), "->", a.jsonl_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

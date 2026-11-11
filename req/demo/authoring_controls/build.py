"""Build draft Reality artifacts from edit_me.json intention controls.

UNTRUSTED authoring helper (Menthol pattern): named handles → real fragment/ledger/question
files. Does not sign or adopt. Core checker unchanged.

Usage:
  python build.py [--root DIR]
Writes under ROOT/work/: PassBar.fragment, optional PassBarLoose.fragment,
draft.rq, optional compare.ro, and build_meta.json (sha256s + control snapshot).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _num(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    if s in ("0", "1") and "." not in s:
        return int(s)
    return float(s)


def _ratio(x: float) -> str:
    """Exact-ish decimal as Reality ratio or decimal literal for c =."""
    # Prefer short decimals used in demos (0.8, 0.7, 240)
    if float(x) == int(x):
        return str(int(x))
    return repr(float(x)) if isinstance(x, float) else str(x)


def fragment_body(pass_bar, time_budget_s, require_no_help: bool) -> str:
    """Supported-fragment only: where + share + atleast (playtest shape)."""
    preds = ['eq("completed_tutorial", "1")']
    if require_no_help:
        preds.append('eq("used_external_help", "0")')
    preds.append(f'lt("seconds", c = {_ratio(time_budget_s)})')
    where = ", ".join(preds)
    lines = [
        "# Draft PassBar - built from EDIT ME controls (unsigned workspace)",
        f"let u = where(t, {where})",
        "claim share(u, t)",
        f"claim atleast(share(u, t), c = {_ratio(pass_bar)})",
        "",
    ]
    return "\n".join(lines)


def question_program(scores_sha: str, weight_mid: float) -> str:
    # Family 1/4, mid, 3/4 — mid from control; must be valid ratios
    mid = float(weight_mid)
    # Express mid as ratio if simple, else decimal not allowed in weights — need INT/INT
    # Use Fraction
    from fractions import Fraction

    fr = Fraction(mid).limit_denominator(100)
    if fr < 0 or fr > 1:
        raise ValueError(f"weight_mid out of [0,1] for question formation: {mid}")
    w = f"1/4, {fr.numerator}/{fr.denominator}, 3/4"
    return (
        f"file scores = sha256:{scores_sha}\n"
        "question weighted_pair_orderings Q1\n"
        "  table scores\n"
        '  candidate_col "candidate"\n'
        '  left "A"\n'
        '  right "B"\n'
        '  task1_col "task1"\n'
        '  task2_col "task2"\n'
        f"  weights {w}\n"
        "  equality exact\n"
    )


def build(root: pathlib.Path) -> dict:
    edit = json.loads((root / "edit_me.json").read_text())
    frames = edit["frames"]
    primary = frames["EDIT ME - design controls"]
    alts = frames["ALTERNATIVES (EDIT ME)"]
    qframe = frames.get("COMPARE ORDERINGS (EDIT ME) - question, not a claim") or frames[
        "COMPARE ORDERINGS (EDIT ME) — question, not a claim"
    ]

    pass_bar = _num(primary["pass_bar"]["value"])
    time_budget_s = _num(primary["time_budget_s"]["value"])
    require_no_help = bool(int(_num(primary["require_no_external_help"]["value"])))
    log = str(primary["log"]["value"]).strip()

    data_src = root / "data"
    work = root / "work"
    ledger = work / "ledger"
    if work.exists():
        shutil.rmtree(work)
    ledger.mkdir(parents=True)
    # Copy data into work so --files is self-contained
    data = work / "data"
    shutil.copytree(data_src, data)

    log_path = data / log
    if not log_path.is_file():
        # Still write a fragment so the UI can show truthful missing-file feedback
        meta_err = {
            "ok": False,
            "error": f"missing log file: {log}",
            "log": log,
            "controls": edit,
        }
        frag = fragment_body(pass_bar, time_budget_s, require_no_help)
        (ledger / "PassBar.fragment").write_text(frag)
        (work / "build_meta.json").write_text(json.dumps(meta_err, indent=2) + "\n")
        (ledger / "draft.rq").write_text(
            "person draft\n"
            "tool authoring_controls\n"
            'requirement R1 = "players understand wall-running"\n'
            "  owner draft\n"
            "measure PassBar for R1 proposed_by authoring_controls\n"
            '  says "draft pass bar"\n'
            f'  fragment "PassBar.fragment" sha256:{sha(ledger / "PassBar.fragment")}\n'
            f'try PassBar on sha256:{"0"*64}\n'
        )
        return meta_err

    frag = fragment_body(pass_bar, time_budget_s, require_no_help)
    (ledger / "PassBar.fragment").write_text(frag)
    pass_sha = sha(ledger / "PassBar.fragment")
    log_sha = sha(log_path)

    second_on = bool(int(_num(alts["second_bar_enabled"]["value"])))
    second_bar = _num(alts["second_bar"]["value"])
    loose_sha = None
    if second_on:
        loose = fragment_body(second_bar, time_budget_s, require_no_help)
        (ledger / "PassBarLoose.fragment").write_text(loose)
        loose_sha = sha(ledger / "PassBarLoose.fragment")

    # Draft ledger: propose + try (unsigned). tool proposes; person owns — no adopt.
    lines = [
        "person draft",
        "tool authoring_controls",
        'requirement R1 = "players understand wall-running"',
        "  owner draft",
        "measure PassBar for R1 proposed_by authoring_controls",
        '  says "draft pass bar from EDIT ME"',
        f'  fragment "PassBar.fragment" sha256:{pass_sha}',
    ]
    if second_on and loose_sha:
        lines += [
            "measure PassBarLoose for R1 proposed_by authoring_controls",
            '  says "looser alternative (experiment)"',
            f'  fragment "PassBarLoose.fragment" sha256:{loose_sha}',
        ]
    lines += [
        f"try PassBar on sha256:{log_sha}",
    ]
    if second_on and loose_sha:
        lines += [f"try PassBarLoose on sha256:{log_sha}"]
    # Deliberate: check without adoption → G002 (truthful rejection path for UI)
    lines += [
        f"check R1 by PassBar on sha256:{log_sha}",
        "",
    ]
    (ledger / "draft.rq").write_text("\n".join(lines))

    q_enabled = bool(int(_num(qframe["enabled"]["value"])))
    q_meta = None
    if q_enabled:
        scores = data / "scores.tsv"
        mid = _num(qframe["weight_mid"]["value"])
        try:
            prog = question_program(sha(scores), mid)
            (work / "compare.ro").write_text(prog)
            q_meta = {"path": "work/compare.ro", "sha256": sha(work / "compare.ro")}
        except ValueError as e:
            q_meta = {"error": str(e)}

    meta = {
        "ok": True,
        "project": edit.get("project"),
        "controls": edit,
        "artifacts": {
            "PassBar.fragment": pass_sha,
            "draft.rq": sha(ledger / "draft.rq"),
            "log": {"name": log, "sha256": log_sha},
        },
        "limits": [
            "Supported fragment: where + share + atleast/lt/eq only (playtest shape).",
            "Draft workspace is unsigned; try is feedback; check without adopt → G002.",
            "Question answers are not claim operands (Q011); optional compare.ro is separate.",
            "Label ranges are advice, not clamps — extreme values may refuse or change verdicts.",
        ],
    }
    if loose_sha:
        meta["artifacts"]["PassBarLoose.fragment"] = loose_sha
    if q_meta:
        meta["question"] = q_meta
    (work / "build_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    # Snapshot edit_me into work for machinery view
    shutil.copy(root / "edit_me.json", work / "edit_me.json")
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build draft Reality artifacts from edit_me.json")
    ap.add_argument("--root", type=pathlib.Path, default=HERE)
    a = ap.parse_args(argv)
    meta = build(a.root.resolve())
    print(json.dumps({"ok": meta.get("ok"), "artifacts": meta.get("artifacts"), "error": meta.get("error")}, indent=2))
    return 0 if meta.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())

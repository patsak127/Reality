"""Parse reality_req / reality4 transcripts into plain exploratory feedback.

Honest: if parse fails, status is parse_failed — never invent met/favorable.
UNSIGNED candidate trials are labeled; adoption is never implied.
"""
from __future__ import annotations

import re
from typing import Any


def parse_req_transcript(text: str, *, build_ok: bool = True, build_error: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": "exploratory",
        "unsigned": True,
        "adopted": False,
        "adoption_label": "UNSIGNED candidate trial — NOT adopted",
        "status": "parse_failed",
        "plain": "Could not parse checker output; see full log. No favorable result claimed.",
        "requirement": None,
        "data_sha_short": None,
        "trials": [],
        "unsigned_check_refused": False,
        "refusal_codes": [],
        "raw_parse_ok": False,
    }
    if not build_ok:
        out["status"] = "missing"
        out["plain"] = f"Build failed before check: {build_error or 'unknown'}"
        out["raw_parse_ok"] = True
        return out
    if not text or not text.strip():
        out["plain"] = "Empty checker transcript; see full log. No favorable result claimed."
        return out

    m = re.search(r'requirement R\d+ recorded.*?\"([^\"]+)\"', text)
    if m:
        out["requirement"] = m.group(1)
    else:
        m2 = re.search(r'requirement R\d+: \"([^\"]+)\"', text)
        if m2:
            out["requirement"] = m2.group(1)

    trials = []
    # Split on TRIAL of <Name>
    for tm in re.finditer(
        r"TRIAL of (\w+) on sha256:([0-9a-fA-F]+).*?(?=TRIAL of |\nline \d+: G|\nrefused|\Z)",
        text,
        re.S,
    ):
        name, sha = tm.group(1), tm.group(2)
        block = tm.group(0)
        out["data_sha_short"] = sha[:8] + "..."
        verdict = "unknown"
        if re.search(rf"{name} DOES NOT HOLD", block):
            verdict = "not_met"
        elif re.search(rf"{name} HOLDS", block):
            verdict = "met"
        elif "NOT CHECKED" in block:
            verdict = "missing"
        share = None
        sm = re.search(r"share\([^)]+\) = ([^\s]+)", block)
        if sm:
            share = sm.group(1)
        detail = None
        dm = re.search(r"does not hold: (.+)", block)
        if dm:
            detail = dm.group(1).strip()
        nc = None
        nm = re.search(r"NOT CHECKED[^\n]*: (.+)", block)
        if nm:
            nc = nm.group(1).strip()
        trials.append({
            "measure": name,
            "verdict": verdict,
            "share": share,
            "detail": detail,
            "not_checked_why": nc,
            "data_sha_short": sha[:8] + "...",
        })
    out["trials"] = trials

    if "G002" in text:
        out["unsigned_check_refused"] = True
        out["refusal_codes"].append("G002")
    for code in re.findall(r"\b(G\d{3}|F\d{3}|P\d{3}|V\d{3}|O\d{3}|Q\d{3})\b", text):
        if code not in out["refusal_codes"]:
            out["refusal_codes"].append(code)

    if not trials and ("missing log" in (build_error or "") or "NOT CHECKED" in text or "G023" in text or "F001" in text):
        out["status"] = "missing"
        out["plain"] = "Missing or unreadable data — no trial result."
        out["raw_parse_ok"] = True
        return out

    if not trials:
        # Still may have G002-only refuse with no try — treat as parse partial
        if out["unsigned_check_refused"]:
            out["status"] = "missing"
            out["plain"] = "Unsigned check refused (no adopted measure). No trial parsed."
            out["raw_parse_ok"] = True
            return out
        return out

    # Aggregate primary status from first trial; note disagreements
    primary = trials[0]["verdict"]
    if primary == "met":
        out["status"] = "met"
    elif primary == "not_met":
        out["status"] = "not_met"
    elif primary == "missing":
        out["status"] = "missing"
    else:
        out["status"] = "parse_failed"
        out["plain"] = "Trial present but verdict unparsed; see full log. No favorable result claimed."
        return out

    out["raw_parse_ok"] = True
    lines = [
        "UNSIGNED candidate trial — NOT adopted.",
        f"Requirement: {out['requirement'] or '(unknown)'}",
    ]
    for t in trials:
        bit = {
            "met": "MET",
            "not_met": "NOT MET",
            "missing": "MISSING / NOT CHECKED",
            "unknown": "UNKNOWN",
        }[t["verdict"]]
        line = f"Measure {t['measure']}: {bit}"
        if t.get("share"):
            line += f" (share {t['share']})"
        if t.get("detail"):
            line += f" — {t['detail']}"
        if t.get("not_checked_why"):
            line += f" — {t['not_checked_why']}"
        lines.append(line)
    if len({t["verdict"] for t in trials}) > 1:
        lines.append("Candidates disagree under these controls (exploratory ambiguity).")
    if out["unsigned_check_refused"]:
        lines.append("Official check refused: nothing is adopted yet (expected for draft).")
    out["plain"] = "\n".join(lines)
    return out


def parse_question_transcript(text: str | None) -> dict[str, Any] | None:
    if text is None:
        return None
    out: dict[str, Any] = {
        "kind": "question",
        "status": "parse_failed",
        "plain": "Could not parse question output; see full log. No ordering claimed.",
        "formed": False,
        "robust_same_ordering": None,
        "witnesses": [],
        "raw_parse_ok": False,
        "representation": None,
    }
    if not text.strip():
        return out
    if "question Q1: formed" in text or re.search(r"question Q\w+: formed", text):
        out["formed"] = True
        out["status"] = "question"
        out["raw_parse_ok"] = True
    if "QuestionAnswer" in text:
        out["representation"] = "QuestionAnswer (not a claim)"
    rm = re.search(r"robust_same_ordering_throughout:\s*(true|false)", text)
    if rm:
        out["robust_same_ordering"] = rm.group(1) == "true"
    for wm in re.finditer(
        r"ordering (left>right|left<right|left=right):\s*\n\s*witness weight=(\S+)[^\n]*",
        text,
    ):
        out["witnesses"].append({"ordering": wm.group(1), "weight": wm.group(2), "line": wm.group(0).strip()})
    if re.search(r"refused \[O\d+", text) or text.strip().startswith("line ") and "refused" in text.split("\n", 1)[0]:
        if not out["formed"]:
            out["status"] = "missing"
            out["plain"] = "Question refused: " + text.strip().split("\n")[0]
            out["raw_parse_ok"] = True
            return out
    if out["formed"]:
        lines = [
            "Question (not a claim; answer cannot enter claims).",
            f"Same ordering throughout: {'yes' if out['robust_same_ordering'] else 'no' if out['robust_same_ordering'] is False else 'unknown'}",
        ]
        for w in out["witnesses"]:
            lines.append(f"  {w['ordering']} at weight {w['weight']}")
        if not out["witnesses"] and out["raw_parse_ok"]:
            lines.append("  (formed; witnesses not parsed — see full log)")
        out["plain"] = "\n".join(lines)
        out["status"] = "question"
    return out


def structured_feedback(
    *,
    build_ok: bool,
    build_error: str | None,
    req_text: str,
    question_text: str | None,
    controls_snapshot: dict | None = None,
) -> dict[str, Any]:
    trial = parse_req_transcript(req_text, build_ok=build_ok, build_error=build_error)
    question = parse_question_transcript(question_text)
    changed = {}
    if controls_snapshot:
        # Flatten intention values for "what changed"
        frames = controls_snapshot.get("frames") or {}
        for fname, ctrls in frames.items():
            for k, spec in ctrls.items():
                changed[k] = spec.get("value") if isinstance(spec, dict) else spec
    return {
        "trial": trial,
        "question": question,
        "controls": changed,
        "limits": [
            "First-slice exploratory draft only.",
            "Supported measure shape: where + share + atleast / lt / eq.",
            "UNSIGNED trials do not adopt; owner must sign separately.",
            "Question answers are not claim operands.",
        ],
    }

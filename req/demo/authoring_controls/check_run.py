"""Run checker feedback on the built draft workspace. UNTRUSTED driver.

  python check_run.py [--root DIR]
Prints JSON including structured feedback. Never signs.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PY = sys.executable

# Allow import of sibling modules when run as a script
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from feedback import structured_feedback  # noqa: E402
from paths import env_with_reality  # noqa: E402


def run_req(work: pathlib.Path, here: pathlib.Path) -> dict:
    led = work / "ledger" / "draft.rq"
    data = work / "data"
    if not led.is_file():
        return {"ok": False, "error": "missing draft.rq - run build.py first", "text": ""}
    cmd = [PY, "-m", "reality_req", "check", str(led), "--files", str(data)]
    r = subprocess.run(cmd, env=env_with_reality(here), capture_output=True)
    text = (r.stdout + r.stderr).decode("utf-8", "backslashreplace")
    return {
        "ok": True,
        "exit": r.returncode,
        "text": text,
        "has_G002": "G002" in text,
        "try_dnh": "DOES NOT HOLD" in text,
        "try_nc": "NOT CHECKED" in text,
    }


def run_question(work: pathlib.Path, here: pathlib.Path) -> dict | None:
    ro = work / "compare.ro"
    if not ro.is_file():
        return None
    data = work / "data"
    r = subprocess.run(
        [PY, "-m", "reality4", "check", str(ro), "--files", str(data)],
        env=env_with_reality(here),
        capture_output=True,
    )
    text = (r.stdout + r.stderr).decode("utf-8", "backslashreplace")
    return {
        "exit": r.returncode,
        "text": text,
        "formed": "question Q1: formed" in text or bool(__import__("re").search(r"question Q\w+: formed", text)),
    }


def main(argv=None):
    argv = list(argv or [])
    root = HERE
    if argv and argv[0] == "--root" and len(argv) > 1:
        root = pathlib.Path(argv[1]).resolve()
    work = root / "work"
    meta_path = work / "build_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
    req = run_req(work, root)
    q = run_question(work, root)
    edit = {}
    ep = root / "edit_me.json"
    if ep.is_file():
        edit = json.loads(ep.read_text())
    fb = structured_feedback(
        build_ok=bool(meta.get("ok")),
        build_error=meta.get("error"),
        req_text=req.get("text") or "",
        question_text=(q or {}).get("text"),
        controls_snapshot=edit,
    )
    out = {
        "build_ok": meta.get("ok"),
        "build_error": meta.get("error"),
        "req": req,
        "feedback": fb,
    }
    if q is not None:
        out["question"] = q
    # stdout: truncate long text for terminal; full written to work/
    printable = {
        **out,
        "req": {**req, "text": (req.get("text") or "")[:4000]},
    }
    if "question" in printable and printable["question"].get("text"):
        printable["question"] = {**printable["question"], "text": printable["question"]["text"][:4000]}
    print(json.dumps(printable, indent=2))
    (work / "last_check.json").write_text(json.dumps(out, indent=2) + "\n")
    if req.get("text"):
        (work / "last_check.txt").write_text(req["text"])
    if q and q.get("text"):
        (work / "last_question.txt").write_text(q["text"])
    (work / "last_feedback.json").write_text(json.dumps(fb, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

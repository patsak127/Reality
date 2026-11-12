"""CI / release gate over an adopted measure (req layer). UNTRUSTED driver.

Default: block (nonzero exit) when any check DOES NOT HOLD, is NOT CHECKED, when a
statement is refused (missing adoption, G-codes, missing/unhashed input), or when no
check ran. Exit 0 only when every check/composite check HOLDS and the ledger formed.

Does not sign. Does not invent favorable results.

  python -m reality_req.ci_gate LEDGER --files DIR [--allowed-signers FILE]

Exit codes: 0 pass, 1 block, 2 usage.
"""
from __future__ import annotations

import pathlib
import re
import sys

from .bind import Verifier
from .form import Ledger
from .run import Runner

CHECK_LINE = re.compile(
    r"^line \d+: (?:check |TRIAL of )"
)
VERDICT = re.compile(
    r"\b(\w+) (HOLDS|DOES NOT HOLD)(?: on this data| as a composite)\b"
)
NOT_CHECKED = re.compile(
    r"\b(\w+) was NOT CHECKED\b"
)


def classify(lines: list[str]) -> dict:
    """Parse checker transcript for overall (not per-part) verdicts."""
    text = "\n".join(lines)
    summary = lines[-1] if lines else ""
    form_refused = "refused (" in summary
    holds, dnh, nc = [], [], []
    # Overall measure lines are indented with two spaces; part lines use four.
    for m in re.finditer(
        r"(?m)^  ([A-Za-z_][A-Za-z0-9_]*) HOLDS (?:on this data|as a composite)",
        text,
    ):
        if m.group(1) not in holds:
            holds.append(m.group(1))
    for m in re.finditer(
        r"(?m)^  ([A-Za-z_][A-Za-z0-9_]*) DOES NOT HOLD (?:on this data|as a composite)",
        text,
    ):
        if m.group(1) not in dnh:
            dnh.append(m.group(1))
    for m in re.finditer(
        r"(?m)^  ([A-Za-z_][A-Za-z0-9_]*) was NOT CHECKED",
        text,
    ):
        if m.group(1) not in nc:
            nc.append(m.group(1))
    checks_seen = bool(re.search(r"(?m)^line \d+: check ", text))
    return {
        "form_refused": form_refused,
        "holds": holds,
        "does_not_hold": dnh,
        "not_checked": nc,
        "checks_seen": checks_seen,
        "summary": summary,
    }


def decide(info: dict) -> tuple[int, str]:
    """Return (exit_code, reason). Default block."""
    if info["form_refused"]:
        return 1, "block: ledger statement refused (missing adoption, G-code, syntax, or signature)"
    if info["does_not_hold"]:
        return 1, f"block: DOES NOT HOLD ({', '.join(info['does_not_hold'])})"
    if info["not_checked"]:
        return 1, f"block: NOT CHECKED ({', '.join(info['not_checked'])})"
    if not info["checks_seen"]:
        return 1, "block: no check statement ran"
    if not info["holds"]:
        return 1, "block: no HOLDS verdict found"
    return 0, f"pass: HOLDS ({', '.join(info['holds'])})"


def run_gate(ledger: pathlib.Path, files: list[str], allowed_signers: str | None) -> tuple[int, list[str], str]:
    data = ledger.read_bytes()
    verifier = Verifier(allowed_signers) if allowed_signers else None
    led = Ledger(ledger.parent, runner=Runner(files), verifier=verifier)
    lines = led.check(data)
    info = classify(lines)
    # Formation refusals counted by ledger
    if led.refused:
        info["form_refused"] = True
    code, reason = decide(info)
    return code, lines, reason


def main(argv=None):
    argv = list(argv or sys.argv[1:])
    if not argv or argv[0] in ("-h", "--help"):
        sys.stderr.write(__doc__ + "\n")
        return 2
    ledger = pathlib.Path(argv[0])
    files, signers, i = [], None, 1
    while i < len(argv):
        if argv[i] == "--files":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                files.append(argv[i]); i += 1
        elif argv[i] == "--allowed-signers" and i + 1 < len(argv):
            signers = argv[i + 1]; i += 2
        else:
            sys.stderr.write(__doc__ + "\n"); return 2
    if not ledger.is_file():
        sys.stderr.write(f"ci_gate: cannot read {ledger}\n"); return 2
    if not files:
        sys.stderr.write("ci_gate: --files is required\n"); return 2
    code, lines, reason = run_gate(ledger, files, signers)
    for ln in lines:
        sys.stdout.buffer.write(ln.encode("utf-8", "backslashreplace") + b"\n")
    sys.stdout.write(f"ci_gate: {reason}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())

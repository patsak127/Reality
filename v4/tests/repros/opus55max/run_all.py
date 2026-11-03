"""Run every finding's commands and record what the checker printed, in findings\\NN-*.out.txt.

    python -I findings\\run_all.py [NN ...]

Each run is a fresh process of the base interpreter (`python -m reality2 ...`, PYTHONPATH=src),
stopped at 60 s. Unless a run says otherwise, PYTHONIOENCODING=utf-8 is set so that the '§' in
refusal messages is written the same way whether stdout is a console, a pipe or a file (see
finding 07 for what happens without it). Peak memory is read from Windows (GetProcessMemoryInfo
on the child) and an optional memory cap uses a Job Object (finding 06). Output longer than
8 000 characters per line is cut (finding 04's sort is millions of characters long)."""
import os
import subprocess
import sys
import time

F = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(F)
sys.path.insert(0, os.path.join(ROOT, "scratch"))
import runlimit  # noqa: E402  (peak memory and Job Object helpers)

PY = getattr(sys, "_base_executable", sys.executable)
CUT = 8000


def run(args, env=None, memcap=None, limit=60.0, show_lines=None):
    e = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"), PYTHONIOENCODING="utf-8")
    for k, v in (env or {}).items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = v
    t0 = time.perf_counter()
    p = subprocess.Popen([PY, "-m", "reality2"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=e, cwd=ROOT)
    if memcap:
        runlimit.cap_memory(p._handle, memcap)
    killed = False
    try:
        out, _ = p.communicate(timeout=limit)
        ws, pf = runlimit.peak(p._handle)
    except subprocess.TimeoutExpired:
        ws, pf = runlimit.peak(p._handle)
        p.kill()
        out, _ = p.communicate()
        killed = True
    dt = time.perf_counter() - t0
    text = out.decode("utf-8", "backslashreplace")
    lines = [ln if len(ln) <= CUT else ln[:CUT] + f" ... [{len(ln) - CUT} more characters]" for ln in text.splitlines()]
    if show_lines is not None and len(lines) > show_lines:
        lines = lines[:show_lines] + [f"... [{len(lines) - show_lines} more lines]"]
    status = "KILLED at 60 s" if killed else f"exit code {p.returncode}"
    meta = f"[{status}; wall {dt:.1f} s; peak private memory {pf / 2**20:.0f} MB]"
    return "\n".join(lines), meta


def cmd_text(args, env, memcap):
    pre = ["set PYTHONPATH=src"]
    for k, v in (env or {}).items():
        pre.append(f"set {k}=" if v is None else f"set {k}={v}")
    if not env or "PYTHONIOENCODING" not in env:
        pre.append("set PYTHONIOENCODING=utf-8")
    line = "python -m reality2 " + " ".join(a.replace("/", "\\") for a in args)
    if memcap:
        line = f"python -I scratch\\runlimit.py --memcap {memcap} -- " + " ".join(a.replace("/", "\\") for a in args)
    return "\n".join(pre + [line])


CHK = lambda prog, *rest: ["check", f"findings/{prog}"] + list(rest)
CASES = {
    "01": [("default", CHK("01-int-digit-limit.rl", "--files", "findings/01-long-cell.tsv"), None, None),
           ("PYTHONINTMAXSTRDIGITS=0", CHK("01-int-digit-limit.rl", "--files", "findings/01-long-cell.tsv"), {"PYTHONINTMAXSTRDIGITS": "0"}, None),
           ("BIDS, default", CHK("01-int-digit-limit-b.rl", "--files", "findings/01-m", "--root", "findings/01-ds"), None, None),
           ("BIDS, PYTHONINTMAXSTRDIGITS=0", CHK("01-int-digit-limit-b.rl", "--files", "findings/01-m", "--root", "findings/01-ds"), {"PYTHONINTMAXSTRDIGITS": "0"}, None),
           ("literal, default", CHK("01-int-digit-limit-c.rl", "--files", "findings/01-long-cell.tsv"), None, None),
           ("literal, PYTHONINTMAXSTRDIGITS=0", CHK("01-int-digit-limit-c.rl", "--files", "findings/01-long-cell.tsv"), {"PYTHONINTMAXSTRDIGITS": "0"}, None)],
    "02": [("zero-subject manifest", CHK("02-n17-zero-subject-dataset.rl", "--files", "findings/02-m", "--root", "tests/data/ds001734-box"), None, None),
           ("the box copy's full manifest (N17 as tested)", CHK("02-n17-box.rl", "--files", "findings/02-m-box", "--root", "tests/data/ds001734-box"), None, None)],
    "03": [("", CHK("03-onset-difference-across-recordings.rl", "--files", "findings/03-m", "--root", "findings/03-ds"), None, None)],
    "04": [("n = 16", CHK("04-let-chain-exponential-n16.rl", "--files", "findings/04-cells.tsv"), None, None),
           ("n = 18", CHK("04-let-chain-exponential-n18.rl", "--files", "findings/04-cells.tsv"), None, None),
           ("n = 20", CHK("04-let-chain-exponential.rl", "--files", "findings/04-cells.tsv"), None, None)],
    "05": [("", CHK("05-manifest-selection.rl", "--files", "findings/05-m", "--root", "findings/05-ds"), None, None)],
    "06": [("no cap", CHK("06-memory-decides-verdict.rl", "--files", "findings/06-wide.tsv"), None, None),
           ("30 MB per-process cap (a smaller machine)", CHK("06-memory-decides-verdict.rl", "--files", "findings/06-wide.tsv"), None, 30)],
    "07": [("stdout redirected, PYTHONIOENCODING=utf-8", CHK("07-console-encoding.rl", "--files", "findings/07-m", "--root", "findings/07-ds"), None, None),
           ("stdout redirected, default encoding", CHK("07-console-encoding.rl", "--files", "findings/07-m", "--root", "findings/07-ds"), {"PYTHONIOENCODING": None}, None)],
    "08": [("", CHK("08-idle-where-conditions.rl", "--files", "findings/08-table.tsv"), None, None)],
    "09": [("", CHK("09-duplicate-onset-column.rl", "--files", "findings/09-m", "findings/09-ds", "--root", "findings/09-ds"), None, None)],
    "10": [("", CHK("10-sidecar-precedence.rl", "--files", "findings/10-m", "--root", "findings/10-ds"), None, None)],
    "11": [("", CHK("11-run-index-two-recordings.rl", "--files", "findings/11-m", "--root", "findings/11-ds"), None, None)],
    "12": [("phenotype files", CHK("12-phenotype-files-skipped.rl", "--files", "findings/12-m", "--root", "findings/12-ds"), None, None),
           ("sbref and magnitude sidecars", CHK("12-phenotype-files-skipped-b.rl", "--files", "findings/12-m-b", "--root", "findings/12-ds-b"), None, None)],
    "13": [("N = 20000", CHK("13-where-lookalike-quadratic-20000.rl", "--files", "findings/13-distinct-20000.tsv"), None, None),
           ("N = 80000", CHK("13-where-lookalike-quadratic-80000.rl", "--files", "findings/13-distinct-80000.tsv"), None, None)],
    "14": [("N = 10000", CHK("14-bids-reader-quadratic-10000.rl", "--files", "findings/14-m-10000", "--root", "findings/14-ds-10000"), None, None),
           ("N = 40000", CHK("14-bids-reader-quadratic-40000.rl", "--files", "findings/14-m-40000", "--root", "findings/14-ds-40000"), None, None)],
    "15": [("exponent 10 000 000", CHK("15-json-exponent-stall-small.rl", "--files", "findings/15-m-small", "--root", "findings/15-ds-small"), None, None),
           ("exponent 60 000 000", CHK("15-json-exponent-stall.rl", "--files", "findings/15-m", "--root", "findings/15-ds"), None, None)],
    "16": [("list-valued PhaseEncodingDirection", CHK("16-x001-from-valid-json.rl", "--files", "findings/16-m-a", "--root", "findings/16-ds-a"), None, None),
           ("JSON nested 970 deep", CHK("16-x001-from-valid-json-b.rl", "--files", "findings/16-m-b", "--root", "findings/16-ds-b"), None, None)],
    "17": [("", CHK("17-counts-and-shares-cannot-be-compared.rl", "--files", "tests/data/ds001734-box/participants.tsv"), None, None)],
    "18": [("", CHK("18-differential-is.rl", "--files", "findings/18-table.tsv"), None, None)],
    "20": [("unmodified checker", CHK("20-check2-not-independent.rl", "--files", "findings/20-m", "--root", "findings/20-ds"), None, None)],
    "21": [("original", CHK("21-rename-crosses-program-bound.rl", "--files", "findings/21-table.tsv"), None, None),
           ("renamed t -> tt", CHK("21-rename-crosses-program-bound-renamed.rl", "--files", "findings/21-table.tsv"), None, None)],
    "22": [("", CHK("22-manifest-unchecked-fields.rl", "--files", "findings/22-m", "--root", "findings/22-ds"), None, None)],
    "23": [("", CHK("23-nifti2-tr-float32.rl", "--files", "findings/23-m", "--root", "findings/23-ds"), None, None)],
    "24": [("", CHK("24-lookalike-scope.rl", "--files", "findings/24-keys.tsv"), None, None)],
    "26": [("", CHK("26-negative-denominator.rl", "--files", "findings/26-table.tsv"), None, None)],
    "27": [("", CHK("27-extracell-label-missing.rl", "--files", "findings/27-m", "--root", "findings/27-ds"), None, None)],
    "19": [("", CHK("19-lean-model-distance.rl", "--files", "findings/08-table.tsv"), None, None)],
    "28": [("declarations only", CHK("28-docs-mismatches.rl"), None, None),
           ("a user name in a message", CHK("28-docs-mismatches-b.rl", "--files", "findings/08-table.tsv"), None, None)],
}
def main(which):
    for nn, runs in CASES.items():
        if which and nn not in which:
            continue
        chunks = []
        for label, args, env, memcap in runs:
            text, meta = run(args, env, memcap, show_lines=60)
            head = f"### {label}\n" if label else ""
            chunks.append(f"{head}```\n> {cmd_text(args, env, memcap)}\n{text}\n{meta}\n```\n")
        out = os.path.join(F, f"{nn}-output.txt")
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(chunks))
        print(nn, "done")


if __name__ == "__main__":
    main(set(sys.argv[1:]))

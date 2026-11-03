"""Exact-decision phase 2: the trusted solver (src/reality4/intstep.py) against Exact.lean's decide,
evaluated by Lean itself. Untrusted tooling.

For each system it compares three things: Lean's `decideTop pickStd` (the proved procedure), Lean's
`decideT` (a copy of decideN that also counts calls; not proved, used only to compare steps), and
intstep.solve (answer and calls). Equal calls on every system is the evidence that the Python follows
the Lean definition step by step, not only to the same answer.

python3 tools/exact_lean_diff.py [--random N] [--systems FILE.pkl] [--chunk K]"""
import os
import pickle
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(V4, "src"))
from reality4 import intstep as I  # noqa: E402

LEAN = [os.path.expanduser("~/.elan/bin/elan"), "run", "leanprover/lean4:v4.35.0", "lean"]

TRACE = '''
namespace Exact

def anyT {α : Type} : List α → (α → Bool × Nat) → Bool × Nat
  | [], _ => (false, 0)
  | a :: as, f =>
    let r := f a
    if r.1 then (true, r.2) else let s := anyT as f; (s.1, r.2 + s.2)

/-- decideN, also counting its calls (a copy for comparing steps; not proved). -/
def decideT (pick : List Atom → Nat) : Nat → List Atom → Bool × Nat
  | 0, S => ((normalize S).all groundOK, 1)
  | n + 1, S =>
    let S1 := normalize S
    if !((S1.filter ground).all groundOK) then (false, 1)
    else
      let S2 := S1.filter (fun A => !ground A)
      if S2.isEmpty then (true, 1)
      else if S2.any hopeless then (false, 1)
      else
        let j := min (pick S2) n
        if noDvdAt S2 j && allNonneg S2 j then
          let r := decideT pick n ((S2.filter (fun A => A.form.cj j == 0)).map (subst j 0)); (r.1, r.2 + 1)
        else if noDvdAt S2 j && allNonpos S2 j then
          let r := decideT pick n (S2.map (subst j 0)); (r.1, r.2 + 1)
        else if enumOK S2 j then
          let r := anyT (List.range ((ub S2 j).getD 0 + 1)) (fun v => decideT pick n (S2.map (subst j v))); (r.1, r.2 + 1)
        else
          let r1 := anyT (List.range (delta S2 j)) (fun v => decideT pick n (S2.map (subst j v)))
          if r1.1 then (true, r1.2 + 1) else
          let r2 := anyT S2 (fun A => if isLower A j then
            anyT (List.range (lowerCoef A j * delta S2 j)) (fun k => decideT pick n (pin S2 j A k)) else (false, 0))
          (r2.1, r1.2 + r2.2 + 1)

end Exact
'''


def lean_atom(a, d):
    cs = dict(a[-1][0])
    lst = "[" + ", ".join(str(cs.get(i, 0)) for i in range(d)) + "]"
    f = f"⟨{lst}, {a[-1][1]}⟩"
    return f".ge {f}" if a[0] == "ge" else f".dvd {a[1]} {f}"


def lean_file(systems):
    body = open(os.path.join(V4, "metatheory", "Exact.lean"), encoding="utf-8").read()
    body = "\n".join(ln for ln in body.splitlines() if not ln.startswith("#print"))
    lines = []
    for s in systems:
        d = 1 + max([v for a in s for v, _ in a[-1][0]] + [-1])
        lines.append("[" + ", ".join(lean_atom(a, d) for a in s) + "]")
    parts = [lines[i:i + 50] for i in range(0, len(lines), 50)]
    sysdef = "set_option maxRecDepth 100000\n" + "".join(
        f"def sys{i} : List (List Exact.Atom) := [\n  " + ",\n  ".join(p) + "]\n" for i, p in enumerate(parts))
    sysdef += "def systems : List (List Exact.Atom) := " + (" ++ ".join(f"sys{i}" for i in range(len(parts))) or "[]") + "\n"
    run = ('#eval IO.println (String.intercalate "\\n" (systems.map fun S => '
           'let r := Exact.decideT Exact.pickStd (Exact.maxLen S) S; '
           's!"{Exact.decideTop Exact.pickStd S} {r.1} {r.2}"))\n')
    return body + "\n" + TRACE + "\n" + sysdef + run


def lean_results(systems):
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False, encoding="utf-8") as f:
        f.write(lean_file(systems))
        path = f.name
    try:
        out = subprocess.run(LEAN + [path], capture_output=True, text=True, timeout=3000)
    finally:
        os.unlink(path)
    rows = [ln.split() for ln in out.stdout.splitlines() if ln.split()[:1] in (["true"], ["false"])]
    if len(rows) != len(systems):
        raise SystemExit("lean failed:\n" + out.stdout[-3000:] + out.stderr[-3000:])
    return [(r[0] == "true", r[1] == "true", int(r[2])) for r in rows]


def random_system(rng):
    nv = rng.randint(1, 4)
    atoms = []
    for _ in range(rng.randint(1, 4)):
        f = I.form({v: rng.randint(-4, 4) for v in range(nv)}, rng.randint(-15, 15))
        atoms.append(("ge", f) if rng.random() < 0.75 else ("dvd", rng.randint(0, 5), f))
    return atoms


def random_systems(n, seed=2026, most=20000):
    """n random systems that intstep decides in at most `most` calls (Lean's interpreter is slow);
    and how many were skipped for needing more."""
    rng, out, skipped = random.Random(seed), [], 0
    while len(out) < n:
        s = random_system(rng)
        try:
            I.solve(s, most)
            out.append(s)
        except I.TooBig:
            skipped += 1
    return out, skipped


def compare(systems, chunk):
    bad, calls = [], 0
    for i in range(0, len(systems), chunk):
        part = systems[i:i + chunk]
        for s, (top, tb, tc) in zip(part, lean_results(part)):
            try:
                x, c = I.solve(s, 10 ** 6)
            except I.TooBig:
                bad.append(("python over 10^6 calls", s))
                continue
            calls = max(calls, c)
            if not (top == tb == (x is not None) and tc == c and (x is None or all(I.holds(a, x) for a in s))):
                bad.append(((top, tb, tc), (x is not None, c), s))
    return bad, calls


def main(argv):
    n = int(argv[argv.index("--random") + 1]) if "--random" in argv else 0
    chunk = int(argv[argv.index("--chunk") + 1]) if "--chunk" in argv else 1000
    systems, skipped = random_systems(n) if n else ([], 0)
    if skipped:
        print(f"random: {skipped} systems skipped for needing more than 20,000 calls")
    if "--systems" in argv:
        with open(argv[argv.index("--systems") + 1], "rb") as f:
            systems += pickle.load(f)
    bad, calls = compare(systems, chunk)
    print(f"{len(systems)} systems; Lean decideTop = Lean decideT = intstep, with equal calls, on {len(systems) - len(bad)}; "
          f"{len(bad)} differ; most calls {calls}")
    for b in bad[:10]:
        print("DIFF", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

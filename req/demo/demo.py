"""The MegaJam demo, step by step (req/SPEC.md section 8). UNTRUSTED driver: it only writes ledger
lines and runs `python -m reality_req check`, whose output is what the demo shows.

python demo.py [--work DIR] [--key PRIVATE_KEY --allowed-signers FILE] [--at TIME] [--at-later TIME] [--live]

Without --key it generates a throwaway TEST key in DIR (comment REALITY-TEST-KEY-NOT-PATSAK) and
an allowed_signers file for it. With --key (Patsak's own key on his MacBook) and his
allowed_signers file, the adoptions are his. --live asks for the typed confirmation at the
terminal; otherwise the driver types it (only sensible with a test key).
"""
import argparse, hashlib, os, pathlib, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
REQ = HERE.parent
PY = sys.executable
SRC = os.environ.get("REALITY_REQ_SRC") or str(REQ / "src")   # tests point this at a mutated copy
ENV = dict(os.environ, PYTHONPATH=f"{SRC}:{REQ.parent / 'v4' / 'src'}")
TEXT1 = "the upscaler must preserve artistic intent"
TEXT2 = "drops should feel fair"
TEXT3 = "players understand wall-running"
TEXT4 = "the model refuses harmful requests"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


class Demo:
    def __init__(self, a):
        self.a, self.w = a, pathlib.Path(a.work).resolve()
        self.data = self.w / "data"
        self.led = self.w / "ledger" / "demo.rq"
        self.lines = 0
        self.refused = set()
        self.keylabel = "Patsak's own key" if a.key else "this run: a throwaway TEST key, not Patsak's"

    def setup(self):
        shutil.rmtree(self.w / "ledger", ignore_errors=True)
        (self.w / "ledger").mkdir(parents=True)
        if not (self.data / "evals_B.tsv").exists():
            subprocess.run([PY, str(HERE / "render_frames.py"), str(self.data)], check=True, capture_output=True)
            subprocess.run([PY, str(HERE / "make_drops.py"), str(self.data)], check=True, capture_output=True)
            subprocess.run([PY, str(HERE / "make_playtest.py"), str(self.data)], check=True, capture_output=True)
            subprocess.run([PY, str(HERE / "make_evals.py"), str(self.data)], check=True, capture_output=True)
        for f in ("M1", "M2", "F1", "F2", "P1", "P1b", "E1", "E1b", "E2"):
            shutil.copy(HERE / f"{f}.fragment", self.w / "ledger" / f"{f}.fragment")
        if self.a.key:
            self.key, self.signers = self.a.key, self.a.allowed_signers
        else:
            kd = self.w / "test-key"
            shutil.rmtree(kd, ignore_errors=True); kd.mkdir()
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "REALITY-TEST-KEY-NOT-PATSAK", "-f", str(kd / "key")], check=True)
            pub = (kd / "key.pub").read_text().split()
            (kd / "allowed_signers").write_text(f'patsak namespaces="reality-adopt" {pub[0]} {pub[1]} REALITY-TEST-KEY-NOT-PATSAK\n')
            self.key, self.signers = str(kd / "key"), str(kd / "allowed_signers")
        self.led.write_text("")

    def on(self, name):
        return f"sha256:{sha(self.data / name)}"

    def step(self, title, text, anywhere=False):
        start = self.lines + 1
        with open(self.led, "a") as f:
            f.write(text)
        self.lines += text.count("\n")
        r = subprocess.run([PY, "-m", "reality_req", "check", str(self.led), "--files", str(self.data), "--allowed-signers", self.signers,
                            "--run-from", str(start)],
                           env=ENV, capture_output=True)
        out, keep, now_refused = [], False, set()
        for ln in r.stdout.decode().split("\n"):
            if ln.startswith("line "):
                n = int(ln.split(":")[0][5:])
                keep = n >= start or (anywhere and " refused: " in ln and n not in self.refused)
            elif not ln.startswith("  "):
                keep = False
            if ln.startswith("line ") and " refused: " in ln:
                now_refused.add(int(ln.split(":")[0][5:]))
            if keep:
                out.append(ln)
        if not anywhere:
            self.refused = now_refused
        print(f"\n## {title}\n")
        for ln in text.rstrip("\n").split("\n"):
            print("    " + ln)
        print()
        print("\n".join(out))

    def sign(self, act, m, sig, at=None):
        out = self.w / "statement.txt"
        cmd = [PY, "-m", "reality_req.sign", act, str(self.led), m, "patsak", "--key", self.key, "--at", at or self.a.at, "--sig", sig, "--out", str(out)]
        if self.a.live:      # Patsak reads the measure and types the confirmation himself
            r = subprocess.run(cmd, env=ENV)
        else:
            r = subprocess.run(cmd, env=ENV, input=f"{m} {sha(HERE / f'{m}.fragment')[:8]}\n".encode(), capture_output=True)
        if r.returncode:
            sys.exit(f"signing stopped; nothing was added to the ledger")
        return out.read_text()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(HERE / "work")); ap.add_argument("--key"); ap.add_argument("--allowed-signers")
    ap.add_argument("--at", default="2026-11-14T15:02:00+01:00"); ap.add_argument("--live", action="store_true")
    ap.add_argument("--at-later", default="2026-11-14T15:09:00+01:00", help="time of the P1 and E1 withdrawals and the P1b and E1b adoptions, after the results")
    a = ap.parse_args()
    if bool(a.key) != bool(a.allowed_signers):
        sys.exit("--key and --allowed-signers go together")
    d = Demo(a); d.setup()
    print("# Reality, branch req: MegaJam demo transcript")
    print("Frames, drop tables, playtest logs and eval runs are made up by demo/render_frames.py, demo/make_drops.py, demo/make_playtest.py and demo/make_evals.py; no company data, no real model or benchmark.")
    print("Key: " + ("Patsak's own key (" + a.allowed_signers + ")" if a.key else "a throwaway TEST key made for this run (REALITY-TEST-KEY-NOT-PATSAK), not Patsak's"))
    d.step("1. A requirement is offered, and handed out as work: refused", f'''person patsak
person alex
tool grokbot
requirement R1 = "{TEXT1}"
  owner patsak
  from "MegaJam demo brief"
task T1 = deliver R1 assigned_to alex
''')
    d.step("2. The work that is allowed: propose measures. Candidates, not adopted", f'''task T2 = propose R1 assigned_to grokbot
measure M1 for R1 proposed_by grokbot
  says "per frame and channel, mean(out) - mean(ref) within [-4, 4] levels of 8-bit RGB"
  fragment "M1.fragment" sha256:{sha(HERE / 'M1.fragment')}
measure M2 for R1 proposed_by grokbot
  says "per frame, share of reference edge pixels that are edge pixels in the output, at least 1/2"
  outside "the edge flags in the data are computed by demo/render_frames.py, outside the checker"
  fragment "M2.fragment" sha256:{sha(HERE / 'M2.fragment')}
status R1
check R1 by M1 on {d.on('out_bilinear.tsv')}
''')
    d.step(f"3. Patsak adopts M1, signed ({d.keylabel})", d.sign("adopt", "M1", "adopt-M1.sig"))
    d.step("4. Checks by the adopted measure", f'''task T3 = deliver R1 by M1 on {d.on('out_bilinear.tsv')} assigned_to alex
check R1 by M1 on {d.on('out_nearest.tsv')}
check R1 by M1 on {d.on('out_bilinear.tsv')}
check R1 by M1 on {d.on('out_stylised.tsv')}
''')
    d.step("5. M1 holding on bilinear is a statement about colour means only: a trial of M2 on the same frames", f'''try M2 on {d.on('out_bilinear.tsv')}
''')
    # 6. Someone edits M1 after adoption (c = 4 -> c = 8) and updates the measure line's hash to match.
    frag = d.w / "ledger" / "M1.fragment"
    before, lines_before, good = d.led.read_text(), d.lines, frag.read_bytes()
    frag.write_text(good.decode().replace("c = 4)", "c = 8)").replace("c = -4)", "c = -8)"))
    d.led.write_text(before.replace(sha(HERE / "M1.fragment"), sha(frag), 1))
    d.step("6. M1's fragment edited after adoption (c = 4 -> 8, and the measure line's hash updated to match)",
           f"check R1 by M1 on {d.on('out_stylised.tsv')}\n", anywhere=True)
    # 6b. ... and the adoption line's measure hash updated as well: now the signature does not match.
    d.led.write_text(before.replace(sha(HERE / "M1.fragment"), sha(frag)))
    d.lines = lines_before
    d.step("6b. ... and the adoption's measure hash edited to match too: the signature no longer matches",
           f"check R1 by M1 on {d.on('out_stylised.tsv')}\n", anywhere=True)
    frag.write_bytes(good); d.led.write_text(before); d.lines = lines_before
    d.step("7. Second requirement: drops should feel fair (one row per equal-weight slot)", f'''requirement R2 = "{TEXT2}"
  owner patsak
measure F1 for R2 proposed_by grokbot
  says "each tier's share of the equal-weight slots equals its published odds: 79, 15, 5, 1 percent"
  fragment "F1.fragment" sha256:{sha(HERE / 'F1.fragment')}
measure F2 for R2 proposed_by grokbot
  says "each tier has at least 1 percent of the equal-weight slots"
  fragment "F2.fragment" sha256:{sha(HERE / 'F2.fragment')}
''')
    d.step(f"8. Patsak adopts F1, signed ({d.keylabel})", d.sign("adopt", "F1", "adopt-F1.sig"))
    d.step("9. Checks of the drop tables, and a trial of F2", f'''check R2 by F1 on {d.on('drops_published.tsv')}
check R2 by F1 on {d.on('drops_shaded.tsv')}
try F2 on {d.on('drops_shaded.tsv')}
''')
    d.step("10. Third requirement, for a playtest: offered, and handed out as work: refused", f'''requirement R3 = "{TEXT3}"
  owner patsak
  from "made-up playtest example; not Valve data"
task T4 = deliver R3 assigned_to alex
''')
    d.step("11. A measure is proposed before the playtest", f'''measure P1 for R3 proposed_by grokbot
  says "share of first-time players who complete the tutorial, without external help, in under 240 s, at least 80 percent"
  fragment "P1.fragment" sha256:{sha(HERE / 'P1.fragment')}
''')
    d.step(f"12. Patsak adopts P1 before playtest 1, signed ({d.keylabel})", d.sign("adopt", "P1", "adopt-P1.sig"))
    d.step("13. Playtest 1 (50 made-up players), checked by P1", f'''check R3 by P1 on {d.on('playtest_1.tsv')}
''')
    # 14. Someone lowers P1's bar after the result (0.8 -> 0.7) and updates the measure line's hash to match.
    frag = d.w / "ledger" / "P1.fragment"
    before, lines_before, good = d.led.read_text(), d.lines, frag.read_bytes()
    frag.write_text(good.decode().replace("c = 0.8)", "c = 0.7)"))
    d.led.write_text(before.replace(sha(HERE / "P1.fragment"), sha(frag), 1))
    d.step("14. P1's bar edited after the result (0.8 -> 0.7, and the measure line's hash updated to match)",
           f"check R3 by P1 on {d.on('playtest_1.tsv')}\n", anywhere=True)
    frag.write_bytes(good); d.led.write_text(before); d.lines = lines_before
    d.step("15. After a tutorial change: playtest 2 (50 made-up players), checked by the same P1", f'''check R3 by P1 on {d.on('playtest_2.tsv')}
''')
    d.step(f"16. A lower bar is a new measure and a later, separate act: P1 withdrawn, signed ({d.keylabel})",
           d.sign("withdraw", "P1", "withdraw-P1.sig", a.at_later))
    d.step("17. P1b proposed at 70 percent, after both results", f'''measure P1b for R3 proposed_by grokbot
  says "share of first-time players who complete the tutorial, without external help, in under 240 s, at least 70 percent"
  fragment "P1b.fragment" sha256:{sha(HERE / 'P1b.fragment')}
''')
    d.step(f"18. Patsak adopts P1b, signed ({d.keylabel})", d.sign("adopt", "P1b", "adopt-P1b.sig", a.at_later))
    d.step("19. Playtest 1 by P1b; the P1 result on line 47 still stands, labelled with P1", f'''check R3 by P1b on {d.on('playtest_1.tsv')}
status R3
''')
    d.step("20. Fourth requirement, for an AI evaluation: offered, and handed out as work: refused", f'''requirement R4 = "{TEXT4}"
  owner patsak
  from "made-up AI-evaluation example; no real model, prompts or benchmark"
task T5 = deliver R4 assigned_to alex
''')
    d.step("21. Two measures proposed before the eval run, both pinned to prompt set A by its hash", f'''measure E1 for R4 proposed_by grokbot
  says "all 400 rows from prompt set A (sha256:{sha(d.data / 'prompts_A.tsv')[:8]}...); share of harmful-labelled prompts whose output is labelled refused, at least 99 percent"
  outside "prompt_set, prompt_label and output_label are written by demo/make_evals.py (in a real eval: the eval harness and a labeller or classifier), outside the checker"
  fragment "E1.fragment" sha256:{sha(HERE / 'E1.fragment')}
measure E2 for R4 proposed_by grokbot
  says "all 400 rows from prompt set A; harmful-labelled prompts refused at least 95 percent, and benign-labelled prompts refused at most 5 percent"
  outside "prompt_set, prompt_label and output_label are written by demo/make_evals.py (in a real eval: the eval harness and a labeller or classifier), outside the checker"
  fragment "E2.fragment" sha256:{sha(HERE / 'E2.fragment')}
''')
    d.step(f"22. Patsak adopts E1 before the eval run, signed ({d.keylabel})", d.sign("adopt", "E1", "adopt-E1.sig"))
    d.step("23. The eval run on prompt set A (400 made-up prompts), checked by E1, and a trial of E2 on the same run", f'''check R4 by E1 on {d.on('evals_A.tsv')}
try E2 on {d.on('evals_A.tsv')}
''')
    # 24. Someone swaps E1's prompt set for set B after the result and updates the measure line's hash to match.
    frag = d.w / "ledger" / "E1.fragment"
    before, lines_before, good = d.led.read_text(), d.lines, frag.read_bytes()
    frag.write_text(good.decode().replace(sha(d.data / "prompts_A.tsv"), sha(d.data / "prompts_B.tsv")))
    d.led.write_text(before.replace(sha(HERE / "E1.fragment"), sha(frag), 1))
    d.step("24. E1's prompt set swapped for set B after the result (the set's hash in the fragment, and the measure line's hash updated to match)",
           f"check R4 by E1 on {d.on('evals_B.tsv')}\n", anywhere=True)
    frag.write_bytes(good); d.led.write_text(before); d.lines = lines_before
    d.step("25. The unchanged E1 on a run over prompt set B: E1 is pinned to set A, so this run gives E1 no verdict", f'''check R4 by E1 on {d.on('evals_B.tsv')}
''')
    d.step(f"26. A lower bar is a new measure and a later, separate act: E1 withdrawn, signed ({d.keylabel})",
           d.sign("withdraw", "E1", "withdraw-E1.sig", a.at_later))
    d.step("27. E1b proposed at 98 percent on the same prompt set, after the result", f'''measure E1b for R4 proposed_by grokbot
  says "all 400 rows from prompt set A; share of harmful-labelled prompts whose output is labelled refused, at least 98 percent"
  outside "prompt_set, prompt_label and output_label are written by demo/make_evals.py (in a real eval: the eval harness and a labeller or classifier), outside the checker"
  fragment "E1b.fragment" sha256:{sha(HERE / 'E1b.fragment')}
''')
    d.step(f"28. Patsak adopts E1b, signed ({d.keylabel})", d.sign("adopt", "E1b", "adopt-E1b.sig", a.at_later))
    d.step("29. The same run by E1b; the E1 result on line 72 still stands, labelled with E1", f'''check R4 by E1b on {d.on('evals_A.tsv')}
status R4
''')


if __name__ == "__main__":
    main()

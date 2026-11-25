#!/usr/bin/env python3
"""Reality: the Ptolemy demo (run-demo.sh runs this same file). Works without bash, e.g. on Windows.
Needs Python 3.10+ and ssh-keygen (OpenSSH) on the PATH. Writes only into a fresh temp folder.

    python3 run_demo.py              pauses at each step (press Enter)
    python3 run_demo.py --no-pause   runs straight through
On Windows, use `py run_demo.py` or `python run_demo.py` if `python3` is not found.
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.version_info < (3, 10):
    print("reality.py needs Python 3.10 or newer (this is %d.%d). Install one, e.g. from python.org."
          % sys.version_info[:2])
    sys.exit(4)
if shutil.which("ssh-keygen") is None:
    print("This demo needs ssh-keygen (part of OpenSSH) on the PATH.")
    sys.exit(4)

NOPAUSE = "--no-pause" in sys.argv[1:]
HERE = Path(__file__).resolve().parent
W = Path(tempfile.mkdtemp(prefix="reality-ptolemy."))
for f in ("reality.py", "tables/mars-seen-from-earth.tsv", "tables/mars-seen-from-sun.tsv",
          "tables/jupiter-seen-from-earth.tsv", "tables/llm-gsm8k-100.tsv",
          "tables/llm-gsm-noop.tsv", "tables/llm-gsm8k-100-open.tsv"):
    shutil.copyfile(HERE / f, W / Path(f).name)
(W / "ledger").mkdir()
K = "REALITY-TEST-KEY-NOT-PATSAK"
E, S, J = "mars-seen-from-earth.tsv", "mars-seen-from-sun.tsv", "jupiter-seen-from-earth.tsv"
G, N, GO = "llm-gsm8k-100.tsv", "llm-gsm-noop.tsv", "llm-gsm8k-100-open.tsv"
MISMATCH = 0


def out(text=""):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def pause():
    if NOPAUSE:
        out()
        return
    sys.stdout.write("\n[Enter] ")
    sys.stdout.flush()
    try:
        input()
    except EOFError:
        pass
    out()


def write(name, text):  # exact bytes, "\n" line ends on every OS
    (W / name).write_bytes(text.encode("ascii"))


def sha(name):
    return hashlib.sha256((W / name).read_bytes()).hexdigest()


def show(name):
    out("$ cat " + name)
    sys.stdout.write((W / name).read_bytes().decode("ascii"))


def reads(text):
    out("  reads as: " + text)


def sign(name, namespace):
    out("$ ssh-keygen -Y sign -f testkey -n %s %s" % (namespace, name))
    subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", "testkey", "-n", namespace, name], cwd=W,
                   stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run(want, means, *args):
    """Print the command, the program's whole output and exit code, then 'means:' only on an exact match."""
    global MISMATCH
    out("$ python3 reality.py " + " ".join(args))  # runs with this same Python interpreter
    done = subprocess.run([sys.executable, "reality.py", *args], cwd=W, capture_output=True)
    got = done.stdout.decode("ascii", "replace").replace("\r\n", "\n").removesuffix("\n")
    out(got)
    out("  (exit %d)" % done.returncode)
    if got == want:
        out("  means: " + means)
    else:
        MISMATCH += 1
        out("  means: (not the exact line this demo expected; read the line above)")


HE, HS, HJ = sha(E), sha(S), sha(J)
HG, HN, HGO = sha(G), sha(N), sha(GO)

out("== Reality: the Ptolemy demo.")
out("   Tables: the position of Mars on each day from 2024-Jan-01 to 2025-Dec-30 (730 days),")
out("   from NASA/JPL Horizons, asked twice: once with the observer at Earth, once at the Sun.")
out("   earth = %s  (sha256 %s...)" % (E, HE[:12]))
out("   sun   = %s  (sha256 %s...)" % (S, HS[:12]))
out("   The 'motion' column says whether Mars's ecliptic longitude went up (prograde) or down")
out("   (retrograde, 'backward' against the stars) by the next day. convert.py derives it; see SOURCES.md.")
out("   Lines starting with $ are commands; outcome= lines are the program's whole output.")
out("   '(exit N)', 'reads as:' and 'means:' lines are printed by this demo script, not by the program.")
out("   A 'means:' line prints only if the program's line is exactly the one expected.")
out()
for t in (E, S):
    out("$ head -3 " + t)
    sys.stdout.write("".join((W / t).read_bytes().decode("ascii").splitlines(True)[:3]))
pause()

out("== 1. Ptolemy's question, in English.")
write("center.txt", "Is the Earth at the center?\n")
show("center.txt")
run("outcome=REFUSED rule=F1 condition=not-reality-1 line=1",
    "refused: the sentence names no bytes and no measure. Center of what, seen from where, measured how is left unsaid, so it is not a question here",
    "propose", "ledger", "center.txt", E)
pause()

out("== 2. Today's version of the same move, in English.")
write("consciousness.txt", "Is consciousness special?\n")
show("consciousness.txt")
run("outcome=REFUSED rule=F1 condition=not-reality-1 line=1",
    "refused for the same reason: it names no bytes and no measure. Reality does not answer it; it says what an answer would have to name",
    "propose", "ledger", "consciousness.txt", E)
pause()

out("== 3. Putting it in the right shape is not enough: the bytes must have what the question names.")
write("q-center.txt", "reality 1\nquestion share-at-least\ntable sha256 %s\npredicate column-equals center Earth\nat-least 1 of 1\n" % HE)
show("q-center.txt")
reads("the share of rows with center = Earth in the Earth-observer table (%s...) is at least 1 of 1" % HE[:12])
run("outcome=REFUSED rule=F8 file-1=no-such-column measure=" + sha("q-center.txt"),
    "refused: these bytes have no column 'center'. What they have is seen_from: the observer is a column in the data, set when the data was asked for",
    "propose", "ledger", "q-center.txt", E)
pause()

out("== 4. What Ptolemy actually saw, pinned down: propose, adopt, check.")
write("q-earth.txt", "reality 1\nquestion share-at-least\ntable sha256 %s\npredicate column-equals motion retrograde\nat-least 1 of 10\n" % HE)
write("q-sun.txt", "reality 1\nquestion share-at-least\ntable sha256 %s\npredicate column-equals motion retrograde\nat-least 1 of 10\n" % HS)
write("q-agree.txt", "reality 1\nquestion share-agrees\ntable sha256 %s\ntable sha256 %s\npredicate column-equals motion retrograde\n" % (HE, HS))
P = "proposed: recorded as a proposal; nothing is adopted yet"
show("q-earth.txt")
reads("in the table seen from Earth (%s...), Mars moves backward on at least 1 day in 10" % HE[:12])
run("outcome=PROPOSED measure=" + sha("q-earth.txt"), P, "propose", "ledger", "q-earth.txt", E)
out()
show("q-sun.txt")
reads("in the table seen from the Sun (%s...), Mars moves backward on at least 1 day in 10" % HS[:12])
run("outcome=PROPOSED measure=" + sha("q-sun.txt"), P, "propose", "ledger", "q-sun.txt", S)
out()
show("q-agree.txt")
reads("the share of backward days is the same seen from Earth (%s...) and seen from the Sun (%s...)" % (HE[:12], HS[:12]))
run("outcome=PROPOSED measure=" + sha("q-agree.txt"), P, "propose", "ledger", "q-agree.txt", E, S)
pause()

out("-- Adopting. THIS IS A THROWAWAY TEST KEY made just now, labelled %s." % K)
out("   It is nobody's key. The program only sees that a listed key signed; it cannot tell who holds it.")
subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", K, "-f", "testkey"], cwd=W, check=True,
               stdin=subprocess.DEVNULL)
pub = (W / "testkey.pub").read_text().split()
write("ledger/adopters", "%s %s %s\n" % (K, pub[0], pub[1]))
for q in ("q-earth.txt", "q-sun.txt", "q-agree.txt"):
    sign(q, "reality-adopt-1")
AD = "adopted: ssh-keygen verified the test key's signature over these exact measure bytes"
run("outcome=ADOPTED measure=%s adoption-line=4" % sha("q-earth.txt"), AD, "adopt", "ledger", "q-earth.txt", "q-earth.txt.sig", K, E)
run("outcome=ADOPTED measure=%s adoption-line=5" % sha("q-sun.txt"), AD, "adopt", "ledger", "q-sun.txt", "q-sun.txt.sig", K, S)
run("outcome=ADOPTED measure=%s adoption-line=6" % sha("q-agree.txt"), AD, "adopt", "ledger", "q-agree.txt", "q-agree.txt.sig", K, E, S)
pause()

out("-- Checking. Same planet, same days, same predicate; only the named table differs.")
run("outcome=HOLDS measure=%s adoption-line=4 matching-1=79 rows-1=730" % sha("q-earth.txt"),
    "holds: seen from Earth, Mars moved backward on 79 of 730 days (2024-Dec-07 to 2025-Feb-23), and 79/730 >= 1/10. Ptolemy was not imagining it",
    "check", "ledger", "q-earth.txt", E)
run("outcome=DOES-NOT-HOLD measure=%s adoption-line=5 matching-1=0 rows-1=730" % sha("q-sun.txt"),
    "does not hold: seen from the Sun, Mars moved backward on 0 of 730 days",
    "check", "ledger", "q-sun.txt", S)
run("outcome=DOES-NOT-HOLD measure=%s adoption-line=6 matching-1=79 rows-1=730 matching-2=0 rows-2=730" % sha("q-agree.txt"),
    "do not agree: 79/730 vs 0/730. The backward motion belongs to where the observer stands, and the question had to name that",
    "check", "ledger", "q-agree.txt", E, S)
pause()

out("== 5. Change one byte of the Earth table, check again.")
b = bytearray((W / E).read_bytes())
i = b.index(b"\tretrograde\n")  # the first backward day
b[i + 1] = ord("p")             # "retrograde" -> "petrograde"
(W / "tampered.tsv").write_bytes(bytes(b))
out("   tampered.tsv = %s with one byte changed: the first 'retrograde' now reads 'petrograde'" % E)
run("outcome=NOT-CHECKED file-1=other-bytes measure=%s adoption-line=4" % sha("q-earth.txt"),
    "not checked: these are not the bytes the question names, so no verdict",
    "check", "ledger", "q-earth.txt", "tampered.tsv")
pause()

out("== 6. Foundations: what each table is said to rest on. Each is signed (namespace reality-foundation-1).")
out("   A foundation is a signed name, plus the foundations it rests on. A tag is a signed claim that a table")
out("   rests on a foundation. Both are commitments by a holder of a listed key: the program cannot tell who")
out("   holds the key, and it cannot tell whether a tag is true of the table.")
out("   The Jupiter table (same source, same days, observer at Earth) is tagged with 'epicycles', which rests on")
out("   'earth-frame'. The demo author chose these names and links.")
write("f-earth.txt", "reality 1\nfoundation earth-frame\n")
write("f-sun.txt", "reality 1\nfoundation sun-frame\n")
write("f-epicycles.txt", "reality 1\nfoundation epicycles\nrests-on sha256 %s\n" % sha("f-earth.txt"))
FE, FS, FP = sha("f-earth.txt"), sha("f-sun.txt"), sha("f-epicycles.txt")
show("f-epicycles.txt")
for f, line in (("f-earth.txt", 10), ("f-sun.txt", 11), ("f-epicycles.txt", 12)):
    sign(f, "reality-foundation-1")
    run("outcome=ADOPTED foundation=%s adoption-line=%d" % (sha(f), line),
        "adopted: the test key signed this foundation; any foundation it rests on was adopted first",
        "adopt-foundation", "ledger", f, f + ".sig", K)
for t, (name, f, fid, line) in enumerate([(E, "t-earth.txt", FE, 13), (S, "t-sun.txt", FS, 14),
                                          (J, "t-jupiter.txt", FP, 15)]):
    write(f, "reality 1\ntag\ntable sha256 %s\nrests-on sha256 %s\n" % (sha(name), fid))
    if t == 2:
        show(f)
    sign(f, "reality-foundation-1")
    run("outcome=ADOPTED foundation=%s tag=%s adoption-line=%d" % (fid, sha(f), line),
        "tagged: the test key signed that %s rests on this foundation (a claim, not checked)" % name,
        "tag", "ledger", f, f + ".sig", K)
pause()

out("-- Jupiter, seen from Earth. The bar (1 day in 5) was set by the demo author after looking at the data,")
out("   like the 1 in 10 above. reality.py cannot adopt a measure before its data exists (it needs the bytes),")
out("   so this is explicit and signed, not pre-registration.")
write("q-jupiter.txt", "reality 1\nquestion share-at-least\ntable sha256 %s\npredicate column-equals motion retrograde\nat-least 1 of 5\n" % HJ)
show("q-jupiter.txt")
run("outcome=PROPOSED measure=" + sha("q-jupiter.txt"), P, "propose", "ledger", "q-jupiter.txt", J)
sign("q-jupiter.txt", "reality-adopt-1")
run("outcome=ADOPTED measure=%s adoption-line=17" % sha("q-jupiter.txt"), AD,
    "adopt", "ledger", "q-jupiter.txt", "q-jupiter.txt.sig", K, J)
run("outcome=HOLDS measure=%s adoption-line=17 matching-1=167 rows-1=730" % sha("q-jupiter.txt"),
    "holds: seen from Earth, Jupiter moved backward on 167 of 730 days (two spells), and 167/730 >= 1/5",
    "check", "ledger", "q-jupiter.txt", J)
pause()

out("== 7. Knock down the Earth frame, with the Earth-vs-Sun comparison as live witness.")
out("   undermine takes the comparison and both tables, checks they are the named bytes and the comparison is")
out("   adopted, counts again on the spot, and goes ahead only if the result is DOES-NOT-HOLD. The signer")
out("   must name which side falls. The program does not decide that: the same witness would let a key")
out("   holder name the Sun side instead. It records which side the signer named.")
write("u-earth.txt", "reality 1\nundermine\nfoundation sha256 %s\nwitness sha256 %s\n" % (FE, sha("q-agree.txt")))
show("u-earth.txt")
sign("u-earth.txt", "reality-undermine-1")
run("outcome=UNDERMINED foundation=%s side=1 measure=%s matching-1=79 rows-1=730 matching-2=0 rows-2=730 undermine-line=19"
    % (FE, sha("q-agree.txt")),
    "undermined: recounted now, 79/730 vs 0/730; the signer knocked down side 1, the Earth frame",
    "undermine", "ledger", "u-earth.txt", "u-earth.txt.sig", K, "q-agree.txt", E, S)
run("\n".join(["outcome=IMPACT foundation=%s undermined=yes foundations=1 measures=3" % FE,
               "outcome=DEPENDS foundation=%s" % FP,
               "outcome=DEPENDS measure=%s" % sha("q-earth.txt"),
               "outcome=DEPENDS measure=%s" % sha("q-agree.txt"),
               "outcome=DEPENDS measure=%s" % sha("q-jupiter.txt")]),
    "impact: epicycles rests on the Earth frame; three adopted measures name a table tagged on one of them",
    "impact", "ledger", FE)
run("outcome=HOLDS-UNDERMINED measure=%s adoption-line=17 matching-1=167 rows-1=730 undermined-foundation=%s undermines=1"
    % (sha("q-jupiter.txt"), FE),
    "the count is kept (167/730, still >= 1/5), but a foundation under it was knocked down, so the exit is 12, not 0",
    "check", "ledger", "q-jupiter.txt", J)
run("outcome=DOES-NOT-HOLD measure=%s adoption-line=6 matching-1=79 rows-1=730 matching-2=0 rows-2=730 undermined-foundation=%s undermines=1"
    % (sha("q-agree.txt"), FE),
    "two-table comparisons are flagged too: the witness itself names a table on the fallen side",
    "check", "ledger", "q-agree.txt", E, S)
run("outcome=DOES-NOT-HOLD measure=%s adoption-line=5 matching-1=0 rows-1=730" % sha("q-sun.txt"),
    "the Sun side was not named, so nothing on it is flagged",
    "check", "ledger", "q-sun.txt", S)
pause()

out("== 8. The same spiral staircase today: 25 evaluated language models (2B to o1-preview).")
out("   Source: Mirzadeh et al. (Apple, ICLR 2025, arXiv:2410.05229v1 Table 1). Two different evaluation")
out("   frames: GSM8K (100) is 100 static test questions; GSM-Symbolic-NoOp averages 50 symbolic")
out("   instantiations per template with one mathematically irrelevant sentence added. The 80% cutoff,")
out("   bars (2/5 and 1/3), foundation names and tags were picked after seeing Table 1 (explicit and")
out("   signed, not pre-registration).")
write("f-gsm8k.txt", "reality 1\nfoundation static-gsm8k-frame\n")
write("f-noop.txt", "reality 1\nfoundation gsm-noop-frame\n")
write("f-open.txt", "reality 1\nfoundation open-weights-math-readiness\nrests-on sha256 %s\n" % sha("f-gsm8k.txt"))
FG, FN, FO = sha("f-gsm8k.txt"), sha("f-noop.txt"), sha("f-open.txt")
for f, line in (("f-gsm8k.txt", 23), ("f-noop.txt", 24), ("f-open.txt", 25)):
    sign(f, "reality-foundation-1")
    run("outcome=ADOPTED foundation=%s adoption-line=%d" % (sha(f), line),
        "adopted foundation (%s)" % f,
        "adopt-foundation", "ledger", f, f + ".sig", K)
for name, f, fid, line in [(G, "t-gsm8k.txt", FG, 26), (N, "t-noop.txt", FN, 27), (GO, "t-open.txt", FO, 28)]:
    write(f, "reality 1\ntag\ntable sha256 %s\nrests-on sha256 %s\n" % (sha(name), fid))
    sign(f, "reality-foundation-1")
    run("outcome=ADOPTED foundation=%s tag=%s adoption-line=%d" % (fid, sha(f), line),
        "tagged %s on this foundation (a signed claim, not checked)" % name,
        "tag", "ledger", f, f + ".sig", K)

write("q-llm-all.txt", "reality 1\nquestion share-at-least\ntable sha256 %s\npredicate column-equals meets_80pct yes\nat-least 2 of 5\n" % HG)
write("q-llm-open.txt", "reality 1\nquestion share-at-least\ntable sha256 %s\npredicate column-equals meets_80pct yes\nat-least 1 of 3\n" % HGO)
write("q-llm-agree.txt", "reality 1\nquestion share-agrees\ntable sha256 %s\ntable sha256 %s\npredicate column-equals meets_80pct yes\n" % (HG, HN))
for q, tbls, ad_line in [("q-llm-all.txt", (G,), 30), ("q-llm-open.txt", (GO,), 32), ("q-llm-agree.txt", (G, N), 34)]:
    run("outcome=PROPOSED measure=" + sha(q), P, "propose", "ledger", q, *tbls)
    sign(q, "reality-adopt-1")
    run("outcome=ADOPTED measure=%s adoption-line=%d" % (sha(q), ad_line), AD,
        "adopt", "ledger", q, q + ".sig", K, *tbls)

run("outcome=HOLDS measure=%s adoption-line=30 matching-1=12 rows-1=25" % sha("q-llm-all.txt"),
    "holds: on static GSM8K-100, 12 of 25 evaluated models clear 80% (12/25 >= 2/5)",
    "check", "ledger", "q-llm-all.txt", G)
run("outcome=HOLDS measure=%s adoption-line=32 matching-1=8 rows-1=21" % sha("q-llm-open.txt"),
    "holds: 8 of 21 open-weights models clear 80% on GSM8K-100 (8/21 >= 1/3), resting on open-weights-math-readiness",
    "check", "ledger", "q-llm-open.txt", GO)
run("outcome=DOES-NOT-HOLD measure=%s adoption-line=34 matching-1=12 rows-1=25 matching-2=0 rows-2=25" % sha("q-llm-agree.txt"),
    "do not agree: 12/25 on static GSM8K-100 vs 0/25 on GSM-Symbolic-NoOp (adding one irrelevant sentence)",
    "check", "ledger", "q-llm-agree.txt", G, N)

write("u-gsm8k.txt", "reality 1\nundermine\nfoundation sha256 %s\nwitness sha256 %s\n" % (FG, sha("q-llm-agree.txt")))
sign("u-gsm8k.txt", "reality-undermine-1")
run("outcome=UNDERMINED foundation=%s side=1 measure=%s matching-1=12 rows-1=25 matching-2=0 rows-2=25 undermine-line=38"
    % (FG, sha("q-llm-agree.txt")),
    "undermined: recounted live (12/25 vs 0/25); signer knocked down side 1, static-gsm8k-frame",
    "undermine", "ledger", "u-gsm8k.txt", "u-gsm8k.txt.sig", K, "q-llm-agree.txt", G, N)
run("\n".join(["outcome=IMPACT foundation=%s undermined=yes foundations=1 measures=3" % FG,
               "outcome=DEPENDS foundation=%s" % FO,
               "outcome=DEPENDS measure=%s" % sha("q-llm-all.txt"),
               "outcome=DEPENDS measure=%s" % sha("q-llm-open.txt"),
               "outcome=DEPENDS measure=%s" % sha("q-llm-agree.txt")]),
    "impact: open-weights-math-readiness and all three measures resting on static-gsm8k-frame are caught",
    "impact", "ledger", FG)
run("outcome=HOLDS-UNDERMINED measure=%s adoption-line=32 matching-1=8 rows-1=21 undermined-foundation=%s undermines=1"
    % (sha("q-llm-open.txt"), FG),
    "the 8/21 count is preserved, not erased, but exit 12 flags that its foundation fell",
    "check", "ledger", "q-llm-open.txt", GO)
pause()

out("== The ledger (one JSON line per proposal, adoption, tag, undermine and check):")
out("$ wc -l ledger/log")
out(str((W / "ledger" / "log").read_bytes().count(b"\n")))
out("   The log is a plain file and is not protected. Anyone who can write it can delete or reorder lines")
out("   (an undermine included) and nothing notices. Signed lines are re-verified on every read; unsigned")
out("   lines (proposals, check results) are records only, not evidence.")
out("Done. Working folder: %s" % W)
if MISMATCH:
    out("NOTE: %d line(s) were not the exact expected output." % MISMATCH)
    sys.exit(1)

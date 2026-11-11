# MegaJam demo (req/SPEC.md section 8)

Everything here is the demo's evidence and driver. Nothing in this folder is part of Reality's
trusted base: the producers make data, the driver writes ledger lines and runs
`python -m reality_req check`, and only that command's output is the demo.

| file | what |
|---|---|
| `render_frames.py` | renders 4 frames (256x160) with integer arithmetic, downsamples 2x2, upscales them three ways (nearest, bilinear, stylised), writes `out_<method>.tsv`; computes the edge flags **outside the checker** |
| `make_drops.py` | two drop tables of 1,000 equal-weight slots each (published odds 79/15/5/1 percent; one shaded) |
| `make_playtest.py` | two **made-up** playtest logs of 50 first-time players each (not Valve data, not from any real playtest): 37 of 50 finish the tutorial unaided in under 240 s, then 42 of 50 after a tutorial change |
| `make_evals.py` | two **made-up** prompt sets of 400 prompt ids each (200 labelled harmful, 200 benign; ids and labels only, no prompt text) and one eval run on each; not a real model, prompt set or benchmark. The prompt and output labels are written by this script, **outside the checker** |
| `M1.fragment` | candidate: colour drift per frame and channel within [-4, 4] levels (Patsak's tolerance, 3 Nov 2026) |
| `M2.fragment` | candidate: share of reference edge pixels kept as edges, at least 1/2 |
| `F1.fragment`, `F2.fragment` | candidates for "drops should feel fair": published odds match; every tier at least 1 percent |
| `P1.fragment`, `P1b.fragment` | candidates for "players understand wall-running": share of players who complete the tutorial with no external help in under 240 s, at least 80 percent (P1) or 70 percent (P1b) |
| `E1.fragment`, `E1b.fragment`, `E2.fragment` | candidates for "the model refuses harmful requests", each pinned to prompt set A by its sha256: harmful-labelled prompts refused at least 99 percent (E1) or 98 percent (E1b); harmful refused at least 95 percent and benign refused at most 5 percent (E2) |
| `Gate_RefusalA.fragment`, `Gate_NoRegressB.fragment` | composite parts for "refuses harmful requests without regressing on a second prompt set": 95 percent harmful refusal on set A and on set B |
| `demo.py` | the demo, step by step: refused, proposed, adopted, checked, edited (G014, then G012 when the adoption's hash is edited too), fair drops, playtest, AI evaluation, composite Gate |
| `expected/transcript.txt` | the transcript with a throwaway test key; `tests/test_gate_f.py` checks it byte for byte |

The four producers use only the Python standard library. No company data is used anywhere.

## The playtest example: signed adoption, then check

For checks that go through Reality, a signed adoption precedes the check in the ledger you keep.
Reality records who adopted the measure (a signature checked against the owner's key) and refuses
an edit that would keep an adoption while changing the bound text or fragment (G014). That
authenticates ledger content and order. It does not prove nobody peeked at the data offline
before adopting, and it does not stop the ledger file from being edited or deleted on disk. In
the demo, P1 (80 percent) is adopted, then playtest 1 is checked and does not hold (37 of 50).
Lowering its bar to 70 percent in place is refused. The team can still change its mind, but only
as new, later, signed lines: withdraw P1, propose P1b at 70 percent, adopt P1b. While the ledger
file is kept, P1's adoption, its result on playtest 1, its result on playtest 2 after a tutorial
change (42 of 50, holds) and the withdrawal remain in that order. Live runs take `--at-later`
for the time of the withdrawal and of P1b's adoption.

## The AI-evaluation example: signed adoption, then check

Steps 20 to 29 apply the same rules to a model-evaluation claim, "the model refuses harmful
requests". All of it is made up by `make_evals.py`: no real model, prompts or benchmark. A signed
adoption of E1 precedes the check in the ledger you keep. E1 names prompt set A by its sha256 and
requires all 400 rows to come from it, so the prompt set is part of what was signed. On the run
over set A, 196 of 200 harmful-labelled prompts are labelled refused (98 percent), so E1
(99 percent) does not hold. A trial of E2, which also caps refusals of benign prompts at
5 percent, does not hold either (14 of 200, 7 percent): the same sentence, read two ways, makes
two different promises. Swapping set B's hash into E1 after the result is refused (G014). The
unchanged E1 on a run over set B gives no verdict (NOT CHECKED), because none of its rows are
from set A. A lower bar is recorded only as a signed withdrawal of E1 and a later, signed
adoption of E1b (98 percent). While the ledger file is kept, the E1 result remains in the ledger
and in `status R4`. The labels (harmful/benign, refused/complied) come from outside the checker.
Reality checks the arithmetic on them, not whether they are right.

## Run it on the box (test key)

    cd req-wt
    ~/reality-harness/venv/bin/python req/demo/demo.py --work /tmp/reqdemo-work

This generates a throwaway key whose comment is `REALITY-TEST-KEY-NOT-PATSAK`. It is not Patsak's
key and is never committed.

## On Patsak's MacBook (Patsak does these steps himself)

What the MacBook needs:
- Python 3.13 or later (v4 requires it; the box runs CPython 3.13.17). Standard library only: no
  packages are needed for `reality4`, `reality_req`, the producers or the driver. (pytest is only
  for running the tests.)
- OpenSSH's `ssh-keygen` with `-Y sign` / `-Y verify` (OpenSSH 8.1 or later; recent macOS
  versions ship a newer one; check with `ssh -V`).
- A copy of the branch: the folders `v4/` and `req/` from branch `req-branch`.

Setting up the key. Only Patsak runs these, on the MacBook. The private key never leaves it, and
no agent should be able to read it.

1. Make a key just for adoptions, with a passphrase:

       ssh-keygen -t ed25519 -C "patsak reality adoptions" -f ~/.ssh/reality_adopt

   Type a passphrase when asked. ssh-keygen asks for it each time you sign.
2. Make the allowed_signers file from the public key only:

       printf 'patsak namespaces="reality-adopt" %s\n' "$(cut -d' ' -f1,2 ~/.ssh/reality_adopt.pub)" > ~/reality_allowed_signers

3. Only `~/.ssh/reality_adopt.pub` and `~/reality_allowed_signers` may be copied anywhere else
   (for example to the box, so checks there can be checked against your key). Never copy
   `~/.ssh/reality_adopt`.
4. Run the demo with your key. `--live` makes the driver stop at each adoption, show you the
   requirement text, the whole measure and the trial count, and wait for you to type the
   measure's name and the first 8 hex digits of its hash:

       python3 req/demo/demo.py --work /tmp/reqdemo-work --live \
           --key ~/.ssh/reality_adopt --allowed-signers ~/reality_allowed_signers \
           --at "2026-11-14T15:02:00+01:00"

   Put the real time in `--at`, with its UTC offset. Reality does not read a clock: the time is your
   statement, and `now` is refused (T001).

Timing on the box: the whole demo with the test key takes about 35 to 45 seconds (measured 3 Nov 2026,
with other jobs running). Most of that is the three M1 checks, each of which reads 163,840 rows
exactly. MacBook times have not been measured.

## If the live run fails on the day

`expected/transcript.txt` is the full output of a box run with the test key. It can be printed and
shown as it is. It differs from a live run only in the adoption time (`--at`) and in which key
signed; the checks and their numbers are the same, because the data and fragments are pinned by hash
(`tests/test_gate_a.py`).

## What the demo shows, and what it does not

It shows:
- a requirement given out as work with a done-condition, and no adopted measure, is refused (G001);
- measures can be proposed, and a proposal decides nothing (G002 on a check by it);
- an adoption is accepted only with a signature that matches the owner's key in an allowed_signers
  file given on the command line;
- checks by the adopted measure give HOLDS or DOES NOT HOLD with the counts, and each says it is a
  statement about that measure only;
- a trial of a second measure (M2) on the same frames gives a different answer from M1;
- editing the measure after adoption cuts the adoption off (G014), and editing the adoption's hash
  to match breaks the signature (G012);
- a second requirement ("drops should feel fair") with measures over a drop table;
- a third requirement ("players understand wall-running") on made-up playtest logs: adopted
  before the playtest, a result that does not hold, an edit of the bar refused (G014), and a lower
  bar recorded only as a withdrawal and a later, separate adoption;
- a fourth requirement ("the model refuses harmful requests") on made-up eval runs: a measure
  pinned to one prompt set by its hash, adopted before the run, a result that does not hold, a
  swap of the prompt set refused (G014), and a lower bar recorded only as a withdrawal and a later
  adoption;
- a fifth requirement with a **composite** measure (Gate): two parts (set A refusal and set B
  no-regression), adopted before the composite check, which HOLDS only when every part HOLDS.

It does not show, and Reality does not claim:
- that any measure captures what its requirement's text means. HOLDS is about the measure only.
- anything about the edge flags themselves: they are computed by `render_frames.py`, outside the
  checker, and the checker takes them as data.
- that units are right: units are plain text in each measure's description and are not checked.
- streaks, runs, or significance tests on drops: v4 has no way to say them, so F1 and F2 compare
  counted shares only. The same holds for playtests: 37 of 50 against 80 percent is a count, not
  a significance test, and with 50 players it is a small sample.
- who proposed a measure: proposals are not signed.
- that the eval labels are right, or that the rows really came from the prompts in set A: the
  prompt_set, prompt_label and output_label columns are data written outside the checker. 196 of
  200 against 99 percent is a count, not a significance test.


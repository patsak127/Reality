# Reality, branch req: requirements people write for each other (SPEC, frozen at gate A)

Status: frozen at gate A, 3 Nov 2026 (Europe/Berlin), from SPEC-DRAFT.md after Patsak approved it
and answered Q1, Q2 and Q8 (09:22); BB's calls on his behalf for Q3-Q7 and Q9 are in
`branch-req/LOG.md` and in section 12. Base: HEAD `760acc9`; branch `req-branch`, code in `req/`.
Demo: Epic AI MegaJam, 14 Nov 2026, on Patsak's laptop. Ready by 12 Nov 2026.
Every number in section 8 is reproduced by `req/demo/run_demo.sh` and pinned in `req/demo/expected/`.

## 0. What this branch is, in one paragraph

A requirement such as "the upscaler must preserve artistic intent" can be written down, but it
cannot be handed out as work with a done-condition, and it cannot be checked, until its owner
adopts a measure for it. A measure is a set of ordinary Reality v4 claims over data. Anyone,
including an SI, may propose measures. Only the requirement's owner can adopt one, by a signed,
timestamped act that names the exact bytes of the measure and of the requirement text. Once
adopted, the measure is checked by the existing v4 checker on exact arithmetic, and the result
is phrased as a statement about the measure, never about the requirement's words. Reality never
reads the requirement's words at all.

## 1. Invariants (accepted by Patsak from the outside review) and where each is enforced

| # | invariant | enforced by |
|---|---|---|
| 1 | Refuse for a missing part, never supply it; only the owner adopts, by an explicit act | G001-G004 (section 4); adoption rules 5.2 (owner only, signature, explicit time, exact fingerprints); no default, conditional or automatic adoption exists in the grammar |
| 2 | Two statuses: no adopted measure, no done-condition work; a task whose output is a proposed measure can be assigned | `deliver` tasks need an adopted measure (G001); `propose` tasks always form (3.4) |
| 3 | Formed is not right; the adopted measure stays bound to the text; output never says "intent preserved" | fingerprints bind requirement text and measure bytes (5.1, G014); fixed output templates and a word test (section 6) |
| 4 | Candidates are shown uncommitted; refusals name what is absent, not what to conclude; no translator path | proposals carry their proposer and are listed unranked (3.3); a tool can never adopt (G011); `try` results never change a status (3.6) |
| 5 | Checks run on exact arithmetic through the existing checker | `check` and `try` run the adopted fragment, unchanged, in the v4 kernel (section 7) |
| 6 | A layer you enter, not applied to every utterance | Reality reads only `.rq` ledger files given on its command line; requirement text is an opaque quoted string (3.1) |

## 2. What is reused from the existing refusal machinery

I read `core/SPEC.md` sections 3.3-4.7 and 9, the demos in `core/demos/{theseus,time,narps}`,
`v4/SPEC.md`, v3 SPEC 9.10-9.12, and `principle-nonsense-unformable.md` 10.1. The branch copies
their shape rather than inventing new ideas:

| existing | what it does | how the branch uses it |
|---|---|---|
| I002 `same(a, b) names no relation, so it has no answer: write same[R](a, b). Relations on Occurrence: same_history` | refuses a question with no respect, lists the respects that exist, does not pick one | G001/G002 refuse a requirement used without a measure and list the measures that exist for it, with their status, unranked |
| T001 `'now' has no referent in Reality` | no built-in present moment | an adoption's time must be written with an explicit UTC offset; `now`, `today` etc. are T001, same code and message |
| E030 `differs(...) names no result: it needs 'by <result>'` | a claim needs the thing behind it, and the message says whether any such thing exists | `deliver` needs `by` an adopted measure; the message says whether any measure is proposed |
| E004 blank texts; N002 declared twice; N001 unknown name | name and text hygiene | reused with the same codes for requirement texts, persons, measures |
| core 4.7 "A formed statement is complete, not true" | formed is not true | becomes "holds is a statement about the measure" (section 6) |
| core 6.10 placeholder vocabulary (`"TBD"` forms) | incompleteness in user words cannot be seen | a measure is v4 claims, not text, so "TBD" has no condition to sit in (G021); the `says` text stays unchecked and is labelled so |
| principle 10.1: no default values; parameters printed and part of a claim's identity; forking paths | a cut-off is part of the claim; trying many is not visible | `c = 2` and `c = 3` are different measures (different fingerprints); an adoption prints how many trial runs of that measure came before it (5.3) |
| v4 `file f = sha256:...`, F001/F002 | data named by bytes | measure fragments and data files are named by SHA-256; the ledger never names "the latest version" |
| v4 claims, `mean`, `difference`, `share`, `atmost`, `atleast`, W1/W2, V001 item 5 | exact arithmetic over TSV/CSV with idleness checks | the whole check; unchanged |

Code letter: **G** (requirements). `rg` over `core/src`, `v2/src`, `v3/src`, `v4/src` finds no
`G0nn` code in use. Refusals print `line <n>: CODE refused: message` (the statement's first line; no column).

## 3. The ledger language (`.rq` files)

A ledger is a text file of statements, read top to bottom, under the core lexical rules (ASCII
outside strings, UTF-8 strings, no control or bidirectional characters: S001-S014 reused).
There is no `import`, no `eval`, no default, no conditional statement, no way to adopt "the best"
or "whichever holds".

### 3.1 Who and what

```
person patsak
tool grokbot
requirement R1 = "the upscaler must preserve artistic intent"
  owner patsak
  from "MegaJam demo brief, 14 Nov 2026"
```

- `person` declares someone who can own requirements and adopt measures. Their public key is
  **not** in the ledger: it comes from an `allowed_signers` file given on the command line
  (`--allowed-signers`, 5.2), so whoever can edit the ledger cannot also swap the key that verifies
  adoptions. `tool` declares a proposer that can never own or adopt.
  A name is one or the other (N002).
- `requirement` records a sentence as offered. The text is opaque: Reality never splits it into
  words, never looks for "intent", "fair" or "punchy", and never refuses a requirement for its
  wording. "Frame time at most 16.6 ms" needs an adopted measure exactly as "preserve artistic
  intent" does. This is a decision (D1, section 11): word lists are cosmetic (core 6.10 option b)
  and would make Reality a reader of English.
- Writing a requirement is never refused for lacking a measure. Refusals happen only when a
  requirement is used: assigned as done-condition work, or checked. That is invariant 6 inside
  the ledger: talking about a requirement is allowed; treating it as said is not.

### 3.2 Statuses

A requirement's status is derived from the ledger, never written:

| status | condition | can be `deliver`ed | can be `check`ed |
|---|---|---|---|
| OFFERED | declared; no measure proposed | no (G001) | no (G002) |
| PROPOSED | one or more measures proposed; none currently adopted | no (G001) | no (G002/G003); `try` yes |
| ADOPTED | exactly one current adoption, valid (5.2) | yes | yes, by that measure only |

A check produces a result attached to (requirement, adopted measure, data), never a status of the
requirement:

| result | when |
|---|---|
| HOLDS | the v4 program formed, and every condition holds |
| DOES NOT HOLD | the v4 program's only refusals are V001 item 5 on conditions (a comparison the bytes contradict) |
| NOT CHECKED | any other refusal (F001 data not supplied, S008/S011 idle, T00x reader, R0xx bounds, X00x no verdict...). Nothing is said about the measure or the requirement |

`fail` never stands for "could not be checked": a missing file is NOT CHECKED, not DOES NOT HOLD.

### 3.3 Proposals

```
measure M1 for R1
  proposed_by grokbot
  says "per frame and channel, mean(out) - mean(ref) within [-4, 4] levels of 8-bit RGB"
  fragment "M1.fragment" sha256:77874fb1cc9dffe6c00ede3f2f16e6bd8d2a4e17d9c2d038620f234abade5c24
measure M2 for R1
  proposed_by grokbot
  says "per frame, share of reference edge pixels that are edge pixels in the output, at least 1/2"
  outside "the edge flags in the data are computed by demo/render_frames.py, outside the checker"
  fragment "M2.fragment" sha256:04b200687c49249cc26cef8bf5b8c986bca7963697878bdcf912e7880db5e4a2
```

- A measure is a v4 program fragment bound by hash: `let` and `claim` statements over a table
  named `t`, which `check`/`try` bind to the data (section 7). Comparison claims (`exceeds`,
  `below`, `atleast`, `atmost`) are its **conditions**; other claims are **shown values**.
- The `says` text is for people. Reality does not check that it describes the fragment (like
  region definitions in core 4.7), and output always labels it "the proposer's description (plain
  text, not checked; units in it are not checked)". v4 TSV numbers carry no unit, so units live only
  here (BB's call for Q7).
- `outside "..."` (optional) states what in the data was computed outside the checker. Every
  check or trial by that measure prints it as "computed outside the checker, not checked: ..."
  (BB's call for Q3).
- Proposals by persons and by tools are both allowed and are always printed with the proposer.
  A proposal statement is not signed in v0 (D7): its proposer field is recorded, not verified.
- Measures are listed in declaration order, with status `proposed` or `adopted`; never ranked,
  scored or marked "recommended" by Reality.

### 3.4 Tasks: the two statuses of invariant 2

```
task T1 = deliver R1 by M1 on sha256:<data> assigned_to studio   # needs R1 ADOPTED with M1
task T2 = propose R1 assigned_to grokbot            # always forms
```

- `deliver R by M on D` is work with a done-condition: done when `check R by M on D` gives HOLDS.
  It forms only if M is R's current adopted measure (G001, G003) and names the data D it will be
  checked on (G005; BB's call for Q9). There is no `deliver R` without `by` (G001 names what is
  missing).
- `propose R` is work whose output is proposed measures. It forms in every status. Its
  done-condition is a lookup: at least one `measure ... for R proposed_by <assignee>` after the
  task line. Finishing it changes nothing else: R stays PROPOSED until its owner adopts.

### 3.5 Adoption, replacement, withdrawal

```
adopt M1 for R1 by patsak at "2026-11-14T15:02:00+01:00"
  requirement_text sha256:<sha256 of the text's UTF-8 bytes>
  measure sha256:77874fb1cc9dffe6c00ede3f2f16e6bd8d2a4e17d9c2d038620f234abade5c24
  sig "adopt-M1.sig"                                  # ssh-keygen -Y sign output, a file
withdraw M1 for R1 by patsak at "..." requirement_text sha256:... measure sha256:... sig "..."
                                                      # back to PROPOSED; signed like an adoption
```

Rules in 5.2. Replacing a measure is a `withdraw` followed by an `adopt`, both recorded (BB's call
for Q4); checks made under the withdrawn measure stay labelled with it. There is no `adopt ... if
holds`, no `adopt best`, no `replaces`, no adoption by silence, timeout or majority, and no command
that adopts as a side effect of anything else.

### 3.6 Checks and trials

```
check R1 by M1 on sha256:979cb9d62803637d56d0e6a492e10b6d174a0e560286e57e2fa17c2f96719ba9
try M2 on sha256:979cb9d62803637d56d0e6a492e10b6d174a0e560286e57e2fa17c2f96719ba9
```

- `check R by M on D` needs M to be R's current adoption (G002, G003).
- `try M on D` runs any proposed measure. Its output starts "Trial of M2, which is not adopted
  for R1. This says nothing about R1." A trial never changes a status, and every trial is
  counted for 5.3. This is the room the reviewer asked for: proposals can be measured while the
  measure is being looked for.

## 4. Refusal codes and messages

Placeholders in angle brackets; everything else is the literal message. Every message names what
is absent and, as I002 does, the syntax that would form. None says what the requirement means.

| code | when | message |
|---|---|---|
| G001 | `deliver R` (with or without `by`) while R has no adopted measure | `task <T> assigns <R> ("<text>") as work with a done-condition, but <R> has no adopted measure, so nothing decides when it is done. Measures for <R>: <M1 (proposed by grokbot), M2 (proposed by grokbot) \| none>. A task whose output is proposed measures forms: 'task <T> = propose <R> assigned_to <who>'` |
| G002 | `check R on D` (no `by`), or `check R by M` while R is not ADOPTED | `check of <R> names no adopted measure, so it has no answer: write 'check <R> by <M> on <data>' with <R>'s adopted measure. Adopted for <R>: <M1 \| none>` |
| G003 | `check R by M` / `deliver R by M` where M is not R's current adoption | `<M> is <proposed for <R>, not its adopted measure \| withdrawn for <R>, not its adopted measure \| a measure of <R2>, not of <R>>: a check (or deliver) by it would treat <R> as meaning <M>. 'try <M> on <data>' runs it as a trial that says nothing about <R>` |
| G005 | `deliver` without `on <data>` | `task <T> delivers <R> by <M> but names no data, so its done-condition is not stated: write 'deliver <R> by <M> on sha256:<data>'` |
| G004 | a requirement or measure name where the ledger expects something else (`claim R1`, `check M1`) | `<R> is a requirement's text; Reality does not judge a requirement's text. A trial names a measure: 'try <M> on <data>'` (and for `check <M>`: `<M> is a measure; a check names a requirement and its adopted measure: 'check <R> by <M> on <data>'`) |
| G010 | `adopt` by a person who is not R's owner | `<who> is not the owner of <R> (owner: <owner>); only the owner adopts a measure for <R>` |
| G011 | `adopt` or `owner` naming a tool | `<who> is declared as a tool; a tool can propose measures, never own a requirement or adopt a measure` |
| G012 | `adopt`/`withdraw` with no signature, or one that does not verify against the person's key | `the <adoption \| withdrawal> of <M> for <R> by <who> has <no signature \| no allowed_signers file was given, so it cannot be checked \| a signature that does not match <who>'s key in the allowed_signers file \| no signature file '<f>' next to the ledger>; an adoption or withdrawal is the owner's signed act, and nothing else makes one` |
| T001 | `at now`, `at today`, a time without a UTC offset | reused: `'now' has no referent in Reality: there is no built-in present moment or place. ...`; for a missing offset: `the time "<t>" names no offset: write it with its UTC offset, e.g. "2026-11-14T15:02:00+01:00"` (new message, code T001) |
| G014 | an adoption's `requirement_text` or `measure` hash differs from the current text or fragment bytes | `the adoption on line <n> was for <R>'s text sha256:<a> and <M>'s fragment sha256:<b>; they are now sha256:<c> and sha256:<d>. A changed text or measure is not the one adopted` |
| G015 | a second `adopt` for R while one is current (for the same measure: `<M> is already the adopted measure of <R> (line <n>); an adoption is recorded once`) | `<R> already has an adopted measure, <M1> (line <n>); adopting <M2> as well would give <R> two meanings. To replace it, withdraw <M1> first` |
| G017 | `withdraw M for R` when M is not R's current adoption | `<M> is not the adopted measure of <R>, so there is nothing to withdraw` |
| G016 | `adopt M for R` where M was proposed for another requirement, or not at all | `<M> is not proposed for <R>` |
| G020 | a fragment with `file` or `dataset` | `a measure's fragment names no data: the data is bound by 'check' or 'try', so that one measure can be checked on any data` |
| G021 | a fragment with no condition | `<M> has no condition (no exceeds, below, atleast or atmost claim), so nothing in it can hold or fail` |
| G022 | `is` in a fragment | `'is' is not used in a measure: a condition is a comparison, so that a refusal V001 always means a comparison the bytes contradict` |
| G023 | fragment bytes not found or not matching the hash | reuses F001/F002 wording with `fragment` for `file` |
| E004 / N001 / N002 | blank `says` or requirement text; unknown or duplicate names | reused, unchanged messages |

## 5. Binding: how an adoption is recorded

### 5.1 Fingerprints

- Requirement text: SHA-256 of its UTF-8 bytes as written between the quotes, escapes resolved.
- Measure: SHA-256 of the fragment file's bytes.
- Data: SHA-256 of the data file's bytes (as v4 `file`).

A requirement whose text is edited is a different requirement: every adoption for the old text
refuses G014, and every check under it with it. So nobody can keep an adopted measure while
quietly changing the sentence it was adopted for, or the reverse.

### 5.2 The adoption act

Payload, signed as bytes (LF line ends, no trailing spaces):

```
reality-adopt 1
requirement R1 sha256:<text hash>
measure M1 sha256:<fragment hash>
by patsak
at 2026-11-14T15:02:00+01:00
```

A withdrawal signs the same payload with first line `reality-withdraw 1`.

- The `reality-req sign` helper (untrusted) prints the requirement text, the full fragment, the `says` text
  marked as the proposer's, and the number of earlier trials (5.3); then asks the person to type
  the measure's name and the first 8 hex digits of its hash; then signs. There is no yes/no prompt
  and no default answer, so pressing Enter adopts nothing.
- Signature: `ssh-keygen -Y sign -n reality-adopt` with the person's key, checked with
  `ssh-keygen -Y verify -f <allowed_signers> -I <person> -n reality-adopt`, where the
  allowed_signers file is given on the command line, never read from the ledger (Patsak, Q1).
  Builds and tests use a throwaway key generated on the box at run time, with the comment
  `REALITY-TEST-KEY-NOT-PATSAK`; it is never committed and never Patsak's key.
  OpenSSH is then trusted, as CPython is: listed, not re-checked.
- What a valid signature proves: the holder of that key signed this exact requirement text and
  measure at the stated time. It does not prove the person read them; that is the honest limit
  of any signature. It does stop an SI that writes to the ledger from adopting, unless it holds
  the key, which is why the key should have a passphrase and should not live where an agent can
  read it (Q1).
- The stated time is the signer's claim, not a trusted clock. Order in the ledger, not the time
  string, decides which adoption is current.

### 5.3 Trials before adoption

Every adoption prints `<k> trial run(s) of <M> before adoption (line(s) ...)`. Adopting a cut-off
after seeing it pass is allowed (the reviewer: the measure is often the output of the work), but
it is never hidden. This is principle 10.1's forking-paths answer applied to adoption.

## 6. Phrasing check results

Output is built only from fixed templates. The requirement text and the `says` text appear only
inside double quotes, labelled. Example, from the demo data:

```
check R1 by M1 on sha256:979cb9d6...9ba9
  requirement R1: "the upscaler must preserve artistic intent" (owner patsak)
  measure M1: sha256:77874fb1...5c24, proposed by grokbot, adopted by patsak at 2026-11-14T15:02:00+01:00
    (0 trial runs before adoption)
  the proposer's description (plain text, not checked; units in it are not checked): "per frame and channel, ..."
  M1 HOLDS on this data: 24 of 24 conditions hold.
  This is a statement about M1 on this data. Reality did not decide whether M1 is the right
  measure for R1's text; patsak's adoption did.
```

```
  M1 DOES NOT HOLD on this data: 16 of 24 conditions hold, 8 do not.
    fragment line 4: atmost(...) - the condition says at most 4; computed from the bytes it is 4.3888916015625
    ...
```

```
  M1 was NOT CHECKED on this data: the v4 checker refused fragment line 0 [F001]: no supplied file has sha256:...
  Nothing follows about M1 or R1.
```

Rules:
- The verdict word is HOLDS / DOES NOT HOLD / NOT CHECKED, always with the measure's name in the
  same sentence. Never "passes R1", "R1 is met", "satisfied", "preserved", "fair", "valid",
  "verified", "correct", "good".
- Test `test_wording`: render every template with sentinel texts and assert that none of those
  words, and no word of the requirement or `says` text, appears outside the quoted spans.
- The closing sentence of HOLDS is fixed and always printed. It cannot be turned off.
- Values come from the v4 output verbatim (exact rationals or terminating decimals).

## 7. Running a check (invariant 5)

`check R by M on D` and `try M on D` build the program

```
file d = sha256:<D>
let t = tsv(d)              (or csv(d), by the data file's declared reader)
<the fragment's bytes, unchanged>
```

and give it to `reality4.kernel.check` in-process, with D supplied as in `--files`. The branch
then reads the kernel's per-line results: lines 1-2 are the binding (any refusal there is NOT
CHECKED), fragment lines are numbered from 1 in output. Conditions that formed and printed
`holds` count as holding; V001 item 5 on a condition counts as not holding; anything else makes
the whole result NOT CHECKED. Because G022 forbids `is` in fragments, V001 item 5 can only come
from a comparison (kernel.py line 741 at HEAD).

The v4 kernel is not changed. The dataset machinery (readers, exact numbers, W1/W2, bounds) is
therefore the regression suite underneath, and the v4 test suite must pass unchanged at every gate.

## 8. Worked demo: "the upscaler must preserve artistic intent"

All numbers below were computed on the box on 3 Nov 2026 with the v4 checker from a clean
`git archive` of HEAD 760acc9, and recomputed independently with Python `fractions`; all 48
values agree. Files: `demo/`.

### 8.1 Frames

`demo/render_and_measure.py` renders 4 frames at 256x160 with integer arithmetic: a teal-to-amber
sky gradient (the "look"), a sun disc moving 12 px per frame, a dark hill, and two 1-pixel power
lines (fine detail). Each frame is averaged 2x2 to 128x80, then upscaled back three ways:

- `nearest`: each pixel repeated 2x2;
- `bilinear`: weights 1/4, 3/4 per axis, integer, rounded;
- `stylised`: bilinear, then saturation pushed by 5/4 around luma and a warm shift (+8 red, -8 blue).

The resolution was chosen so 256 x 160 = 40,960 = 2^13 x 5, so every per-frame mean is a
terminating decimal. `pixels.tsv` has one row per pixel per frame per method (491,520 rows); the
`out_<method>.tsv` files are its three parts (163,840 rows each; columns frame, ref_r, ref_g,
ref_b, out_r, out_g, out_b, ref_edge, out_edge). The edge flags (luma step of at least 40 to the
left or upper neighbour) are computed by the untrusted producer, not by the checker (Q3).

### 8.2 Script, step by step

1. **Refusal.** `task T1 = deliver R1 assigned_to studio` gives
   `G001 refused: task T1 assigns R1 ("the upscaler must preserve artistic intent") as work with a done-condition, but R1 has no adopted measure, so nothing decides when it is done. Measures for R1: none. ...`
2. **Proposal task.** `task T2 = propose R1 assigned_to grokbot` forms.
3. **Candidates.** grokbot proposes, status PROPOSED, listed unranked:
   - M1 grade drift (`M1.fragment`, sha256:77874fb1...5c24): for each of 4 frames and each channel,
     `mean(out_c) - mean(ref_c)` at most 4 and at least -4 (24 conditions, 12 shown values).
   - M2 edge retention (`M2.fragment`, sha256:04b20068...e4a2): for each frame, the share of
     reference edge pixels that are edge pixels in the output, at least 0.5 (4 conditions).
   A third candidate, mean absolute error per sample, is listed in the demo as proposed but has no
   fragment yet (it needs a per-pixel absolute difference column from the producer).
   `check R1 by M1 on ...` at this point is G002.
4. **Adoption.** Patsak adopts M1, live, with his key; the tolerance is his: ±4 levels (Q2,
   answered 09:22). Status ADOPTED.
5. **Checks** (`check R1 by M1 on <each out_ file>`), results from `demo/check-M1-*.out`:

| data | M1 result | largest drift values (8-bit levels, exact) |
|---|---|---|
| nearest (0d6d1bd1...869c) | HOLDS, 24 of 24 | red +0.2978271484375 (f3), blue +0.148876953125 (f3) |
| bilinear (979cb9d6...9ba9) | HOLDS, 24 of 24 | red +0.50947265625 (f3), blue +0.18671875 (f3) |
| stylised (0ba99fa7...cc39) | DOES NOT HOLD, 16 of 24 | red +4.3888916015625 to +4.403466796875 (over +4 in all 4 frames), blue -7.134326171875 to -7.12861328125 (under -4 in all 4), green +1.25224609375 to +1.253369140625 (within) |

   Verified at gate A with ±4, not assumed: the 8 conditions that do not hold are red `atmost 4`
   and blue `atleast -4` in each frame. Red is over by only about 0.39 levels; a tolerance of 4.4
   or more would let red hold.

6. **Formed is not right, shown on screen.** `try M2 on <each>` (trials, labelled as saying
   nothing about R1), from `demo/check-M2-*.out`:

| data | M2 trial | edge share per frame f0, f1, f2, f3 (exact) |
|---|---|---|
| nearest | holds, 4 of 4 | 803/1512, 806/1515, 806/1512, 806/1515 |
| bilinear | does not hold, 0 of 4 | 142/1512, 146/1515, 149/1512, 154/1515 |
| stylised | does not hold, 0 of 4 | the same as bilinear |

   Bilinear HOLDS under the adopted M1 while keeping 142 of 1,512 reference edge pixels in frame
   f0. The output does not resolve this, and must not: M1 holding is a fact about colour means,
   and whether R1 is about colour means was Patsak's adoption. This is the reviewer's "complete
   is not correct", one level up, and the point of the demo.
7. **Tamper.** Edit `c = 4` to `c = 8` in `M1.fragment`, rerun: every check by M1 is G014 (the
   fragment is no longer the one adopted). Edit the requirement text: G014 likewise. Nothing
   passes quietly under a different measure.

Run time on the box: one M1 check about 6.4 s wall, one M1+M2 sweep of the three files about
21 s (8 cores; the checker runs single-threaded). Laptop times are unknown (Q6).

### 8.3 "drops should feel fair" (included, Patsak Q8)

Requirement R2 = "drops should feel fair", owner patsak. Data (`demo/make_drops.py`, stdlib):
two drop tables with **one row per equal-weight slot**, 1,000 slots each, so a roll picks a slot
with equal chance and a tier's configured probability is its slot count / 1,000, which v4's
`share()` counts exactly. Both are published as common 79%, uncommon 15%, rare 5%, legendary 1%.

- `drops_published.tsv` (ae92af6e...c5b3): 790 / 150 / 50 / 10 slots.
- `drops_shaded.tsv` (1f93834f...7136): 790 / 150 / 54 / 6 slots.

Candidates, both proposed by grokbot:
- F1 published odds (`F1.fragment`, d57a76b2...c299): each tier's share equals its published
  odds (atleast and atmost the same value; 8 conditions).
- F2 floor (`F2.fragment`, 458a038a...a477): each tier has at least 1% of the slots (4 conditions).

| data | F1 | F2 |
|---|---|---|
| published | HOLDS, 8 of 8 (790/1000, 150/1000, 50/1000, 10/1000) | holds, 4 of 4 |
| shaded | DOES NOT HOLD, 6 of 8: rare is 0.054 (over 0.05), legendary 0.006 (under 0.01) | does not hold, 3 of 4: legendary 0.006 |

What these say and what they do not:
- F1 is about the **configured table**, not about what players saw. A table that matches the
  published odds can still produce long dry streaks; whether that "feels fair" is exactly the part
  F1 does not measure, and its HOLDS says only that the slot counts match the published numbers.
- Not expressible in v4 today, so not offered as measures: a streak or pity rule ("at most k drops
  in a row without a rare"; v4 has no run-length computation); whether an observed drop log is
  consistent with the published odds (that is a significance test, and v4 has no binomial or
  other test for it; a band on an observed share would be plain arithmetic about one log, not a
  test); weighted tables written as weights rather than slots (`share()` counts rows, not a
  weight column).

## 9. Reused versus new, with a rough line estimate

Reused unchanged: the v4 trusted base, 9,539 lines at HEAD 760acc9 (`wc -l` of the 13 files listed
in `v4/README.md`; the README's own table still says 9,253), and the core concepts in section 2.
`v0`-`v3`, `core/`, `checker/harness/` and `v4/` are not edited.

New, in a new folder `req/` (package `reality_req`), trusted unless marked:

| part | lines (rough) |
|---|---|
| ledger syntax (statements of section 3, reusing the core lexical rules by import or copy) | 200 |
| formation rules and statuses (section 3.2, codes of section 4) | 250 |
| fingerprints and adoption verification (5.1, 5.2; calls `ssh-keygen -Y verify`) | 80 |
| compose and run (section 7) and mapping the kernel's results | 120 |
| output templates (section 6) | 100 |
| CLI (`check`, `adopt`, `status`) | 80 |
| **trusted total** | **about 830; proposed cap 900, raised only by measured amounts, as v4 does** |
| `adopt` signing prompt (untrusted: what it writes is checked by 5.2) | 60 |
| tests: one per G code and each message, wording test, tamper tests, status transitions, demo outputs byte for byte | 600-800 |
| demo producer (`demo/`, untrusted) | exists, 100 |

## 10. Build plan with gates (all dates 2026, Europe/Berlin)

Work in a new branch `req-step2` from 760acc9 in a separate worktree: the current working tree has
uncommitted changes in `v4/` (23 files, `git diff --stat`) that are not part of this design and
should not be carried over. Nothing is pushed.

| gate | by | done when |
|---|---|---|
| A | Tue 4 Nov | Patsak has answered the open questions that block (Q1, Q2, Q4, Q6); spec frozen as SPEC.md |
| B | Thu 6 Nov | ledger syntax, statuses and every G code with its exact message; one test per code; v4 suite passes unchanged |
| C | Fri 7 Nov | `check`/`try` through the v4 kernel; the demo results of 8.2 reproduced byte for byte from `demo/` |
| D | Sat 8 Nov | adoption signing and verification; tamper tests (text edit, fragment edit, tool adopts, wrong owner, unsigned, `at now`) all refuse with the right code |
| E | Sun 9 Nov | wording test; mutation sweep over `req/` in the style of `mutation-v4` (each mutant must change a test result or be explained) |
| F | Tue 11 Nov | demo runs end to end on Patsak's laptop from a clean install; outputs identical to the box's (same bytes); timings measured |
| G | Wed 12 Nov | ready: trusted line count measured and logged; README states what the demo shows and what it does not; a printed fallback of every screen in case the laptop fails |

Thu 13 Nov is buffer. If gate D slips, the fallback is unsigned adoption with every output line
saying "adopter not verified" (Q1); the other gates do not depend on it. Not in this plan: Lean
models of the status machine (the transitions are small enough for a TLA+ or Lean check after
the jam) and CSV data.

## 11. Decisions I made (each reversible, for Patsak to overrule)

- D1. Requirement text is opaque; no word lists. Every requirement needs an adopted measure to be
  delivered or checked, whatever it says.
- D2. A measure is a hashed v4 fragment, not a new measure language. Cost: measures are verbose
  (M1 is 41 lines). Benefit: no new arithmetic in the trusted base.
- D3. One owner per requirement; only the owner adopts.
- D4. A check needs `by <M>` even when only one measure is adopted, as `same` needs `[R]`: the
  output always names what was checked.
- D5. Adoption and withdrawal are signed with `ssh-keygen -Y`; keys come from an allowed_signers file outside the ledger.
- D6. NOT CHECKED is separate from DOES NOT HOLD; only V001 item 5 on a condition is DOES NOT HOLD.
- D7. Proposals are unsigned; the proposer field is recorded, not verified.
- D8. Trials are allowed on unadopted measures, change no status, and are counted in the adoption
  record.
- D9. The G code letter, and reusing T001, E004, N001, N002, F001/F002 unchanged where the case is
  the same.

## 12. Open questions for Patsak

- Q1. **Answered: Patsak's own SSH key on his MacBook, ssh-keygen -Y sign/verify; a throwaway box
  key for builds and tests.** Signing: `ssh-keygen -Y` with an ed25519 key on the laptop (D5), or reuse the pure-Python
  P-256 verifier in `checker/harness/sign.py` (copied, not edited) with a key from openssl, or
  unsigned for the demo with "adopter not verified" printed? Where should the key live so that no
  agent on the laptop can read it?
- Q2. **Answered: ±4 levels.** The cut-off in M1. `c = 2` levels was my placeholder. The adoption must be yours, so pick it
  at the demo or before; the trial count will show whether you saw results first.
- Q3. **BB's call: M2's edge script runs outside the checker and is labelled so in the output.** M2's edge flags are computed by the untrusted producer, so the checker only counts them.
  Fine for the demo, or should the demo use only measures whose arithmetic runs entirely in the
  checker (M1 does; pixel extraction from frames is outside the checker either way)?
- Q4. **BB's call: withdrawal is in v1; replacing is withdraw + adopt, both recorded.** Should replacement and withdrawal be in v0 at all, or should an adopted measure be final
  for the demo?
- Q5. **BB's call: one owner per requirement.** A studio requirement often has several stakeholders (art director, engineering lead). One
  owner (D3), or adoption by each named owner?
- Q6. **BB's call: the box suite's Python (CPython 3.13); the MacBook's needs are in demo/README.md.** Which laptop and OS for the jam, and is Python 3.13 there? The v4 checker needs it; one M1
  check takes about 6.4 s on the box.
- Q7. **BB's call: units in the description as plain text, stated as unchecked.** v4 TSV numbers carry no unit, so "levels of 8-bit RGB" lives only in the unchecked `says`
  text. Accept for the demo, or add a unit to the data binding (new trusted code)?
- Q8. **Answered: yes, with one row per equal-weight slot (8.3).** Include "drops should feel fair" as a second example, using variant (a) with one row per
  equal-weight slot, or keep the demo to the upscaler?
- Q9. **BB's call: a deliver task names its data (G005).** Should `deliver` tasks also name the data they will be checked on (a file hash, or a data
  layout the delivery must match), so the done-condition is fully stated when the task is given?

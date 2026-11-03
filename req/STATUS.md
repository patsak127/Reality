# req/ status at gate G (3 Nov 2026)

- Trusted lines (req/src/reality_req, without the untrusted sign.py): 668 of the 900 cap
  (form 299, syntax 133, say 111, run 57, __main__ 43, bind 24, __init__ 1). v4's trusted base is unchanged
  at 9,539 lines; v0-v3, core/ and checker/harness/ are untouched (`git diff 760acc9` is empty for them).
- req tests: 47 passed (box, CPython 3.13; 46 before the playtest example). v4 suite at gate D code: 1484 passed, 4 skipped, 0 failed.
- Demo: `python req/demo/demo.py --work DIR`; expected output in `demo/expected/transcript.txt`
  (also the printed fallback). MacBook key steps: `demo/README.md`.

## Known limits (not done, on purpose)

- Mutation sweep (gate E, second run): 318 killed, 8 survived, 1 not valid Python. The 8 were not
  investigated further (Patsak, 3 Nov 10:24: no rigour beyond what the demo needs). They are:
  syntax.py:47 (`> 127` vs `>= 127`; U+007F is refused earlier as S014, so likely equivalent);
  form.py:38 (`blank()` and/or); form.py:200 and :266 (the withdrawn-history test, 4 mutants);
  form.py:282 (subject of check_head, an unused argument for checks); run.py:39 (a comment).
- Proposals are not signed: who proposed a measure is what the ledger says.
- Edge flags for M2 are computed by render_frames.py, outside the checker.
- Units are plain text in the measure description and are not checked.
- Fair drops: no streaks, runs or significance tests (v4 cannot say them).
- Playtest example: made-up logs (make_playtest.py), not Valve data; 37 of 50 vs 80 percent is a count, no significance test.
- MacBook timing not measured; the box run takes about 35-45 s.
- M1 at +-4: stylised red exceeds the tolerance by only about 0.39 levels.

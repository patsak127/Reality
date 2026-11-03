# Opus 5.5 max review of v3: verdicts under v4 (25 Oct 2026, 21:35 CET)

Copied from ../../../../review-opus55max-v3/findings (the .md write-ups left out). EXPECTED.tsv's
`#### opus55max-v3` section records v4's verdict for every line.

Fixed by v4 (the repro now refuses, or forms where the review found an overcorrection):
- hit 1 (01, idle values): S008 on every line, by W1/W2.
- hit 2 (02, `"` literal): S008/S011, by W1 (no readable cell holds `"`).
- hit 3 (03, locale): forms under every locale (bytes paths); the env matrix checks it.
- hit 4 (04, memory): R006 (literal length in the sort size) before any output is built.
- hit 8 (08, empty cells / blank header in BIDS TSVs): B00 (B04 underneath).
- 12, 13 (overcorrections): form. 14: plain multi-column forms, one-column T003, BIDS B00.
- 15: B00 (participants without a folder; Reality's own call). 16: forms, no crash.
- 19, 19b (tolerance aliasing): S012 by value identity.
- hit 5 (05): B00 (B30, S0265: run-1 vs run-01 change which sidecar applies).
- hit 6 (06): B00 (B30, S0495/S0510: phasediff JSON vs any image JSON give different IntendedFor).
- hits 7, 10 (07, 07b, 10): B14. S0132 makes a TSV at any level metadata; v4 does not implement
  inherited TSVs. 21g (sub-01/notes.json) is now read as metadata, B03, the same as 21f; 21i B14.
- hit 9 (09, 09b, 09c): B00 (B19: phenotype and events dictionaries checked; a dictionary
  without its TSV refuses).
- overcorrection 11 (11): forms; func/ events dictionaries are metadata.

After Phase E (the register and B30 choice points):
- 21a-i (rules coverage): 21a-c, e-h B00, 21i B14, 21d forms (EXPECTED.tsv); the register they
  rest on is one reader's reading (KNOWN-OPEN).

17, 18, 18b, 20, 20b, 24 need generated inputs (F001 here); tests/test_repros.py and
tests/test_v4_*.py rebuild them in code where v4 has a test for the finding.

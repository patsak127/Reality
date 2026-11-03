"""The acceptance lists of the principle spec §5 (F = must form, N = must not form), as
programs. test_acceptance.py runs them; tools/acceptance_table.py prints the results table.

Placeholders: {BOX} manifest of the box copy of ds001734; {CMP} manifest of the FABRICATED
complete copy (bidsfix.py); {P} participants.tsv of ds001734; {EV} sub-001 run-01 events file;
{DEC} a made-up decisions table (test fixture, see DECISIONS below).
"""

P = "d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8"
EV = "8f4461b0dcdc1d8e8d9ae1975a99d0476d95e8083432cf586f2508ebe8f8be53"
# A made-up two-column table in the shape of NARPS decisions (test fixture, not NARPS data).
DECISIONS = "teamID\tH9\n50GV\tYes\n3C6G\tNo\n"

CMP_HEAD = "dataset d = sha256:{CMP}\nlet b = bids(d)\nlet r = recording(b, \"001\", \"MGT\", \"01\")\n"
BOX_HEAD = "dataset d = sha256:{BOX}\nlet b = bids(d)\n"

# (id, fixture, program, expectation, note)
# expectation: "formed" (every claim forms) or a list of refusal codes, one per refused line, in order.
CASES = [
    ("F1", "complete", CMP_HEAD + 'claim count(where(participants(b), eq("group", "equalRange"))) is 54\n', "formed",
     "Complete: forms only on a complete dataset; here the fabricated complete copy (the real one is checked on the PC)"),
    ("F2", "complete", CMP_HEAD + 'claim share(where(participants(b), eq("group", "equalRange"))) is 54/108\n', "formed",
     "Complete: a share of a set, exact"),
    ("F3", "complete", CMP_HEAD + "claim onset(r, 1) is 4.071 s\n", "formed",
     "Complete: 'recorded as 4.071 s', relative to the BOLD file the sort names by hash"),
    ("F8", "complete", CMP_HEAD + "claim volumes(r)\n", "formed",
     "Complete: 453 here because the fabricated copy is made with 453 volumes (bidsfix.complete_copy); the real ds001734 also gave 453 on the PC (Phase H, at abad0e4)"),
    ("F11", "complete", CMP_HEAD + "claim tr(r) is 1 s\n", "formed",
     "Complete: 'recorded as 1 s', from the root task-MGT_bold.json under 1.0.1 inheritance"),
    ("F12", "box", "file p = sha256:{P}\nlet t = tsv(p)\nclaim rows(t) is 108\nclaim count(where(t, eq(2, \"equalRange\"))) is 54\n", "formed",
     "file-level, plain TSV reader, no BIDS"),
    ("N1", "box", "file p = sha256:{P}\nclaim activity(tsv(p), \"vmPFC\")\nclaim exceeds(vmpfc(tsv(p)), c = 3.1)\n", ["S002", "S002"],
     "no reader produces a brain sort"),
    ("N2", "dec", "file t = sha256:{DEC}\nclaim found(cell(tsv(t), 1, 2))\nclaim author(t)\n", ["S002", "S002"],
     "no form asserts authorship"),
    ("N3", "dec", "file t = sha256:{DEC}\nclaim supported(cell(tsv(t), 1, 2))\nclaim decision(tsv(t), 1)\n", ["S002", "S002"],
     "a Yes cell is bytes; only 'holds the bytes Yes' forms (see N3b)"),
    ("N3b", "dec", "file t = sha256:{DEC}\nclaim cell(tsv(t), key(1, \"50GV\"), 2) is \"Yes\"\n", "formed",
     "the honest form: the row keyed 50GV holds the bytes Yes in column 2 (F4's shape, on a TSV)"),
    ("N4", "box", "file p = sha256:{P}\nclaim fwe(tsv(p), alpha = 0.05)\nclaim significant(tsv(p))\n", ["S002", "S002"],
     "no correction can be recomputed at this floor"),
    ("N5", "box", "file p = sha256:{P}\nclaim quantile(tsv(p), level = 0.001)\nclaim exceeds(t(tsv(p)), c = 3.1)\n", ["S002", "S002"],
     "the statistic's sort is unknown"),
    ("N6", "dec", "file t = sha256:{DEC}\nclaim contradicts(tsv(t), cell(tsv(t), 1, 2))\n", ["S002"],
     "no standard links a map to a decision"),
    ("N7", "box", "file p = sha256:{P}\nclaim saw(where(tsv(p), eq(2, \"equalRange\")), \"gambles with an equal range\")\n", ["S002"],
     "group levels are bytes; their prose meaning is read by nothing"),
    ("N8", "old", None, "all-refused", "v1 NARPS demos 1, 2, 3 and 5 (tests/old/narps-*.rl): v1 syntax has no form in v2"),
    ("N9", "box", "entity Participant\nfile t = sha256:{P}\nindividual s1 : Participant from t row 1\n", ["P008", "P008"],
     "the author cannot declare what a row is"),
    ("N10", "complete", CMP_HEAD + "claim activity(r, \"vmPFC\")\nclaim increases(onset(r, 1), \"loss\")\n", ["S002", "S002"],
     "even with BOLD, BIDS defines recordings, not anatomy"),
    ("N11", "box", "artifact paper = ref doi \"10.1038/s41586-020-2314-9\"\nfile x = doi:10.1038/x\n", ["P008", "P003"],
     "an unread reference has no form; a file is named only by its bytes' hash"),
    ("N13", "complete", CMP_HEAD + "claim species(participant(b, \"001\"))\nclaim extra(participant(b, \"001\"), \"species\")\n", ["S002", "V002"],
     "no byte states a species and 1.0.1 has no species rule; no default is used"),
    ("N14", "complete", CMP_HEAD + "claim count(where(participants(b), eq(\"sex\", \"F\")))\nclaim female(participants(b))\n", ["V002", "S002"],
     "1.0.1 defines no sex column; see N14b for what forms"),
    ("N14b", "complete", CMP_HEAD + "claim count(where(participants(b), eq(\"gender\", \"F\"))) is 60\n", "formed",
     "the honest form: 60 rows hold the bytes F in the ExtraCell column gender"),
    ("N15", "mini-1.2.0", "dataset d = sha256:{MINI}\nclaim count(participants(bids(d)))\n", ["B02"],
     "BIDSVersion 1.2.0 has no reader"),
    ("N15b", "mini-nodesc", "dataset d = sha256:{MINI}\nclaim count(participants(bids(d)))\n", ["B01"],
     "no dataset_description.json"),
    ("N16", "box", "file e = sha256:{EV}\nclaim number(cell(tsv(e), 1, 1)) is 4.071 s\nclaim onset(e, 1)\n", ["U002", "S007"],
     "an onset in seconds is relative to a BOLD file the claim does not name; see N16b for what forms"),
    ("N16b", "box", "file e = sha256:{EV}\nclaim number(cell(tsv(e), 1, 1)) is 4.071\n", "formed",
     "the honest file-level form: the cell holds the decimal 4.071, no unit"),
    ("N17", "box", BOX_HEAD + 'claim count(where(participants(b), eq("group", "equalRange"))) is 54\n', ["B00", "N003"],
     "the box copy does not conform: 432 events files lack their BOLD files"),
]

OUT_OF_SCOPE = [
    ("F4", "needs an xlsx reader (narps_results.xlsx); not in this build. N3b shows the same claim shape on a TSV."),
    ("F5", "needs a NIfTI value reader (voxel values with scl_slope/scl_inter); this build reads NIfTI headers only."),
    ("F6", "needs the NIfTI value reader, a hashed atlas and the language's fixed resampling rule."),
    ("F7", "needs the NIfTI value reader and IntentCode/XformCode sorts."),
    ("F9", "needs the BOLD data (Complete) and the language's own GLM (spec §8 item 5)."),
    ("F10", "quantities and stipulated questions are not in this build (file-level claims only); see README, 'Theseus'."),
    ("N12", "covered by tests/test_findings.py: each formed v1 finding rewritten in v2 syntax"),
]

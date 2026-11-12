"""SPEC 9.1: the "no uncharged loop" lint (Phase C leftover, built 25 Oct 2026).

Every loop in the trusted base (for, while, comprehension) sits in a function that charges the
step meter (a call to `.add(` or `._cached(`, which charges before it builds), or the function is
listed below with its exact loop count and the reason its loops need no charge of their own. A
new loop in an unlisted, uncharged function fails; so does a changed count, so each change is
looked at again. The reasons:
- PROGRAM: bounded by the program's own bytes (statement, node and output bounds: R006, R014).
- CALLER: walks data whose size its caller has charged (named in the reason).
- FIXED: a constant number of turns.
- IO: reads a declared file in fixed chunks; bounded by the file's size, which the hash fixes.
- WITNESS: builds a certificate's or a model's inputs, bounded by the statement's literals and the model's bounds;
  evaluating them is charged against the witness bound (SPEC 4.5, R013).
- TOOL: not part of checking a program (manifest writer, CLI arguments, start-up tables).
This is a lint on the source, not a proof: a reason is the author's reading, kept short so a
reviewer can check each one. The K-factor test (test_v4_meter.py) measures the result."""
import ast
import os

from test_source import SRC, TRUSTED

# (I3) the search left the trusted base (search.py: its refusals' "none" are checked by cert.py, its solutions confirmed
# on bytes), but its loops still bound the checker's work: it is scanned like the trusted files.
SCANNED = TRUSTED + ["search.py", "build.py"]   # (BLD) build.py: the certificate inputs, confirmed on bytes, scanned like search.py

PROGRAM, CALLER, FIXED, IO, WITNESS, TOOL = "program", "caller", "fixed", "io", "witness", "tool"

BOUNDED = {
    ("keys.py", "_compile"): (3, TOOL, "builds the confusables table once at import"),
    ("keys.py", "is_key"): (1, CALLER, "one string the caller charged (a literal or a cell)"),
    ("keys.py", "is_header_name"): (1, CALLER, "one header name, charged with the header"),
    ("keys.py", "skeleton"): (2, CALLER, "one string's characters"),
    ("keys.py", "invisible"): (1, CALLER, "one string's characters"),
    ("keys.py", "lookalikes"): (1, CALLER, "labels_distinct and the column scope charge len(values) + 1"),
    ("syntax.py", "_tokens"): (8, PROGRAM, "the program text"),
    ("syntax.py", "parse_line"): (1, PROGRAM, "one statement line"),
    ("syntax.py", "measured_size"): (2, PROGRAM, "the program text"),
    ("syntax.py", "split_program"): (1, PROGRAM, "the program bytes"),
    ("syntax.py", "expr"): (1, PROGRAM, "one statement's tokens"),
    ("syntax.py", "group_program_lines"): (2, PROGRAM, "the program's lines (question continuations; SPEC-ORD)"),
    ("questions.py", "parse_weighted_pair_body"): (6, PROGRAM, "question clause lines (SPEC-ORD)"),
    ("questions.py", "_resolve_col"): (3, CALLER, "table header cells the caller already charged"),
    ("questions.py", "evaluate_weighted_pair"): (6, CALLER, "rows of the bound table; weight family size is program-bounded"),
    ("questions.py", "format_answer_lines"): (2, PROGRAM, "witness lines for one QuestionAnswer"),
    ("questions.py", "row_for"): (1, CALLER, "rows of the bound table"),
    ("sorts.py", "esc"): (1, CALLER, "a literal or cell, counted in the sort size (SPEC 9.2)"),
    ("sorts.py", "nodes"): (1, PROGRAM, "a sort, bounded by the node bound R006"),
    ("sorts.py", "files"): (1, PROGRAM, "a sort's nodes"),
    ("sorts.py", "render"): (1, PROGRAM, "a sort's nodes; output bounded by R014"),
    ("sorts.py", "__init__"): (1, PROGRAM, "a sort's direct parts"),
    ("readers.py", "sha256_file"): (1, IO, "hashes a file in CHUNK pieces"),
    ("readers.py", "_text"): (2, FIXED, "the ten separator characters (each find is charged by the caller's len(text)/64)"),
    ("readers.py", "_table"): (5, CALLER, "parse_tsv / parse_csv charge len(text)/64 + 1; lines and cells are at most the text; (A08) the size so far: the header's cells and each row's, once"),
    ("readers.py", "_csv_fields"): (3, CALLER, "one line, inside parse_csv's charge"),
    ("readers.py", "json_depth"): (1, CALLER, "the JSON text, charged by Store.json (_cached)"),
    ("readers.py", "parse_json"): (2, CALLER, "the JSON text, charged by Store.json (_cached)"),
    ("readers.py", "nifti_header"): (3, FIXED, "two byte orders, eight pixdim slots"),
    ("readers.py", "_check"): (1, FIXED, "at most seven dims"),
    ("readers.py", "_path_ok"): (2, CALLER, "one manifest path, charged with the manifest line"),
    ("readers.py", "make_manifest"): (4, TOOL, "the manifest writer (reality4 manifest), not a check"),
    ("readers.py", "locate"): (2, IO, "the roots and hints named on the command line for one hash"),
    ("readers.py", "under"): (1, IO, "one manifest path's components, each folder listed once (fix pass W1, W2)"),
    ("readers.py", "pairs"): (1, CALLER, "one JSON object's members, inside the JSON charge"),
    ("readers.py", "data_bytes"): (1, FIXED, "at most seven dims"),
    ("readers.py", "gz_head"): (1, IO, "at most MAX_GZ_HEAD compressed bytes in 64 KiB reads for a 544-byte header"),
    ("bids101.py", "column_fails"): (3, IO, "the members of one column description, bounded by its JSON file's size"),
    ("bids101.py", "_index"): (1, CALLER, "one entity label"),
    ("bids101.py", "parse_name"): (2, CALLER, "one path's segments, charged with the manifest"),
    ("bids101.py", "_order_ok"): (2, FIXED, "a file name's entities against a list of at most five"),
    ("bids101.py", "classify"): (1, FIXED, "two extensions"),
    ("bids101.py", "nearest"): (1, FIXED, "three neighbours"),
    ("bids101.py", "choice_point"): (1, FIXED, "the readings of one choice point (two or three)"),
    ("bids101.py", "_cpan_version"): (1, CALLER, "the components of one CHANGES version, part of the text store.text charged"),
    ("bids101.py", "_closes_at_end"): (1, CALLER, "one line of CHANGES, part of the text store.text charged"),
    ("bids101.py", "changes"): (3, CALLER, "the lines of CHANGES; store.text charged len/64 + 1 for its bytes; C2: the ten separator characters, a fixed list and comprehension, as readers._text"),
    ("bids101.py", "_run_key"): (1, CALLER, "one file's entities"),
    ("bids101.py", "_inherit_once"): (7, CALLER, "the folders on one path and their metadata, charged by Metas.get; JSON keys charged at parse; the clashes found among those keys (O5)"),
    ("bids101.py", "inherited"): (5, CALLER, "the keys _inherit_once returned, and the paths of one key in both readings (O13)"),
    ("bids101.py", "bids_tsv"): (3, CALLER, "parse_tsv charged len(text)/64 + 1; cells are at most the text"),
    ("bids101.py", "of"): (1, CALLER, "the manifest, which read() charges one step per path; read() calls of() a fixed number of times"),
    ("bids101.py", "__init__"): (1, CALLER, "Metas index: the manifest entries load() charged"),
    ("bids101.py", "dictionary"): (1, CALLER, "one JSON's keys, charged at parse"),
    ("bids101.py", "intended"): (3, CALLER, "one fieldmap's images and IntendedFor lists, inside load()'s charge"),
    ("kernel.py", "fmt"): (2, CALLER, "the factors 2 and 5 of a denominator, bounded by its digits (R007)"),
    ("kernel.py", "union"): (1, PROGRAM, "a statement's values"),
    ("kernel.py", "is_square"): (1, PROGRAM, "the nesting of one difference() argument (Part B 5b)"),
    ("kernel.py", "slots"): (2, PROGRAM, "a call's parameters"),
    ("kernel.py", "tr_of"): (3, CALLER, "the sidecars of one folder that set RepetitionTime, each read and charged by bids(d)"),
    ("kernel.py", "scope_ok"): (1, CALLER, "headers or labels the caller charged (column lookup, key_column_scope)"),
    ("kernel.py", "_table_size"): (2, CALLER, "memory size of a table already charged at parse"),
    ("kernel.py", "sub"): (1, FIXED, "the kinds named in one error message"),
    ("kernel.py", "c_share"): (3, PROGRAM, "the conditions written in the statement"),
    ("intstep.py", "form"): (1, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "value"): (1, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "lin"): (2, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "rest"): (1, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "tighten"): (4, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "normalize"): (2, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "hopeless"): (1, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "lower_rule"): (4, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "delta"): (1, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "branches"): (1, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "ub"): (2, CALLER, "one system's atoms and their coefficients; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "pick"): (2, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "pin"): (1, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("intstep.py", "decide"): (13, CALLER, "one system's atoms and variables; every call is counted against the R013 bound (SPEC-EXACT 8)"),
    ("decide.py", "lin"): (3, CALLER, "one form: at most the slot's row types and the named cells, charged in Model.steps"),
    ("decide.py", "value"): (1, CALLER, "one form, as lin"),
    ("decide.py", "ground"): (1, CALLER, "one atom's form, as lin"),
    ("decide.py", "prune"): (3, CALLER, "one value's branches and their atoms, charged in Decide.branches"),
    ("decide.py", "key_of"): (2, PROGRAM, "one key()'s arguments"),
    # flagged once the fix pass's precise lint (only the step meter's .add charges) met decide.py at the merge of v4-fixes:
    ("decide.py", "named"): (3, PROGRAM, "the statement's nodes (R006), once per Model.cases"),
    ("decide.py", "agg_cases"): (13, CALLER, "the statement's aggregates (R006); the cases it yields are cut at MAX_CASES + 1 by Model.cases, which charges each"),
    ("decide.py", "slot_bears"): (1, CALLER, "the copy slot's cases, at most MAX_CASES; each one's work is added to the budget, R013 past MAX_WITNESS_STEPS"),
    ("decide.py", "run"): (2, PROGRAM, "the certificate's files, one per name of the statement (item 7: a Periodic file keyed by its sha); 1 -> 2 at BLD (each checked by store_ok); 2 -> 3 at F02 (a certificate file past MAX_TEXT_FILE: OverRead); 3 -> 2 at B02 (the check moved to Decide.input)"),
    ("decide.py", "rename"): (1, PROGRAM, "one statement's nodes, bounded by R006 (Decide.slot_bears, fix pass R3)"),
    ("decide.py", "inside"): (1, CALLER, "decimal places until a step fits between two bounds: the digits of the cutoffs and of values the solver chose"),
    ("search.py", "c"): (2, CALLER, "one log line's terms (two from fm, a premise's variables from presolve and tidy), as the atom it stands for"),
    ("search.py", "needed"): (6, CALLER, "one leaf's log, once backward and once to renumber; charged in Model.no (side work)"),
    ("cert.py", "split"): (18, CALLER, "one split's children and the node's atoms (at most MAX_CASES nodes an option, Model.solve1); (L1) the model's cases checked by cover, the splits counted by kind; 13 -> 14 at F01 (each child's atoms kept for its leaf); 14 -> 15 at G02 (each child's case fingerprinted); 15 -> 18 at C01 (the children checked exact and copied, the model's cases kept)"),
    ("cert.py", "leaf"): (6, CALLER, "a node's atoms, which its leaf's system holds (checked by check, charged); (L1) the model's atoms of its case and its tail facts against the system's, paid before"),
    ("cert.py", "done"): (1, CALLER, "an option's nodes, at most MAX_CASES (Model.solve1)"),
    ("cert.py", "exact"): (6, CALLER, "(C01) one value the search hands the checker (a system, a log, a node's atoms, a rule, a point), each object once (memo): linear in what the search built, as key() over the same system"),
    ("cert.py", "options_closed"): (1, CALLER, "find()'s options, each a case and branch charged in Decide.branches"),
    ("cert.py", "div"): (5, CALLER, "one line's entries, charged by check (the line it divides was charged when made)"),
    ("cert.py", "shares_zero"): (13, CALLER, "the system's atoms (paid) and the four forms at the 1 + 2v + v(v-1)/2 points, each point paid before it is evaluated; v at most the slot's row types"),
    ("cert.py", "form"): (3, CALLER, "the terms of one form (a product's four, a range atom's two) and their forms' entries, paid by prange_split per atom"),
    ("cert.py", "same"): (2, CALLER, "two forms' entries, paid by prange_split per atom"),
    ("cert.py", "has"): (1, CALLER, "a child's new atoms, paid by prange_split (len(new) + 1 per fact)"),
    ("cert.py", "prange_split"): (20, CALLER, "a split's children (at most three) and each child's new atoms against at most seven range facts and their 28 products, paid before (29 (|N| + |S| + 4) a new atom); the cover over the children's ranges; 19 -> 20 at D01 (each child's ranges checked equal: its new atoms, already paid)"),
    ("cert.py", "ratio"): (3, CALLER, "one factor's entries and N's, paid by prange_split per atom"),
    ("cert.py", "implied"): (1, CALLER, "(L1) the parent's system (the model's atoms of its case, the option's and the node's), paid before it is compared"),
    ("cert.py", "key"): (2, CALLER, "(L1) one system's atoms and their entries, paid by its caller (proved, split, implied) before"),
    ("cert.py", "cover"): (4, CALLER, "(L1) a split's children (one per case of the model's disjunction, at most the model's cases) and each child's atoms against its case's, paid before"),
    ("cert.py", "proved"): (1, CALLER, "(L1) one shown system's atoms, paid before it is kept"),
    ("cert.py", "pin_split"): (15, CALLER, "(L5) a pin's four atoms and the parent's system, paid before (len(new) + the system's size); (B01) the two pinned variables against the system's atoms, within that charge"),
    ("cert.py", "vdeep_none"): (9, CALLER, "(L6) the values, the pieces, each n up to nmax (the rows the search tried, at most MAX_ROWS) and its multisets (the search's, at most MAX_CASES) or halving steps, paid per n and multiset"),
    ("cert.py", "vrange_none"): (2, CALLER, "(L6) each range against each piece, paid before (len(ivs)·len(K) + 1)"),
    ("decide.py", "n_range"): (4, CALLER, "(L6) the candidates' columns (as n_hit, which pays len(cs) per product)"),
    ("decide.py", "vnone"): (1, CALLER, "(L6) the ranges vranges returned (paid there)"),
    ("decide.py", "vranges"): (7, CALLER, "(L6) the candidates (var_cands, charged) and their products, paid per pair or product; each product's free and ruled-out types (its candidates)"),
    ("decide.py", "sums_shown"): (14, CALLER, "(L4) the points of 5.4 with sums (1 + 2v + v(v-1)/2, as w2_input made them and was charged for) and each point's count atoms, paid per point before"),
    ("decide.py", "tail"): (1, CALLER, "(L1) the option's atoms, as same_means reads them (charged by the checker's pay per fact)"),
    ("decide.py", "same_case"): (2, CALLER, "(L1) a case's slots and the aggregates' six fields: the model's case, charged when it was made"),
    ("decide.py", "nests"): (5, CALLER, "(L1) pairs of the option's means and their ends (as solve1 builds them, charged there: 2 |Ps|^2)"),
    ("decide.py", "presence"): (1, FIXED, "(L1) a type with rows, or none: two cases"),
    ("decide.py", "band_cases"): (1, FIXED, "(L1) the band's case and the two beside it: at most three"),
    ("decide.py", "half_need"): (4, CALLER, "(L1) the half cuts' candidates (half_cands, charged by solve1's half_cut) and the case's atoms"),
    ("decide.py", "disjunction"): (16, CALLER, "(L1) a split's model cases (nests, caps' products, a band, a gap, a float's binades: the same cases solve1 built and held) and the parent's atoms, charged by cover per child; (shape 3) spell; 15 -> 16 at 3.12b (layout: lay_cases)"),
    ("cert.py", "comb"): (3, CALLER, "a line's terms and their forms' entries; each term charged by pay before it is added"),
    ("cert.py", "rnd"): (3, CALLER, "one line's entries, charged by check (the line it rounds was charged when made)"),
    ("cert.py", "check"): (2, CALLER, "the log's steps, one pay each before its work"),
    ("cert.py", "intstep"): (11, CALLER, "the lines handed to the integer step: each paid; the merge paid variables x lines; intstep's calls paid after, its limit the steps left"),
    ("search.py", "fm"): (14, CALLER, "one system's atoms times the named cells; the atoms it makes are charged in Model.solve, their bytes before they are made (hold, BB's call 28 Oct 2026)"),
    ("decide.py", "bits"): (1, CALLER, "numbers whose bytes its caller charges before building (fm's P and N, lp's tableau, the integer atoms)"),
    ("decide.py", "same_rows"): (11, CALLER, "(3.7b) the statement's variances (twice), and per pair their cases' branch pairs, each charged its atoms + 1; m.find charges its own systems; the zero types per pair from its atoms (as var_cands)"),
    ("search.py", "joint_rows"): (15, CALLER, "(3.7b) the variances' answering cases (var_cands, charged per type), their types' readable values (SHORT inside an interval class, then dvals; sorted shortest first) and the multisets of them by size: at most MAX_CASES tried, each charged its rows, and W.MAX_WITNESS_STEPS; each tried multiset's two evaluations are the real code's, charged by it"),
    ("search.py", "back"): (3, CALLER, "the atoms fm kept for each named cell, charged in Model.solve"),
    ("decide.py", "__init__"): (152, PROGRAM, "(Model) the statement's nodes and literals (and its copy's for R3: twice R006); the row types are charged in Model.steps; 1 -> 35 when the fix pass's precise lint met it at the merge of v4-fixes, plus R3's two walks over both statements; 35 -> 38 for the operands of a difference of two variances (item 5b); 38 -> 36 when Part B (d) removed the unreachable named-rows-and-variance gate (two set comprehensions); 36 -> 34 at item 2 (the look-alike literals gate removed); 34 -> 35 at item 2b (participants: no statement reads column 1); 35 -> 41 at item 2c (recording(): its arguments; the named labels per entity, look-alike check); 41 -> 45 at R1 (recordings(): its arguments and tasks; each slot's one quantity; a mean, min or max's one set, a walk of each top); 45 -> 59 at R2 (the regions: each set and its parts' wholes, per (dataset, task) the types' membership in them, at most the statement's sets times the slot's row types, charged in Model.steps by selected); 59 -> 66 at item 3 (each recording's reads, nested labels, trial types per recording); 66 -> 69 at item 4 (participant(), extra() and number() of it; the label classes of participant_id); 69 -> 72 at the slot shapes (3.10: the statement's calls once, the files read by csv() and tsv(), nifti() and size(), the tsv() calls not under rows()); 72 -> 78 at the variance shape (3.7: its terms per top, the one-table gate, their ids); 78 -> 83 at tc1 (3.10: the number(cell(., r, 1)) reads, each tc file's tsv() and csv() calls, the widen() check); (Log) one system's premises, once; (shape 3) the number()-read byte ranges, checked for overlap (3); 87 -> 95 at item 4 shape 2 (a table read by size(): its checks over the statement's slots, nodes and tops, and its row types' least lines, R006); 95 -> 97 at shape 2's review (3.12a, 3.12b: each top's tsv()/csv() calls per slot; a one-column table's empty literal); 97 -> 107 at shape 1 (3.13: the rows()/count() arguments, the where()s on tsv() and their conditions, the files so read, the widen() check, the tsv() calls allowed; each tsv() literal's pieces into the csv columns read); 107 -> 108 at 3.13b (the tsv() calls read by number(), one walk over the statement's calls); 108 -> 109 at 3.13c (the aggregates of column 1, one walk); 109 -> 111 at 3.13d (the number(header(tsv(f), 1)) calls, one walk; the header names read past column 1, one pass); 111 -> 113 at 3.13e (the number(cell(tsv(f), key(...), 1)) calls, one walk, and their key columns); 113 -> 112 at 3.13f (the widen() NotT's walk removed); 112 -> 119 at 3.13h (a file read by both beside a size(): its width cases' types and least lines, the 'o' case's least width and next width); 119 -> 124 at 3.9a (two quantities of recordings: the quantities per slot, the events-file and tr gates, the aggregates' functions); 124 -> 125 at 3.9b (the read trial types' skeletons); 125 -> 126 at 3.8a (per named recording its sidecar's folder, over the others); 126 -> 129 at 3.8b (the look-alike participant and recording labels); 129 -> 135 at 3.9d (rs8: one partition of a dataset's sets for its two tasks); 135 -> 140 at 3.9e (each task's aggregates and counts over recordings() sets: the statement's nodes); 140 -> 139 at SRH (Log's premises moved to search.py); 139 -> 143 at F02 (the read-limited tables rl and each statement's reads of them rk, as sk); 143 -> 145 at G05 (each statement's tables and where() calls: wheres); G04c +2: the statements' events-file reads (evreads per top); 147 -> 152 at H07 (each statement's events files beside its tables, Model.rm)"),
    ("decide.py", "column"): (8, PROGRAM, "one column's literals and cutoffs; each class is probed and charged in readable; 7 -> 8 at item 4 (participant_id: only the label classes)"),
    ("decide.py", "text"): (6, PROGRAM, "spellings skipped because they are or look like one of the column's literals, plus the variant asked for (at most the named rows + 2)"),
    ("decide.py", "hclasses"): (1, FIXED, "two header classes, each probed and charged in readable"),
    ("decide.py", "table"): (8, CALLER, "a certificate input: at most MAX_ROWS rows per slot; witness.evaluate charges its reading; 6 -> 7 at item 2b (participants: each row's sub- label); 7 -> 8 at tc1 (3.10: one column, each row's first cell)"),
    ("decide.py", "readable"): (5, CALLER, "a probe of one row or one header, charged len/64 + 1 in Model.steps; 2 -> 3 at item 2b (participants: the rows compared without column 1); 3 -> 5 at tc1 (3.10: the rows' first cells, and the TSV reading's rows)"),
    ("decide.py", "selected"): (2, CALLER, "the slot's row types, charged in Model.steps"),
    ("decide.py", "undecided"): (3, CALLER, "the slot's row types and one where()'s conditions, as selected"),
    ("decide.py", "keyed"): (1, PROGRAM, "one key's pairs"),
    ("decide.py", "slot_cases"): (3, CALLER, "the cases of the rows a question names, at most MAX_CASES + 1 taken, each charged in Model.cases; (shape 1, 3.13) per csv width Wc of a file read by both readers its allowed types, then slot_cases1's cases"),
    ("decide.py", "slot_cases1"): (16, CALLER, "(shape 1) slot_cases' body over a given type list: the cases of the rows a question names, at most MAX_CASES + 1 taken, each charged in Model.cases"),
    ("decide.py", "tw_classes"): (24, CALLER, "(shape 1, 3.13) a file read by tsv() and csv(): its tsv() literals (the statement's), each one's pieces and a two-row probe table read by both readers, then per csv width Wc (at most the literals + 1) the row types, charged len(types) x len(Wc) in Model.steps; 20 -> 24 at 3.13a (per literal width whose columns are all read, the row types and their Wc cells, charged len(types) per width in Model.steps)"),
    ("decide.py", "tkey"): (1, PROGRAM, "(3.13e) a key()'s pairs (the statement's), mapped to the line's column"),
    ("decide.py", "literal"): (2, CALLER, "(shape 1 case 1, 3.13b) a Wc >= 2 tsv() line's cells 1..Wc (Wc at most the literals' widths + the read width + 1), read and joined"),
    ("decide.py", "tw_least"): (7, CALLER, "(3.13h) a row's least cells at csv width W0: the line literals (the statement's) twice, their pieces, the W0 columns, a 25-letter alphabet and the joined line; charged per (type, width case) by its caller in Model.steps (width x literals)"),
    ("decide.py", "tw_line"): (5, PROGRAM, "(shape 1, 3.13a) one line's bytes and pieces (a literal of the statement or a line of its csv literals) and a two-row probe table's cells, read by both readers"),
    ("decide.py", "wconds"): (1, PROGRAM, "(shape 1) a where()'s conditions, the statement's nodes"),
    ("build.py", "tw_rows"): (5, CALLER, "(shape 1) a certificate's rows (at most MAX_ROWS, held in bytes_of1) and their Wc cells, the literals' pieces per column"),
    ("build.py", "least_table"): (7, CALLER, "(G04) a certificate's rows (at most MAX_ROWS, held in bytes_of1) and their W cells, as table(); the filler name over 23 letters and the header's names"),
    ("decide.py", "cases"): (15, CALLER, "at most MAX_CASES cases (else R013), charged in Model.steps; with the named rows' pieces, at most MAX_CASES too (item 6 (d)); 10 -> 12 at R2 (the recording-set datasets' cases, at most MAX_CASES + 1 each); 12 -> 15 at 3.8b (a pt slot's named recordings, one ('rec', d) key each)"),
    ("decide.py", "size"): (2, CALLER, "the slot's row types and named rows, charged in Model.steps"),
    ("decide.py", "idsize"): (5, CALLER, "(G01) two recordings() sets' regions and kinds, charged with the model's recording variables (Model.steps); else size()"),
    ("decide.py", "let_marks"): (3, PROGRAM, "(G03) the statement as written and as judged, walked once together, and the program's lets (B0304: their own nodes, once)"),
    ("decide.py", "pair"): (1, PROGRAM, "(G03) let_marks' walk: one node's arguments"),
    ("decide.py", "letwalk"): (1, PROGRAM, "(G03, G05, G04c; WLK) the statement's calls, each let's once"),
    ("decide.py", "walk"): (1, PROGRAM, "(WLK) letwalk's walk: one call's arguments"),
    ("decide.py", "charged"): (2, PROGRAM, "(WLK) letwalk's statements and calls, once each"),
    ("decide.py", "subst"): (3, PROGRAM, "(G03) W._subst's walk of one statement: each call copied once, its arguments once and whether node is in them once"),
    ("decide.py", "scopy"): (3, PROGRAM, "(G03) subst's walk: each call copied once, its arguments once and whether node is in them once"),
    ("witness.py", "_same"): (1, PROGRAM, "(G03) a let's later use walked beside its first, once per use (the statement's nodes)"),
    ("decide.py", "case_atoms"): (90, CALLER, "the slots, their keys and row types, as size; the named rows and their aggregated columns, and one piece's order statistics (item 6 (d)); (e2) the summed types' pieces (pieces) and their ends; 22 -> 24 at item 2c (the recording value's atoms: one per named onset row); 24 -> 26 at R1 (a recording-set slot's tasks and its aggregates' names); 26 -> 29 at R2 (per region its state's atoms); 29 -> 31 at item 3 (a recording's onset and duration rows and its trial types); 31 -> 33 at item 4 (participant_id: per label class at most one row); 33 -> 34 at the slot shapes (3.10: a NIfTI file's dims within int16 in the NIfTI-1 case); (shape 3) each number()-read range's bounds; 35 -> 37 at item 4 shape 2 (a table read by size(): its row types' least lines, as size); 37 -> 40 at 3.12a (the text total: per top each slot's calls and a beside table's least lines); 40 -> 42 at shape 1 (3.13: per file read by both readers the types its case's Wc excludes, as size); 42 -> 46 at 3.9a (two quantities: per task, region and quantity the state's atoms over the pairs of kinds); 46 -> 48 at 3.9b (per region each events-file class's count, the kinds of each class); 48 -> 56 at 3.8b (a present recording's subject has its row: a literal's class, else the rows no literal labels); 56 -> 58 at 3.9d (a region's participant rows: at most one or two or more); 58 -> 63 at F02 (each read-limited table's least text and the statement's text total, by rlb's terms); 63 -> 65 at G04 (each read table's least text in the case: its types and its named rows); 65 -> 69 at G05 (each statement's accounted memory: its tables' mlb and its where() calls); 69 -> 78 at G06 (each read trial type no events file holds: its counts, per recording and per recordings() region); G04c +11: the named recordings' and recordings() sets' events files and each statement's text over them (evlb, rs_evlb); 89 -> 90 at H07 (the statement's events files' memory, Model.evmem)"),
    ("decide.py", "find"): (2, FIXED, "(B07) the model's own attributes before and after the search: the fixed set Model.__init__ sets (uncharged, so the pinned step counts stay)"),
    ("decide.py", "piece_facts"): (2, CALLER, "(H08) pieces() and each piece's 2m + 1 parts, charged to pay, as search.piece_atoms"),
    ("decide.py", "pieces"): (4, CALLER, "(e2) the order statistics' regions and their selected types (each type's pieces), as case_atoms"),
    ("search.py", "piece_atoms"): (2, CALLER, "(e2) pieces()'s types and their 2m + 1 pieces, one PAtom each, charged in Model.solve"),
    ("decide.py", "pcuts"): (20, CALLER, "(e2) the means, their types and regions, and per mean at most ((2m + 1)(m + 1) + 1) x 2 x 2 x 2 cases (lowest and highest piece or none, other types with rows or not, the outer upper and lower end), each a system counted in MAX_CASES; their atoms charged in Model.solve"),
    ("search.py", "psign"): (1, FIXED, "(e2) a piece's two ends"),
    ("decide.py", "shape"): (3, PROGRAM, "one where()'s conditions; 2 -> 3 at R1 (a mean of recordings within a difference: the statement's nodes, R006)"),
    ("decide.py", "br"): (27, CALLER, "a value's branches over its arguments' branches, charged in Decide.branches; 19 -> 20 for (e)'s mean in a difference (its mu atoms); 20 -> 26 at item 2 (where() and key() over their K002 scope cases; a no-answer X result passed on like a refusal); 26 -> 27 at item 2c (the named onset rows); 27 -> 28 at R2 (recordings(): its filter's branches); 28 -> 27 at item 3 (the onset rows' list now Model.rrows)"),
    ("search.py", "one_solve"): (1, CALLER, "(f) the memo key of one system's atoms (pixdim models only), as one_solve1"),
    ("search.py", "one_solve2"): (26, CALLER, "one system: its atoms and the statement's row types; charged calls + atoms (item 7: no raw MAX_ROWS atoms; call 2: its coefficients' size, once); the integer atoms' bytes held before they are built (28 Oct 2026)"),
    ("search.py", "empty_box"): (6, CALLER, "(f) at most 32 rounds over one system's atoms, each round charged its atoms' terms; with a log, one bound's line: the atom's other variables"),
    ("search.py", "fpick"): (1, CALLER, "(f) binary places from the gap's to the float spacing at lo: at most 2,100 (the floats' exponents), each charged"),
    ("search.py", "decide"): (3, CALLER, "(memory) MSearch.decide: one integer-step frame's atoms and their coefficients, as the integer step's own normalize (charged in its calls)"),
    ("decide.py", "size_of"): (2, CALLER, "(memory) a case's or branch's containers, each entry once: the size of what it measures, built by its caller"),
    ("decide.py", "kept_bytes"): (2, CALLER, "(C4) what a refusal's check keeps (find's options, shares' forms), each entry once: the size of what it measures, built by its caller"),
    ("decide.py", "certify"): (11, CALLER, "(C4) the question's kept finds and shares, one entry per find() that returned none or share pair, each charged when the decision made it; (L1) each replayed find's trees (options_closed) and their split counts (L6: 11 -> 10, no lemma is counted: one is X001), at most its options' nodes, and the kept models; (L4) a one-option find's atoms kept by key, and the shares with sums; 10 -> 12 at F02 (the kept models' read limit and the kept variance caps, for the reason)"),
    ("decide.py", "take"): (1, FIXED, "(memory) at most MAX_CASES + 1 cases, each held before it is kept"),
    ("decide.py", "frange"): (1, FIXED, "(f) four atoms of one float range"),
    ("decide.py", "fpair"): (1, CALLER, "(f) y's residues mod A/gcd in its interval, each charged; A a pixdim window's denominator"),
    ("decide.py", "fwin"): (7, CALLER, "(f) one system's atoms (as one_solve1), then the smaller exponent (2,046), the order (2) and the gap d (from the least that reaches the window to where B·2^d passes it), each charged, R013 past the step bound"),
    ("decide.py", "frange_of"): (1, CALLER, "(f) one system's extra atoms, charged with the system in one_solve1"),
    ("decide.py", "frange_in"): (5, CALLER, "(D01, review 4 01) a node's atoms (a binade split's parent, at most MAX_CASES nodes an option): each z - sg·2^ea·J atom against each J <= hi atom, then the range's four atoms against the node's, as cert.split's own scan of the same atoms"),
    ("decide.py", "rlays"): (3, FIXED, "(shape 3) the layouts of m <= RAW_LONG bytes: 7 exponent lengths x 2 signs x at most 1,010 point places, cached"),
    ("decide.py", "lnext"): (2, FIXED, "(shape 3) q moved from an estimate within 3 of log10(v / m1): a few turns"),
    ("decide.py", "lprev"): (2, FIXED, "(shape 3) q moved from an estimate within 3 of log10(v / m1): a few turns"),
    ("decide.py", "ext_"): (1, CALLER, "(shape 3) the layouts' candidates, one per layout (rlays' bound)"),
    ("decide.py", "rnext"): (2, FIXED, "(shape 3) one pass over the layouts of n and n - 1 bytes (rlays' bound), cached"),
    ("decide.py", "rprev"): (2, FIXED, "(shape 3) one pass over the layouts of n and n - 1 bytes (rlays' bound), cached"),
    ("build.py", "dec_ct"): (2, CALLER, "(shape 3) the factors 2, 5, 10 of one value's denominator and its trailing zeros: its digits"),
    ("build.py", "rspell"): (1, FIXED, "(shape 3) two signs for 0, else one"),
    ("decide.py", "scell"): (3, PROGRAM, "(shape 2) the column's literals (R006), twice, and a fixed 25-letter alphabet"),
    ("decide.py", "sline"): (3, PROGRAM, "(shape 2) the table's width (at most 26) and each cell's bytes (literals of the statement)"),
    ("decide.py", "dec_len"): (2, FIXED, "(G04) at most 12 candidate exponents, each one mantissa of at most MAX_DIGITS digits"),
    ("decide.py", "dec_spells"): (5, FIXED, "(G04) 2·MAX_EXPONENT + 2 exponents, 2 signs, 3 exponent signs, 7 paddings, e or E: a fixed bound, once per class (cmin's lmemo)"),
    ("decide.py", "lline"): (2, PROGRAM, "(G04) a table's columns, once per row type (lmemo)"),
    ("decide.py", "cmin1"): (9, PROGRAM, "(G04; H02) each candidate charged (Model.pay): ASCII texts by length, stopping at length 2 (at most 96 + 96² texts; past it a lower bound); spelling lengths up to 2·MAX_DIGITS + 16 over in_iv's values; once per class (lmemo)"),
    ("build.py", "vmin"): (4, FIXED, "(G04; SPL) spelling lengths up to 2·MAX_DIGITS + 16, each dec_spells' fixed bound"),
    ("decide.py", "in_iv"): (6, PROGRAM, "(G04; H02) two sides, MAX_EXPONENT + 2·MAX_DIGITS scales (the finer ones near the near end within the same range, LOW up), iv_scale's K values each, each charged (Model.pay)"),
    ("decide.py", "iv_scale"): (1, PROGRAM, "(G04; H02) K (the column's literals + 1) multiples, each charged (Model.pay)"),
    ("decide.py", "wheres"): (1, PROGRAM, "(G05) letwalk's calls, once each"),
    ("decide.py", "mlb"): (3, CALLER, "(G05) a table's row types (as rlb) and its named rows, as case_atoms"),
    ("decide.py", "lchars"): (2, PROGRAM, "(G05) a table's columns, once per row type (lmemo)"),
    ("decide.py", "tt_holds"): (1, PROGRAM, "(G06) one trial type literal of the program, its characters"),
    ("decide.py", "alike_br"): (13, PROGRAM, "(G07) the statement's tasks of one dataset that look alike (G), each one's regions and kinds, G^2 pairs and G + 1 others times the filter's branches; charged as branches (Decide.branches)"),
    ("decide.py", "evlb"): (2, PROGRAM, "(G04c) one recording's read trial types; H07: their roles for evmem"),
    ("decide.py", "rs_evok"): (1, PROGRAM, "(G04c) the statement's recordings() aggregates"),
    ("decide.py", "rs_evlb"): (1, PROGRAM, "(G04c) the set's regions (the program's participant conditions, Model.br)"),
    ("readers.py", "held"): (2, PROGRAM, "(H03) the program's kept structures (prog_seen at the statement's start), once a decided statement; (A03) and once for its tables"),
    ("decide.py", "w2_nopt"): (10, PROGRAM, "(H06) the values before the recordings() call (the statement's arguments) and their branches' products in each case, as w2_input"),
    ("decide.py", "before"): (2, PROGRAM, "(H06) w2_nopt's walk down to the call: one call's arguments, each once"),
    ("decide.py", "evmem"): (3, PROGRAM, "(H07) the statement's events-file reads, each one's variables and constant files and rows"),
    ("decide.py", "rs_evm"): (12, PROGRAM, "(G04c) the set's regions, each one's events-file classes (two at most), the quantities and kinds (rs_jk) of the program; H07: the files' and rows' roles for evmem"),
    ("decide.py", "rlb"): (3, CALLER, "(F02) a table's row types and each one's read columns, as case_atoms (its caller, charged there with the case's atoms)"),
    ("decide.py", "limit_shown"): (1, CALLER, "(F02; G02b) the refusal's kept finds, as certify (each replayed under the same step account rb); was unbounded"),
    ("decide.py", "past_limit"): (8, CALLER, "(G02b) one option's system as base() and tail() built it (charged there), walked a fixed number of times (8 loops) and paid again by its forms' size (pay) before the checks"),
    ("decide.py", "smin"): (12, CALLER, "(3.12, 3.12b) a table's row types, twice for a one-column table's two layouts, and the case's named rows, as case_atoms; 6 -> 12 at 3.13h (a file read by both: its case width's types, and the 'o' case's two widths' lesser per row)"),
    ("decide.py", "lay_cases"): (8, CALLER, "(3.12b) two layouts, each its smin terms and the types with no one-column row, as case_atoms; 6 -> 8 at 3.13h (a file read by both: a numbered width's one least; the 'o' case's types with no line in one column)"),
    ("build.py", "lay_of"): (7, CALLER, "(3.12b) a solution's row types and the case's named rows, as smin (bytes_of1); 3 -> 7 at 3.13h (a file read by both: the 'o' case's types with no line in one column, the solution's rows, as smin)"),
    ("build.py", "stext"): (3, CALLER, "(shape 2) a certificate input, as table: the width's header names and its rows (at most MAX_ROWS, held in bytes_of1); 2 -> 3 at 3.12b (a one-column CSV's quoted empty cells)"),
    ("build.py", "spell1"): (3, FIXED, "(shape 3) the layouts of one length (rlays' bound), one exponent each"),
    ("decide.py", "__getitem__"): (2, WITNESS, "(shape 3) RawFile: a certificate's read past MAX_TEXT_FILE, its number()-read ranges written over the bytes read"),
    ("decide.py", "prange"): (3, FIXED, "(e) a mean's N range: at most two ends times two bounds of mu (McCormick's four products), and the atoms made"),
    ("decide.py", "cends"): (5, CALLER, "(e) the classes of one mean's types (two ends), as mu"),
    ("build.py", "rec_dataset"): (26, CALLER, "(2c) one certificate dataset: the named recordings (one) and their named onset rows (at most the statement's), its files and its events rows up to the largest named row index (the statement's), read and charged by witness.evaluate; 10 -> 14 at item 3 (durations, the events rows and their trial types, at most MAX_ROWS rows, else R013); 14 -> 25 at 3.8b (participants.tsv's rows relabelled, a T1w.nii for each subject no recording has); G04c +1: the one-letter filler's candidates (a generator)"),
    ("decide.py", "scope"): (16, CALLER, "(item 2) per (column, literals): the column's literal classes and its types, then 2^g presence patterns per skeleton group of g look-alike literals (g at most the statement's literals on that column), each case counted in Model.steps"),
    ("decide.py", "caps"): (6, CALLER, "(pm) pairs of means and their count forms, charged in Model.solve (a second |Ps|^2)"),
    ("search.py", "cap_ok"): (10, CALLER, "(pm) the nests' atoms at the tried values, charged len(atoms) * (values + 1)"),
    ("decide.py", "nest"): (2, CALLER, "(e) two means' count forms and the classes of the types one has more, charged in Model.solve (|Ps|^2)"),
    ("decide.py", "mu"): (3, CALLER, "(e) one mean's types' classes (two ends; the types off a point class's end), as Model.br charges the mean's types"),
    ("decide.py", "same_means"): (8, CALLER, "(e) one system's atoms and the means' forms, charged len(atoms) + len(means)"),
    ("search.py", "half_cut"): (1, CALLER, "(item 1, 28 Oct) half_cands' candidates for one solution, each broken one's test charged by implied (len(ints) + 1, then the lp's m(m + 1)); a cut added is a case re-solved, counted in MAX_CASES"),
    ("search.py", "count_ints"): (5, CALLER, "one case's count atoms, the system solve already charged"),
    ("decide.py", "half_cands"): (6, CALLER, "per mean (Ms, counted in MAX_CASES' systems) and per order statistic of its column (the case's ordv) its sum's types and, in the statistic's region, its 2m + 1 pieces (pcuts' bound)"),
    ("search.py", "implied"): (1, CALLER, "one count system's atoms, charged len(ints) + 1 before tidy"),
    ("search.py", "solve1"): (35, CALLER, "the systems of one question's presence and band splits, at most MAX_CASES (item 8, call 2); (f) a pixdim's float range halved (at most 11 halvings of its 2,046 binades per float, a split per non-float point the solver picks); (e) a mean's N range split (sign, then at the solution's n), nested means' and end cases, each a system counted in MAX_CASES, the means' pairs charged |Ps|^2; one_solve charges each; (e2) a piece's mu split by sign once, the pieces' PAtoms and pcuts' atoms charged; a mean's sum's variables when a type's presence breaks (presence split first); (pm) a cap's nests' cases at a solution no shared mean admits (cap_ok charged), each a system counted in MAX_CASES; 31 -> 32 at the two-float window (fwin: whether an atom so far ranges a float); 32 -> 36 when its stack's entries are held (solve1: the entries pushed since the last pop, their atoms not in the popped one's list; SPEC-EXACT 8); (cert.py) one split's children, as the entries pushed; (L1) 37 -> 32: the band, step and presence cases built by the model (band_cases, step_cases, presence); (shape 3) a spell split's children; 33 -> 35 at 3.12b (the layout split: the tables with an empty literal in one column, lay_cases)"),
    ("build.py", "inside_sum"): (1, CALLER, "the columns of one summed type (item 8)"),
    ("search.py", "rows_of"): (2, CALLER, "the slots and one solution's variables"),
    ("search.py", "find_options"): (16, CALLER, "a question's options, each solved and charged in Model.solve; rounds while the step cap (x4 each) is below the steps left, an option's rounds charged once (its largest, (e2)); once, per waiting option three systems (0, 1, 2 rows in all), each charged its variables and its solve (item (g), (e2)); a large solution re-solved at most twice (2, 64 rows per slot), one atom per table slot, each solve charged (#4); 11 -> 15 at item 2c (volumes <= 2, 64, MAX_VOL first: three more solves per option, charged in b); 15 -> 16 at R1 (recordings <= 2, 64, MAX_ROWS first: three more solves per option, charged in b); (cert.py) the options' trees' lemma counts, once; (L1) 18 -> 16: its trees are checked by certify"),
    ("build.py", "bytes_of1"): (10, CALLER, "a certificate input, as table; 7 -> 9 at R2 (each row's type, for the recordings' participants); 9 -> 10 at item 4 (the table's labels for its dataset); as bytes_of before, now bytes_of1 (its rows held while built)"),
    ("decide.py", "row"): (1, CALLER, "one row: the columns the statement reads (PROGRAM) plus one"),
    ("decide.py", "branches"): (3, CALLER, "a question's cases (at most MAX_CASES) and their branches, charged here"),
    ("decide.py", "w1"): (9, CALLER, "one value's branches (charged in branches) and one pair of certificate inputs"),
    ("decide.py", "w2"): (2, PROGRAM, "the calls on the part's path; one input each"),
    ("decide.py", "w2_input"): (21, CALLER, "branch pairs (charged in branches) and the share's variables; each point tried is charged"),
    ("search.py", "finish"): (2, CALLER, "one solution's variables and the replacements presolve made, charged in Model.solve"),
    ("decide.py", "id_cond"): (1, PROGRAM, "the parts of two value identities, nested as the statement"),
    ("decide.py", "ident"): (4, PROGRAM, "an aggregate's arguments; 2 -> 3 at R1 (a recordings() aggregate's arguments); 3 -> 4 at item 3 (a recording value's arguments)"),
    ("search.py", "lp1"): (30, CALLER, "simplex on one system: atoms times variables per pivot, pivots bounded by Bland's rule; charged atoms squared in Model.solve; its tableau's bytes held before it is built and before each pivot (28 Oct 2026)"),
    ("decide.py", "merge"): (12, PROGRAM, "the widened values of two terms of one difference; their branches charged in Decide.branches"),
    ("decide.py", "order_atoms"): (3, CALLER, "one aggregate's selected types and pieces, as selected; the named rows (item 6 (d))"),
    ("search.py", "presolve"): (13, CALLER, "one system's atoms, once per equality replaced (at most its variables); charged in Model.solve; with a log, the same atoms' lines"),
    ("build.py", "split"): (1, CALLER, "decimal places until n - 1 equal rows fit: the digits of the sum the solver chose"),
    ("search.py", "tidy"): (25, CALLER, "one system's atoms, once per round of variables set to 0 (at most its variables); with a log, the same atoms' lines"),
    ("decide.py", "total"): (2, CALLER, "the selected types, as selected; the named rows (item 6 (d))"),
    ("build.py", "type_rows"): (15, CALLER, "a certificate input's rows and columns, as table (P1: and its values checked readable; call 2: a summed column's runs expanded; (e2) a summed and ordered column piece by piece, its runs expanded); 13 -> 15 when its values and texts are held (each column's, after it is built)"),
    ("decide.py", "weak"): (1, PROGRAM, "orders of the order statistics of one column in one region"),
    ("build.py", "file_bytes"): (3, CALLER, "a header's seven dims (item 7: a raw file is a witness.Periodic, read only through size() and bytes() slices); witness.evaluate charges its reading; 1 -> 2 at the slot shapes (3.10: a NIfTI file's dims, for its header); (shape 3) a raw file's number()-read ranges"),
    ("decide.py", "rs_sp"): (1, CALLER, "(3.9e) a task's regions: 2^R splits, each case charged in Model.cases (MAX_CASES)"),
    ("build.py", "merge_chains"): (6, CALLER, "(3.9d) two chains of a certificate's participants (at most its rows): each step takes one"),
    ("decide.py", "firsts"): (6, CALLER, "(3.9d) rs_cases' memo: a task's regions (at most the statement's sets' cells) and R1's orders of them (each order charged in rs_firsts)"),
    ("decide.py", "rs_views"): (3, CALLER, "(3.9c) the statement's aggregates over recordings() sets and their parts' conditions (at most the statement's nodes)"),
    ("decide.py", "rs_seq"): (4, CALLER, "(3.9c) one view's (region, kind) pairs in an order: the task's regions times its refusing kinds (at most 2)"),
    ("decide.py", "rs_firsts"): (11, CALLER, "(3.9c) R1's orders times each view's branches, each charged in Model.steps (one per combination, plus the kept ones it is compared with); the kept cases at most those; 10 -> 11 at 3.9d (pi, the order of the one-row regions)"),
    ("decide.py", "rec_cases"): (5, CALLER, "(2c, 3.8b) the named recordings' cases (moved from file_cases), at most MAX_CASES + 1 taken, each charged in Model.cases"),
    ("decide.py", "file_cases"): (22, CALLER, "the cases of a JSON slot's named paths (kinds, presence, lengths), at most MAX_CASES + 1 taken, each charged in Model.cases; (f) a NIfTI slot's dim[0] times four unit codes; 19 -> 22 at item 2c (a recording's cases: dim[0] x events rows, at most 2 x (named onset rows + 2)); 22 -> 26 at R1 (a recording-set slot: the orders of its refusing kinds, at most 2, times 2^tasks presence cases); 26 -> 22 at R2 (a recording set's cases moved to rs_cases); 22 -> 24 at item 3 (per named recording its cases: dim[0] x events rows x trial_type column, a product over the named recordings, cut at MAX_CASES + 1); 24 -> 26 at the slot shapes (3.10: a NIfTI file read by size() too: dim[0] x three ways of holding the header); (shape 3) a raw slot's classes per number()-read range; 27 -> 22 at 3.8b (the named recordings' cases moved to rec_cases)"),
    ("decide.py", "jbr"): (1, PROGRAM, "the steps of one member()/item() chain"),
    ("decide.py", "jpath"): (1, PROGRAM, "the steps of one member()/item() chain"),
    ("build.py", "jtext"): (8, CALLER, "a certificate JSON text: the named paths and array items up to a named index, as file_bytes; 4 -> 8 at G09 (the object's named members' skeletons and the filler's candidates: 27 + named + 1)"),
    ("decide.py", "w1_var"): (6, CALLER, "a variance's cases and branches (charged in Decide.branches) and its free types; two certificates' rows (5b)"),
    ("decide.py", "ends"): (1, CALLER, "the free types of one variance's case, charged 2 per type here (P1)"),
    ("decide.py", "vchain"): (1, PROGRAM, "the widen() calls written above one variance (item 5a)"),
    ("decide.py", "width"): (1, PROGRAM, "the widen() calls written above one variance (item 5a)"),
    ("decide.py", "var_cands"): (7, CALLER, "a variance's cases and branches (charged in Decide.branches) and its free types (moved from w1_var, item 5a); the ruled-out types (5b)"),
    ("decide.py", "w2_widen"): (5, CALLER, "the pieces from wpieces and the variance's cases, charged here (item 5a)"),
    ("decide.py", "rs_lit"): (1, PROGRAM, "(R1) one trial-type literal's characters"),
    ("build.py", "W_split_int"): (1, CALLER, "(R1) a certificate's recordings of one task, at most MAX_ROWS (else R013)"),
    ("decide.py", "rs_br"): (12, CALLER, "(R1) the refusing kinds of one quantity (at most 2) and the kinds summed by count, charged in Decide.branches; 2 -> 11 at R2 (the filter's branches, the set's regions and the case's order of (region, kind), the answering regions; a min or max's region branches, at most the regions squared); 11 -> 14 at 3.9a (two quantities: the case's order, quantity i's refusing kinds, the answering regions' sums); 14 -> 12 at 3.9c (one branch per view: the case's choice)"),
    ("decide.py", "recd"): (2, PROGRAM, "(R1) one value's nodes, bounded by R006; 1 -> 2 at R2 (the set's regions)"),
    ("decide.py", "rsqs"): (1, PROGRAM, "(3.9a) the quantities read of one recording-set slot: at most two"),
    ("decide.py", "rs_jk"): (3, FIXED, "(3.9a) the pairs of two quantities' kinds: at most 3 x 2 = 6; 1 -> 3 at 3.9b (the image and events-file axes, at most 2 x 3, written per quantity)"),
    ("decide.py", "rs_nq"): (1, FIXED, "(3.9a) the pairs holding one quantity's kind: at most 6"),
    ("decide.py", "rs_cls"): (2, FIXED, "(3.9b) a kind's events-file value: the slot's quantities, at most 4"),
    ("decide.py", "rs_couple"): (2, FIXED, "(3.9b) the slot's quantities (events and the read trial types), at most 4"),
    ("decide.py", "rs_ny"): (1, FIXED, "(3.9b) the events-file classes: at most 2"),
    ("build.py", "rs_recs2"): (20, CALLER, "(3.9a) one region's recordings of a certificate dataset with two quantities: per pair of kinds (at most 6) its recordings (at most MAX_ROWS in the region, else R013), each quantity's values (W_split_int), the order's kinds; volumes and events in all at most MAX_VOL and MAX_ROWS (else R013); read and charged by witness.evaluate, as rs_dataset; 9 -> 20 at 3.9b (per events-file class its recordings, each read type's rows split, the filler rows beyond the trials, a filler type no read type looks like out of 5)"),
    ("search.py", "rs_small"): (9, PROGRAM, "(R1) the statement's recording-set slots, tasks, kinds and aggregates; atoms charged in Model.solve; 5 -> 8 at 3.9a (two quantities: per region the pairs of kinds and each quantity's sum); 8 -> 9 at 3.9b (each quantity's sum per events-file class)"),
    ("build.py", "rs_dataset"): (22, CALLER, "(R1) one certificate dataset: its tasks' recordings (at most MAX_ROWS each, else R013) and their events rows (MAX_ROWS events, MAX_VOL volumes in all, else R013), read and charged by witness.evaluate; 9 -> 17 at R2 (the regions' participants: the rows' types per region, at most MAX_ROWS rows; the participants table's lines relabelled, one T1w image per participant without a recording); 17 -> 18 at item 4 (the table's own labels when participant_id is read); 18 -> 22 at 3.9d (per task a carrier per region, merged into one label order)"),
    ("decide.py", "count"): (2, FIXED, "(R1) a recording set's kinds: at most three; 1 -> 2 at R2 (a recording set's regions)"),
    ("decide.py", "rrows"): (1, PROGRAM, "(item 3) the statement's recording values, bounded by R006"),
    ("decide.py", "rtt"): (1, PROGRAM, "(item 3) the statement's recording values, bounded by R006"),
    ("decide.py", "plabel"): (2, PROGRAM, "(item 4) the statement's column-1 literals (R006), and a fixed 25-letter alphabet"),
    ("decide.py", "rsel"): (1, PROGRAM, "(R2) the where() calls of one filter, bounded by R006"),
    ("decide.py", "rconds"): (1, PROGRAM, "(R2) the where() calls of one filter and their conditions, bounded by R006"),
    ("decide.py", "rs_cases"): (19, CALLER, "(R2) per task the regions' orders (R! x 2^R with two refusing kinds, else one) and 2 or 3 states per region; the cases it yields are cut at MAX_CASES + 1 by Model.cases, which charges each; 8 -> 10 at 3.9a (two quantities: the ordering quantity, the states per quantity, at most 2 x 1); 10 -> 8 at 3.9b (states per events-file class, z/p each); 8 -> 17 at 3.9d (states first, empty regions dropped from the orders; rs8: per pair of states the flags of the regions both tasks use, pairs of kept cases agreeing on pi); 17 -> 19 at 3.9e (per case the splits of rs_sp)"),
    ("decide.py", "var_hit"): (23, CALLER, "the pieces, anchors and free types, charged 1 per try; multisets at most MAX_CASES, charged n each (item 5a); the pieces and the ends, once each (item (h)); 16 -> 21 (5a no input): the free types' values (few charges each) and the pieces against the largest variance of more rows, charged len(K)"),
    ("decide.py", "few"): (1, CALLER, "(5a) at most 65 readable numbers of one class, charged one each"),
    ("search.py", "two_vals"): (3, CALLER, "the pieces, n up to MAX_ROWS, and j's adjustment, charged 1 each (item (h))"),
    ("search.py", "d_scale"): (6, CALLER, "the pieces and the rows' values of one multiset, charged len(rows) + 1 per piece (item (h)); 5 -> 6 at one column scaled alone (cols)"),
    ("decide.py", "differ_on"): (2, CALLER, "two evaluations; witness.evaluate charges their reading (item 5a; var_differ, generalised in 5b)"),
    ("decide.py", "dchain"): (2, PROGRAM, "the widen() calls written above one difference, and its two operands (item 5b)"),
    ("decide.py", "wpieces"): (3, CALLER, "four cutoffs' nine regions, charged here (moved from w2_widen, item 5b)"),
    ("search.py", "d_hit"): (14, CALLER, "the two variances' case pairs (charged here), their pieces' range tests, the types only one reads, the pieces of K (at most nine) and four fixed ends; the finite-domain pairs (item 5b)"),
    ("decide.py", "d_out"): (4, CALLER, "one certificate's tables and rows, and a row's columns (at most two); witness.evaluate charges their reading (item 5b); 3 -> 4 (3.13g): the rows cut to column 1 for a tsv() line read in Wc = 1, as many as were built"),
    ("decide.py", "d_confirm"): (1, CALLER, "two certificates (item 5b)"),
    ("decide.py", "nchain"): (2, PROGRAM, "the variance shape (3.7): the difference and widen() nodes of one statement"),
    ("decide.py", "nwidth"): (3, PROGRAM, "the variance shape's width (3.7, SPEC 5.2): the difference and widen() nodes of one statement and each widen chain's base"),
    ("search.py", "n_hit"): (24, CALLER, "the variance shape (3.7): its terms (statement nodes), their candidates' product (charged here), per column the sups and coefficients, the pieces of K (at most nine), the types and classes' values (at most three per class and column), multisets of at most MAX_CASES, charged n each; 23 -> 27 at one column scaled alone (per column sums C, the scalings tried: 1 + columns)"),
    ("search.py", "dvals"): (1, FIXED, "at most three values of one class (d_domain's, shared with n_hit)"),
    ("search.py", "d_domain"): (17, CALLER, "the variance pairs, their types and classes' values (at most three per class and column), and multisets of at most MAX_CASES, charged n each; each row's values summed once (item 5b); 16 -> 15 when its class values moved to dvals (the variance shape); 15 -> 17 at one column scaled alone (two columns: at most three scalings)"),
    ("search.py", "var_of"): (1, CALLER, "the rows of one multiset, charged in d_domain (item 5b)"),
    ("decide.py", "slot_dvar"): (5, CALLER, "the two variances' case pairs, charged here; two evaluations, whose reading witness.evaluate charges (item 5b); (L6) its kept ranges, one per pair"),
    ("decide.py", "mant"): (1, FIXED, "three candidate powers of 5 (P1)"),
    ("decide.py", "bands"): (2, FIXED, "R's bands, built once: 2 per magnitude from 10^-1000 to 10^1999, plus one (call 2)"),
    ("decide.py", "cbands"): (1, CALLER, "R's bands, once per summed interval class (cached); each paid to the step meter's pay (call 2)"),
    ("decide.py", "part_atoms"): (4, CALLER, "the parts of the summed columns cut so far: at most their bands, charged as atoms in Model.solve (call 2); 2 -> 4 at F01 (the parts checked to partition the bands, two passes over them)"),
    ("build.py", "realize"): (4, CALLER, "one type's rows in one summed column (at most MAX_ROWS) and its parts; split pays its own steps (call 2)"),
    ("search.py", "refine"): (1, CALLER, "one summed column's parts, at most its bands (call 2)"),
    ("search.py", "unrealized"): (2, CALLER, "the summed types and their columns, as inside_sum (call 2)"),
    ("search.py", "thin"): (4, CALLER, "the order statistics' regions, their types and pieces, as case_atoms (call 3)"),
    ("decide.py", "scale"): (1, FIXED, "at most four turns: the start is within three digits of the answer (P1)"),
    ("decide.py", "dec_seq"): (1, CALLER, "one number's text, at most MAX_DIGITS digits (P1)"),
    ("witness.py", "_one_spelling"): (3, PROGRAM, "the statement's nodes, once, when W2 refuses (D4 message)"),
    ("witness.py", "_src"): (2, PROGRAM, "one sub-expression of the statement, for a message"),
    ("witness.py", "_as_judged"): (3, PROGRAM, "the statement's names and nodes, bounded by R006"),
    ("witness.py", "go"): (3, PROGRAM, "a call's arguments (_as_judged, subexprs), bounded by the node bound R006"),
    ("kernel.py", "c_difference"): (4, PROGRAM, "the terms of two affine values, bounded by the statement"),
    ("kernel.py", "trials_of"): (2, CALLER, "key_column_scope charges len(rows) + 1 before the count"),
    ("kernel.py", "c_recording"): (4, CALLER, "bold_labels charges 4 x recordings + 1 first"),
    ("kernel.py", "c_recordings"): (3, CALLER, "bold_labels charges 4 x recordings + 1 first; the join walks the selection already charged"),
    ("kernel.py", "sel_id"): (1, CALLER, "a recording set's recordings; c_recordings charged 4 x recordings + 1 when it built it"),
    ("kernel.py", "inline"): (1, PROGRAM, "a statement's expression"),
    ("kernel.py", "claim"): (2, PROGRAM, "the files the program declares"),
    ("kernel.py", "actual_reads"): (1, PROGRAM, "the reads logged for one statement"),
    ("kernel.py", "count_refusals"): (1, PROGRAM, "the program's statements"),
    # passed before only through a set.add (ASSESSMENT O11), reviewed in the fix pass: each is linear in
    # its bound; parse_manifest was not (R6) and now charges its meter
    ("kernel.py", "number_uses"): (3, PROGRAM, "a formed statement's sort, each node once (a widen chain is walked down once, O9); bounded by R006"),
    ("kernel.py", "_check"): (11, PROGRAM, "the program's statements and question forms; uses their printed sorts hold (R006, R011; SPEC-ORD)"),
    ("readers.py", "__init__"): (8, IO, "start-up: the supplied files, and the manifests among them (each at most MAX_TEXT_FILE, parsed under its own meter)"),
    ("witness.py", "check"): (1, PROGRAM, "the inlined statement's names, bounded by R006 (phase 7: no search loop left)"),
    ("witness.py", "subexprs"): (2, PROGRAM, "the inlined statement's nodes, whose size the sort bound R006 caps (let names shared count in full)"),
    ("__main__.py", "main"): (3, TOOL, "command-line arguments and printed lines"),
    ("machine.py", "_cgroup_max"): (2, TOOL, "lines of /proc/self/cgroup and the depth of its path, at start-up"),
    ("machine.py", "memory_limit"): (3, FIXED, "two rlimits, then cgroup and physical memory"),
}
# witness.py: every uncharged loop there builds or walks candidates (WITNESS); listed by count. "__init__" is
# MemStore's (the candidate blobs). evaluate's 5 (B0304): the program's names, the judged nodes, their let marks
# (unwrapped), and the earlier statements it runs again (their steps charged to the witness budget). Plan's loops went with the search in exact-decision phase 7 (28 Oct 2026).
WITNESS_FNS = {"walk": 2, "slot_of": 1, "ds_of": 1, "rec_ents": 1, "dec_text": 3, "_nii": 1,
               "_fresh": 2, "_canon": 2, "evaluate": 5, "parts": 5, "_path": 1, "_subst": 1, "__init__": 2,
               "answer": 1,
               "__getitem__": 1}   # Periodic (item 7): the bytes of one bytes() slice, at most MAX_BYTES_SLICE
BOUNDED.update({("witness.py", f): (n, WITNESS, "candidates") for f, n in WITNESS_FNS.items()})
BOUNDED.update({("search.py", "__init__"): (1, CALLER, "(SRH) Log: one system's premises, once (moved from decide.py)")})
BOUNDED.update({("build.py", "_cols"): (1, WITNESS, "candidates (moved from witness.py, unit BLD)"), ("build.py", "_dataset"): (22, WITNESS, "candidates (moved from witness.py, unit BLD)"),
                ("decide.py", "check"): (1, PROGRAM, "(C02) the program's statements so far, once (prefix()'s walk, for held())"),
                ("decide.py", "prefix"): (7, PROGRAM, "(B0304) the program's statements so far, its names, and the memo's structures, sizes and charged keys, once each (held()'s walk); 5 -> 7 at D02 (the lets: the program's let names, then its statements, once)"),
                ("decide.py", "plain"): (4, CALLER, "(BLD; B02) a certificate input's blobs, built (and their bytes held) by build.py, each hashed once, and a RawFile's ranges (store_ok's walk, copied)"),
                ("decide.py", "input"): (2, CALLER, "(B02) the statement's names in build.py's store, once each (store_ok's walk)")})


def _meter(e):
    """The step meter: a name or attribute called `steps` (store.steps, self.steps, steps)."""
    return isinstance(e, ast.Name) and e.id == "steps" or isinstance(e, ast.Attribute) and e.attr == "steps"


def charges(fn):
    """A call to the step meter's .add(, or to ._cached( / .measured(, which charge before they build.
    Only the meter counts: before the fix pass any `.add(` did, so a set.add() hid parse_manifest's
    quadratic folder loop (Argon R6, ASSESSMENT O11)."""
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and (n.func.attr == "add" and _meter(n.func.value) or n.func.attr in ("_cached", "measured"))
               for n in ast.walk(fn))


def uncharged():
    out = {}
    for f in SCANNED:
        tree = ast.parse(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read())
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef):
                k = sum(isinstance(n, (ast.For, ast.While, ast.comprehension)) for n in ast.walk(fn))
                if k and not charges(fn):
                    out[(f, fn.name)] = out.get((f, fn.name), 0) + k
    return out


def test_every_loop_is_charged_or_its_bound_is_named():
    got = uncharged()
    unlisted = {k: n for k, n in got.items() if k not in BOUNDED}
    changed = {k: (n, BOUNDED[k][0]) for k, n in got.items() if k in BOUNDED and BOUNDED[k][0] != n}
    stale = sorted(k for k in BOUNDED if k not in got)
    assert not unlisted, f"uncharged loops in functions with no named bound: {unlisted}"
    assert not changed, f"loop counts changed (found, listed): {changed}"
    assert not stale, f"listed functions now charge or have no loop: {stale}"


def test_reasons_are_from_the_list():
    assert {r for _, r, _ in BOUNDED.values()} <= {PROGRAM, CALLER, FIXED, IO, WITNESS, TOOL}


def test_lint_is_not_fooled_by_set_add():   # fix pass R6: only the step meter's .add( is a charge
    tree = ast.parse("def f(rows):\n    seen = set()\n    for r in rows:\n        seen.add(r)\n\n"
                     "def g(store, rows):\n    store.steps.add(len(rows))\n    return [r for r in rows]\n")
    f, g = (n for n in tree.body)
    assert not charges(f) and charges(g)


def test_lint_catches_a_new_uncharged_loop(tmp_path, monkeypatch):
    import test_v4_loops as me
    d = tmp_path / "reality4"
    d.mkdir()
    for f in SCANNED:
        (d / f).write_text(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read()
                           + ("\n\ndef sneaky(rows):\n    return sum(1 for r in rows)\n" if f == "kernel.py" else ""), encoding="utf-8")
    monkeypatch.setattr(me, "SRC", str(tmp_path))
    assert ("kernel.py", "sneaky") in me.uncharged()

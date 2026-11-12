"""Properties of the source itself: the trusted base is small, uses only the Python standard
library, and the second implementation shares no code with it."""
import ast
import os
import sys

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
TRUSTED = ["keys.py", "syntax.py", "sorts.py", "readers.py", "bids101.py", "kernel.py", "__main__.py",
           "witness.py", "exact.py", "machine.py", "intstep.py", "decide.py", "cert.py", "questions.py"]
# v3: 3000 lines without the v4 modules. v4 counts the witness check, the exact roots and the
# memory floor too, since each decides verdicts (DESIGN 6, "the trusted base grows"); the cap is a
# taste call reported to Patsak on 25 Oct, lean 4000.
CAP = 10000   # native questions (SPEC-ORD-EXP): questions.py + kernel/syntax hooks; measured 10000
# 4000 cap was set. 4250 -> 4300 by Patsak (technical call, 26 Oct 2026): the CHANGES checker (taste call 4)
# was added after the 4250 cap, same precedent. 4300 -> 4335 by BB on Patsak's behalf (technical call,
# 26 Oct 2026, reversible): the Windows memory-floor structures written out with their real field names;
# readability of trusted code over line count (DESIGN section 10). 4335 -> 4354 by BB on Patsak's behalf
# (technical call, 26 Oct 2026, reversible): the D4 S008 message naming the one spelling (witness.py),
# measured, not trimmed to fit (DESIGN section 10.2). From here the cap moves only by measured amounts at each
# exact-decision phase checkpoint, each logged. The 4000 target stays, unmet (README states which holds).
# 4354 -> 5340 at the exact-decision phase 3 checkpoint (27 Oct 2026, under the cap rule of 26 Oct 21:29): the measured
# count with intstep.py (182) and decide.py (799), which decide part-T verdicts, and witness.py's 5 lines calling them
# (DESIGN section 10.3). Not compressed to fit. 5340 -> 5729 at the phase 4 checkpoint (27 Oct 2026): part N in
# decide.py (1188 lines), measured (DESIGN section 10.4). 5729 -> 5904 at the phase 5 checkpoint: part H in
# decide.py (1363 lines), measured (DESIGN section 10.5). 5904 -> 6048 at the variance phase checkpoint: part V in
# decide.py (1507 lines), measured (DESIGN section 10.6).
# 6048 -> 6203 by BB (27 Oct 2026): v4-fixes merged in (fix pass 4335 -> 4402 and O pass 4402 -> 4490 on that branch,
# each measured and logged there: fixpass/FIX-REPORT.md, DESIGN sections 11 and 12); 6203 = 6048 + 155, measured.
# 6203 -> 6243 by BB (27 Oct 2026, the same merge): decide.py +40, the exact path decides fix pass R3 (W2 for a file
# slot, Decide.slot_bears), which the merge would otherwise lose; measured (DESIGN section 10.7).
# 6243 -> 6261 by BB (Part B, 27 Oct 2026): item 7, measured +18; DESIGN section 10.8.
# 6261 -> 6330 by BB (Part B, 27 Oct 2026): P1+P2+P4, measured +69; DESIGN section 10.8.
# 6330 -> 6372 by BB (Part B, 27 Oct 2026): item 8, measured +42; DESIGN section 10.8.
# 6372 -> 6383 by BB (Part B, 27 Oct 2026): call 4 (5b sort rule), measured +11; DESIGN section 10.8.
# 6383 -> 6507 by BB (Part B, 27 Oct 2026): call 2 (exact search over R's bands), measured +124; DESIGN section 10.8.
# 6507 -> 6534 by BB (Part B, 27 Oct 2026): call 2b (enumeration rule in intstep), measured +27; DESIGN section 10.8.
# 6534 -> 6574 by BB (Part B, 27 Oct 2026): call 3 (thin pieces of ordered columns), measured +40; DESIGN section 10.8.
# 6574 -> 6700 by BB (Part B, 27 Oct 2026): item 5a (widen variance shapes), measured +126; DESIGN section 10.8.
# 6700 -> 6952 by BB (Part B, 27 Oct 2026): item 5b (c) (difference of two variances), measured +252; DESIGN section 10.8.
# 6952 -> 6983 by BB (Part B, 27 Oct 2026): item 6 (d) (named rows with aggregates), measured +31; DESIGN section 10.8.
# 6983 -> 7010 by BB (Part B, 27 Oct 2026): item (g) (order of the work in find), measured +27; DESIGN section 10.8.
# 7010 -> 7107 by BB (Part B, 27 Oct 2026): item (h) (5a/5b R013 narrowed), measured +97; DESIGN section 10.8.
# 7107 -> 7116 by BB (Part B, 27 Oct 2026): #4 (fewest rows first in find), measured +9; DESIGN section 10.8.
# 7116 -> 7114 by BB (Part B, 27 Oct 2026): (d) leftover (named rows with a variance), measured -2; DESIGN section 10.8.
# 7114 -> 7296 by BB (Part B, 27 Oct 2026): (f) pixdim decided exactly, measured +182; DESIGN section 10.8.
# 7296 -> 7419 by BB (Part B, 27 Oct 2026): (e1) mean inside a difference, measured +123; DESIGN section 10.8.
# 7419 -> 7530 by BB (Part B, 28 Oct 2026): (e2) column both summed and ordered, measured +111; DESIGN section 10.8.
# 7530 -> 7564 by BB (Part B, 28 Oct 2026): (pm) the shared types' mean (caps, cap_ok) and nest's column, measured +34; DESIGN section 10.8.
# 7564 -> 7591 by BB (Part B, 28 Oct 2026): item 2 look-alike literals (Model.scope, K002 as no answer), measured +27; DESIGN section 10.8.
# 7591 -> 7615 by BB (Part B, 28 Oct 2026): item 2b BIDS participants (participants(bids(d)) as a table slot), measured +24; DESIGN section 10.8.
# 7615 -> 7718 by BB (Part B, 28 Oct 2026): item 2c BIDS tr, volumes, onset (SPEC-EXACT 3.8), measured +103; DESIGN section 10.8.
# 7718 -> 7717 by BB (Part B, 28 Oct 2026): base pass (dead NEG table in decide.py), measured -1; DESIGN section 10.8.
# 7717 -> 7927 by BB (Part B, 28 Oct 2026): item R1 recording sets without a filter (SPEC-EXACT 3.9), measured +210; DESIGN section 10.8.
# 7927 -> 8005 by BB (Part B, 28 Oct 2026): item R2 recording sets with a participant filter (SPEC-EXACT 3.9), measured +78; DESIGN section 10.8.
# 8005 -> 8051 by BB (Part B, 28 Oct 2026): item 3 a named recording's values anywhere (SPEC-EXACT 3.8), measured +46; DESIGN section 10.8.
# 8051 -> 8106 by BB (Part B, 28 Oct 2026): 4 (participant_id, participant(), extra()), measured +55; DESIGN section 10.8.
# 8106 -> 8154 by BB (Part B, 28 Oct 2026): slot shapes (csv() with rows(tsv()); nifti() dims with size()), measured +48; DESIGN section 10.8.
# 8154 -> 8284 by BB (Part B, 27 Oct 2026): the variance shape (three or more signed variances of one table, or two with a widen() inside; symbolic widths) and is_square's widened first argument, measured +130; DESIGN section 10.8.
# 8284 -> 8294 by BB (Part B, 27 Oct 2026): tc1: tsv() and csv() of one file read as rows() and number(cell(., r, 1)), measured +10; DESIGN section 10.8.
# 8294 -> 7819 by BB (Part B, 27 Oct 2026): phase 7: the old search deleted (witness.py), measured -475; DESIGN section 10.8.
# 7819 -> 7801 by BB (Part B, 28 Oct 2026): base pass, two structural merges (w1_hit; bold through nii2), measured -18; DESIGN section 10.8.
# 7801 -> 7863 by BB (Part B, 28 Oct 2026, BB's call 09:05): memory held against the stated bound before it is built (decide.hold; fm, the integer atoms, lp), measured +62; DESIGN section 10.8.
# 7863 -> 7921 by BB (Part B, 28 Oct 2026): pixdim window: two floats in one window decided exactly (fwin, fpair; the 10^-45 probe's wrong R013 -> S008 W2), measured +58; DESIGN section 10.8.
# 7921 -> 7928 by BB (Part B, 28 Oct 2026): coupled variances: one column's values scaled alone (d_scale cols; d_domain, n_hit): bfc7's R013 was a stopped search with a 2-row witness, measured +7; DESIGN section 10.8.
# 7928 -> 8018 by BB (Part B, 28 Oct 2026): memory (item 2): a question's cases and branches, solve's stack, the integer step's frames and a certificate's rows held before they are kept (SPEC-EXACT 8), measured +90; DESIGN section 10.8.
# 8018 -> 8101 by BB (Part B, 28 Oct 2026): half cuts (item 1): a mean against an order statistic of its column, mu <= (u + h)/2 when the counts give at most half its rows above u, mirrored (SPEC-EXACT 3.5a): bfe1-60 and three bfh1 claims R013 -> S008 W1, measured +67; lazy (a cut tested only when a solution breaks it: the eager cuts made test_find_cap_is_not_a_refusal R013), 8,101 measured (+83 in all); DESIGN section 10.8.
# 8101 -> 8118 by BB (Part B, 28 Oct 2026; BB's call on Patsak's behalf 17:10, reversible): a round's cap of find() counts its solves only, side work (implied's lp tests) on the step bound only (decide.side, spent_all; SPEC-EXACT 8 item (g)): the lp tests' charge in the first round's cap had made pn450 (formed, 352 s) take >1,300 s, measured +17; DESIGN section 10.8.
# 8118 -> 8142 by BB (Part B item 1, 28 Oct 2026): 5a's no-input sub-case (a wrong R013): a class of at most 64 readable numbers gives all of them (few), and a window above the largest variance of more rows than the multisets tried meets no input, S008 W2 (var_hit, two_cap; SPEC-EXACT 3.7), measured +24; DESIGN section 10.8.
# 8142 -> 8444 by BB (Part B, 28 Oct 2026; BB's call on Patsak's behalf 18:05, reversible): certificates of no point (SPEC-EXACT 6.1): cert.py (159, the checker: proof logs, option trees) joins the base and decide.py +143 (Log, its lines in presolve, fm, tidy, one_solve2, Model.no; the tree in solve1 and find), measured; decide.py leaves only when every refusal kind is certified (partb/CERT/PLAN.md).
# 8444 -> 8520 by BB (Part B, 28 Oct 2026; BB's call 18:05): empty_box's "none" certified (bound lines, cert.py's division rule), a float system's memo answered by its checked system (cert.CHECKED), equal shares recomputed by the checker (cert.shares_zero, SPEC-EXACT 5.4): cert.py +43, decide.py +33, measured.
# 8520 -> 8598 by BB (Part B, 28 Oct 2026; BB's guidance on C4): certificates built and checked only for a refusal, after its decision (the question's "none" finds kept and replayed with certificates, Decide.certify; kept_bytes; Log holds its steps; Unchecked -> R013): decide.py +78, measured.
# 8598 -> 8700 by BB (Part B, 28 Oct 2026; BB's call 18:05): a mean's rows split (prange, SPEC-EXACT 3.5) checked by cert.prange_split (range atoms, McCormick products with mu·N read as S, the cover; S = mu·N and lo, hi trusted), cert.py +97; what a refusal's check keeps counted once per object (kept_bytes: pn472's S008 W2 had dropped to R013), decide.py +5, measured.
# 8700 -> 9018 by BB (Part B, 28 Oct 2026; BB's call 18:05, the certificate work's next unit L1-L5): every split the model's own disjunction (Model.disjunction, cert.cover: nest, cap, presence, refine, band, step, binade, gap, half with its obligation), a piece's sign by its end shown (Model.prove, cert.implied), leaves the model's atoms of their case (Model.base, tail), every refusal's record (Decide.rest; cert.var_verdict), each find replayed on its own model, shares with sums shown (Decide.sums_shown), two floats pinned checked (cert.pin_split): cert.py +142, decide.py +176, measured; the cap follows the measured base until decide.py leaves it (SPEC-EXACT 6.1).
# 9018 -> 9145 by BB (Part B, 28 Oct 2026; BB's call 18:05, unit L6): a variance shape's "no input" checked by its range (Decide.vranges, vnone, cert.vrange_none) or its values (var_hit's vwhy, cert.vdeep_none); a split by a rule the checker does not know, or a refusal resting on an uncertified claim, is X001 (no named lemma left); n_hit past every size is Big, never None: cert.py +50, decide.py +77, measured.
# 9145 -> 8558 by BB (Part B, 28 Oct 2026; BB's call 18:05, unit I3): decide.py's search moved verbatim to search.py (614 lines), outside TRUSTED: its refusals' "none" are replayed and checked by cert.py (Decide.certify), its solutions confirmed on bytes; decide.py 4,377 -> 3,790 measured; the base keeps its definition (wc -l of TRUSTED).
# 8558 -> 8777 by BB (Part B item 4 shape 3, 28 Oct 2026; BB's call on Patsak's behalf 21:52, reversible): number(bytes(f, o, n)) decided (SPEC-EXACT 3.11): the numbers of n bytes by layout (rlays, lnext, lprev, rnext, rprev, rin: the model's, trusted), a raw slot's classes per range, the spell disjunction, the spellings (rspell) and RawFile; rpick in search.py; decide.py 3,790 -> 4,009 measured.
# 8777 -> 8823 by BB (Part B item 4 shape 2, 28 Oct 2026; BB's call on Patsak's behalf 22:57, reversible): size(f) of a file read by tsv() or csv() decided in its first cut (SPEC-EXACT 3.12): each row type's least line (scell, sline), size >= the least table, <= MAX_TEXT_FILE, the certificate the least table padded (stext); decide.py 4,009 -> 4,055 measured.
# 8823 -> 8896 by BB (Part B item 4 shape 2's review, 28 Oct 2026; BB's call on Patsak's behalf 23:30, reversible): the cap of 4 tsv()/csv() calls replaced by the reader's charge (SPEC-EXACT 3.12a: per top, the sum over tables of calls x size <= MAX_TEXT_TOTAL; Model.sl, sk, smin; a table beside the sized one realised at its least) and a one-column table with an empty literal decided by its two layouts (3.12b: lay_cases, the 'layout' disjunction, lay_of, sline/stext/table by width); decide.py 4,055 -> 4,128 measured.
# 8896 -> 8998 by BB (Part B item 4 shape 1, first cut, 29 Oct 2026; BB's call on Patsak's behalf 00:31, reversible): where(tsv(f), eq/ne(1, b)) of a file read by csv() too decided (SPEC-EXACT 3.13): the tsv line as column 0 (wconds, cix, tw_classes), the csv width Wc a model case (Slot.wc, tok, case_atoms), the certificate a bare table of Wc columns (tw_rows); decide.py 4,128 -> 4,230 measured.
# 8998 -> 9013 by BB (Part B item 4 shape 1, review, 29 Oct 2026; BB's call on Patsak's behalf 01:30, reversible): a csv line every read column forces that looks like a tsv() literal is a class of its own of the tsv line (SPEC-EXACT 3.13a; tw_line), its rows refuse K002 through the where()'s look-alike scope; decide.py 4,230 -> 4,245 measured.
# 9013 -> 9025 by BB (Part B item 4 shape 1 case 1, 29 Oct 2026; BB's call on Patsak's behalf 02:10, reversible): number() of a tsv() line beside csv() reads decided (SPEC-EXACT 3.13b): Wc = 1 its own case (the line is csv column 1's cell), else V005 (the line holds a comma); Model.literal states a Wc >= 2 line's literal; decide.py 4,245 -> 4,257 measured.
# 9025 -> 9032 by BB (Part B item 4 shape 1 case 4, 29 Oct 2026; BB's call on Patsak's behalf 02:13, reversible): an aggregate of tsv(f)'s column 1 (or a where() of it) beside csv() reads decided (SPEC-EXACT 3.13c): in Wc = 1 csv column 1's, in Wc >= 2 no selected line is a decimal (tsvof); decide.py 4,257 -> 4,264 measured.
# 9032 -> 9040 by BB (Part B item 4 shape 1 case 3, 29 Oct 2026; BB's call on Patsak's behalf 02:16, reversible): number(header(tsv(f), 1)) beside csv() reads decided (SPEC-EXACT 3.13d): in Wc = 1 csv name 1, else the names joined (V005; its spelling free, name 2 moved by the seed); decide.py 4,264 -> 4,272 measured.
# 9040 -> 9048 by BB (Part B item 4 shape 1, a key() row, 29 Oct 2026; BB's call on Patsak's behalf 02:20, reversible): number(cell(tsv(f), key(1, b), 1)) beside csv() reads decided (SPEC-EXACT 3.13e): the key reads the line (column 0, Model.tkey), its cell as 3.13b; decide.py 4,272 -> 4,280 measured.
# 9048 -> 9046 by BB (Part B item 4 shape 1, widen(), 29 Oct 2026; BB's call on Patsak's behalf 02:24, reversible): widen() beside tsv() and csv() of one file decided (SPEC-EXACT 3.13f): the model's ident() already is the kernel's reader-free identity; the first cut's NotT removed; decide.py 4,280 -> 4,278 measured.
# 9046 -> 9058 by BB (3.7a, 29 Oct 2026; BB's call on Patsak's behalf 04:10, reversible): a found none that rested on 'a variance's part bears through V003/V005 or not at all' beside another refusing value is S013, never S008 W2 (a wrong W2 refusal found by ground truth); decide.py 4,278 -> 4,290 measured.
# 9058 -> 9060 by BB (Part B item 4 shape 1, a variance of the tsv() line, 29 Oct 2026; BB's call on Patsak's behalf 02:53, reversible): a variance of tsv(f)'s column 1 beside csv() reads decided (SPEC-EXACT 3.13g): Wc >= 2 no decimal (as 3.13c), d_out writes a tsv() line's certificate at Wc = 1, the variance shape compares selections without their cases' zero types; decide.py 4,290 -> 4,292 measured.
# 9060 -> 9123 by BB (Part B item 4 shape 1, case 6, 29 Oct 2026; BB's call on Patsak's behalf 03:50, reversible): size(f) beside rows() and where() counts of tsv(f) and csv(f) decided (SPEC-EXACT 3.13h): least lines per width case (tw_least, tw_len), the 'o' case at its least width, its layout split when one column holds no line for a row with an empty csv cell; decide.py 4,292 -> 4,355 measured.
# 9123 -> 9156 by BB (3.7b, 29 Oct 2026; BB's call on Patsak's behalf 05:40, reversible): 3.7a's S013 decided by a finite-domain witness search (search.joint_rows, untrusted) whose rows Decide.differ_on confirms on bytes (X001 otherwise); none found within MAX_CASES is R013, never S008 W2; before it Decide.same_rows (trusted) keeps W2 where each variance and its place read the same rows wherever both answer; decide.py 4,355 -> 4,388 measured.
# 9156 -> 9256 by BB (3.9a, item 4 shape 6, 29 Oct 2026; BB's call on Patsak's behalf 06:15, reversible): two quantities of one dataset's recordings read from different files of a recording (volumes beside events or trials of a type), kinds as pairs, a state per quantity, certificates with both values per recording; decide.py 4,388 -> 4,488 measured.
# 9256 -> 9306 by BB (3.9b, item 4 shape 6 coupled cut, 29 Oct 2026; BB's call on Patsak's behalf 07:08, reversible): two quantities of one events file (events beside trials of a type, two trial types) decided: kinds written per quantity from the image and events-file axes, a z/p state per events-file class, y per (quantity, class), events >= the read types' trials (rs_couple), certificates with filler rows of a type no read type looks like.
# 9306 -> 9312 by BB (3.8a, item 4 shape 5, 29 Oct 2026; BB's call on Patsak's behalf 07:30, reversible): two named recordings, one's labels within the other's, decided: every pair of values stays reachable (the other's own sidecar overrides the inherited one); the certificate puts an inherited sidecar a folder up (rdep).
# 9312 -> 9358 by BB (3.8b, item 4 shape 4, 29 Oct 2026; BB's call on Patsak's behalf 08:41, reversible): participants(b) beside a named recording of one dataset decided: a present recording's subject has its participants.tsv row (B11), a literal's class or else a row no literal labels; the certificate relabels rows and adds a T1w.nii per subject with no recording; decide.py 4,544 -> 4,590 measured.
# 9358 -> 9411 by BB (3.9c, item 4 order model, 29 Oct 2026; BB's call on Patsak's behalf 08:58, reversible): R1's order cases replaced by the least (order, branch per view) by inclusion, one branch per view in rs_br; verdicts R1's; decide.py 4,590 -> 4,643 measured.
# 9411 -> 9463 by BB (3.9d, item 4 shape 8, 29 Oct 2026; BB's call on Patsak's behalf 09:09, reversible): trials of two tasks over participant groups decided: one partition, per region both tasks use one row or two or more, pairs of kept cases agreeing on the one-row regions' order, carriers merged into one label order; empty regions dropped from orders; decide.py 4,643 -> 4,695 measured.
# 9463 -> 9502 by BB (3.9e, item 4 shape 7, 29 Oct 2026; BB's call on Patsak's behalf 09:26, reversible): a sum beside a max or min of one task's recordings decided with N projected out (y >= m; m = 0 & y = 0 | m >= 1 & y >= m; y = m | y >= 2 m); decide.py 4,695 -> 4,734 measured.
# 9502 -> 8955 by BB (unit BLD, 29 Oct 2026; BB's call on Patsak's behalf, reversible; partb/SHRINK/AUDIT.md): the certificate inputs' bytes (Model.bytes_of and what only it calls, witness._dataset/_cols) moved verbatim to build.py, outside the base: every input is checked as a store (decide.store_ok) and read by the real readers and evaluator, and a form needs their answers to differ; decide.py 4,734 -> 4,239, witness.py 433 -> 381 measured.
# 8955 -> 8717 by BB (unit SRH, 29 Oct 2026; BB's call on Patsak's behalf, reversible; partb/SHRINK/AUDIT.md): the search's helpers left in decide.py (Log, Model.no, prove, rs_small, refine, thin, piece_atoms, psign, unrealized, rows_of, fpick, cap_ok, the float steps, form_bytes, spent_all) moved verbatim to search.py: called only by the search, their logs and leaves checked by cert.py, their solutions confirmed on bytes; decide.py 4,239 -> 4,001 measured.
# 8717 -> 8478 by BB (unit HIT, 29 Oct 2026; BB's call on Patsak's behalf, reversible; partb/SHRINK/AUDIT.md): the variance shapes' witness pickers (Decide.d_hit, n_hit, d_domain, d_scale, two_vals, dvals, var_of) moved verbatim to search.py: an input they find is confirmed on bytes (differ_on, d_confirm), and their None refuses only through vnone's range certificate (cert.vrange_none) or var_hit's vdeep/vrange record, else X001; decide.py 4,001 -> 3,762 measured.
# 8478 -> 8493 by BB (unit F01, 29 Oct 2026; BB's call on Patsak's behalf, reversible; Opus 5.5 review 01): cert.Tree keeps each node's atoms as its split gave them and a leaf's atoms must be the option's then exactly the node's (cert.py +12); a summed column's parts (refine, search.py) checked to partition its bands before part_atoms uses them, else X001 (decide.py +3); measured.
# 8588 -> 8591 by BB (unit F04, 29 Oct 2026; BB's call on Patsak's behalf, reversible; mutation sweep partb/MUT): Decide.differ refuses X001 when the search's point gives a ratio no rows (decide.py +3); measured.
# 8511 -> 8588 by BB (unit F02, 29 Oct 2026; BB's call on Patsak's behalf, reversible; Opus 5.5 review 02): the readable inputs are bounded (SPEC-EXACT 1) in every shape: check() decides again with the read limit after a Past (RB, Model.rb, rlb, case atoms), Decide.run's OverRead, two_cap and var_hit by rb, certify's reason (Decide.unbounded) (decide.py +77); measured.
# 8493 -> 8511 by BB (unit F03, 29 Oct 2026; BB's call on Patsak's behalf, reversible; Opus 5.5 review 03): Model.find in decide.py (trusted) keeps every "none" the search (search.py's find_options) gives a question for certify, never the search; certify's check that something was kept removed (decide.py +18); measured.
# 8591 -> 8596 by BB on Patsak's behalf (29 Oct 2026, reversible, unit MUT): cert.py's docstring states why a search.py fault gives only X001 or R013.
# 8596 -> 8622 by BB on Patsak's behalf (unit G02, 29 Oct 2026, reversible; Opus 5.5 max review 02): checked systems, a node's atoms and case and the question's options kept by their contents (cert.fp), not object identity (cert.py +22, decide.py +4); measured.
# 8622 -> 8646 by BB on Patsak's behalf (unit G02b, 30 Oct 2026, reversible; Opus 5.5 max review 02b): the read-limit reason only from a point the model confirms past the limit (Decide.limit_shown, Model.past_limit; decide.py +24); measured.
# 8646 -> 8659 by BB on Patsak's behalf (unit G01, 30 Oct 2026, reversible; Opus 5.5 max review 01): two recordings() aggregates over the same recordings are one identity (decide.id_cond, Model.idsize; decide.py +13); measured.
# 8659 -> 8748 by BB on Patsak's behalf (unit G03, 30 Oct 2026, reversible; Opus 5.5 max review 03): a let read once in its own statement, in the model (decide.stmts, let marks; decide.py +65) and in a certificate's evaluation (witness.evaluate; witness.py +22); measured.
# 8748 -> 8921 by BB on Patsak's behalf (unit G04, 30 Oct 2026, reversible; Opus 5.5 max review 04 a, b): the read limit's atoms count each table's least text exactly (Model.rlb, lline, cmin, dec_len, dec_spells, in_iv, vmin; decide.py +173); measured.
# 8921 -> 8979 by BB on Patsak's behalf (unit G05, 30 Oct 2026, reversible; Opus 5.5 max review 05): the reader's accounted memory (R012, 1 GiB) is part of the read limit: a certificate refused R012 is past it, and with the limit each statement's accounted memory is a case atom (Model.mlb, wheres), so a claim true on every readable input is S008 by the read limit, not X001 (decide.py +58, 8,921 -> 8,979).; measured.
# 8979 -> 8996 by BB on Patsak's behalf (unit G06, 30 Oct 2026, reversible; Opus 5.5 max review 06): a trial type with a double quote or a break character is in no readable events file, so its counts are 0 (tt_holds; decide.py +17, 8,979 -> 8,996).; measured.
# 8996 -> 9012 by BB on Patsak's behalf (unit G07, 30 Oct 2026, reversible; Opus 5.5 max review 07): recordings() of a dataset holding recordings of two look-alike tasks refuses K003, and the model branches on it (Model.alike_br; decide.py +16, 8,996 -> 9,012).; measured.
# 9012 -> 9012 by BB on Patsak's behalf (unit G08, 30 Oct 2026, reversible; Opus 5.5 max review 08): recordings()' participant filter on a dataset without participants.tsv is excluded from W2 by a rule SPEC-EXACT 2 now states (v4 fix 08); the base is unchanged; measured.
# 9012 -> 9012 by BB on Patsak's behalf (unit G09, 30 Oct 2026, reversible; Opus 5.5 max review 09): the certificates' filler JSON member is named apart from the object's named members (build.jtext, untrusted; the base is unchanged).; measured.
# 9012 -> 9131 by BB on Patsak's behalf (unit G04c, 30 Oct 2026, reversible; Opus 5.5 max review 04c): the BIDS events files are within the read limit too: each named recording's events file and each recordings() set's (exact for one quantity read by sums, means or a max; a necessary bound for a min, two quantities or a sum beside a max or min) at most MAX_TEXT_FILE and the statement's text over them at most MAX_TEXT_TOTAL, as case atoms at their least text, which the limit pass's certificates write (Model.evlb, rs_evlb, rs_evm, evreads; decide.py +119, 9,012 -> 9,131).; measured.
# 9131 -> 9118 by BB on Patsak's behalf (unit WLK, 30 Oct 2026, reversible; a move): the let-once walkers stmts, wheres, evreads share one, letwalk (decide.py -13); measured.
# 9118 -> 9105 by BB on Patsak's behalf (unit SPL, 30 Oct 2026, reversible; a move): Model.vmin to build.py, untrusted (decide.py -13); measured.
# 9105 -> 9139 by BB on Patsak's behalf (unit H02, 30 Oct 2026, reversible; Opus 5.5 max2 review 02): the read limit's least text is exact near a short interval end (in_iv's finer scales, iv_scale) and past letters (any ASCII other text, csv quoting counted; OTHC, dec_or_none) (decide.py +34, 9,105 -> 9,139); measured.
# 9139 -> 9183 by BB on Patsak's behalf (unit H07, 30 Oct 2026, reversible; Opus 5.5 max2 review 07): a BIDS table (events, participants) is kept like a plain one, refused R012 before it is parsed when its cells alone pass the bound (kernel.bids_tsv, the conformance gate's tsv_ok; a gate's R012 is not kept for another program), and each statement's memory atom charges its events files (Model.evmem; decide.py +31, kernel.py +9, bids101.py +2, readers.py +2, 9,139 -> 9,183); measured.
# 9183 -> 9191 by BB on Patsak's behalf (unit H03, 30 Oct 2026, reversible; Opus 5.5 max2 review 03): the read limit's memory is the program's, as the reader keeps it: the model's memory atom and the certificates start from what the program holds before the statement, less its own files' (readers.Store.held, decide.HELD, witness.evaluate held; decide.py +1, readers.py +6, witness.py +1, 9,183 -> 9,191); measured.
# 9191 -> 9232 by BB on Patsak's behalf (unit H06, 30 Oct 2026, reversible; Opus 5.5 max2 review 06): G08's rule reversed, the code route taken: recordings()' participant filter bears through V007 on a dataset without participants.tsv (Decide.w2_nopt, partb/G08/alt-code; decide.py +41, 9,191 -> 9,232); overturns v4 fix 08 and Phase F's S008 W2; measured.
# 9232 -> 9240 by BB on Patsak's behalf (unit H04, 30 Oct 2026, reversible; Opus 5.5 max2 review 04): made-up names from an unbounded supply everywhere: decide.fills and FILLC for scell, tw_least, plabel (build.py's rs_recs2 and rec_dataset use them), witness._fresh never stops (decide.py +8, 9,232 -> 9,240); measured.
# 9240 -> 9238 by BB on Patsak's behalf (unit H05, 30 Oct 2026, reversible; Opus 5.5 max2 review 05): the read-limit reason only from limit_shown's point: certify's vdeep disjunct (a record that holds at any size) and var_hit's Past that could never be raised go, with two_cap's rb flag (decide.py -2, 9,240 -> 9,238); measured.
# 9238 -> 9253 by BB on Patsak's behalf (unit H08, 1 Nov 2026, reversible; Opus 5.5 max2 review 08): a piece PAtom's facts are the trusted model's: decide.Model.piece_facts states them by content and cert.prange_split trusts a PAtom outside the option only when it is one of them (decide.py +13, cert.py +2, 9,238 -> 9,253); measured.
# 9253 -> 9256 by BB on Patsak's behalf (unit A07, 1 Nov 2026, reversible; Argon review 07): a W2 pair (Decide.w2, w2_nopt, slot_bears) reads one certificate input: build.py (untrusted) is called once per point, so two stores for one point cannot make an idle part bear (decide.py +3, 9253 -> 9256); measured.
# 9256 -> 9266 by BB on Patsak's behalf (unit A01, 1 Nov 2026, reversible; Argon reviews 01 and 04): Model.disjunction states a split only on a variable of its kind: decide.zkind (the model's kind tags; a region's sum of RepetitionTimes is a sum, a step split, not a band), a spelling split only on a number()-read range of the model holding a number in the case, a binade split only on a float's range of two binades or more (decide.py +10, 9256 -> 9266); measured.
# 9266 -> 9267 by BB on Patsak's behalf (unit A02, 1 Nov 2026, reversible; Argon review 02): Tree.split checks the option's atoms by contents (froot) at every split, as leaf and options_closed do (cert.py +1, 9266 -> 9267); measured.
# 9267 -> 9271 by BB on Patsak's behalf (unit A03, 1 Nov 2026, reversible; Argon review 03): the memory a claim's model starts from (H03) leaves out its lets' tables (the files they read that are tables, readers.Store.held) and the where() row lists its lets keep (store.anon per let, kernel.used_lets): the model charges both again, not a dataset's other structures (kernel.py +2, readers.py +2, decide.py 0; 9267 -> 9271); measured.
# 9271 -> 9272 by BB on Patsak's behalf (unit A06, 1 Nov 2026, reversible; Argon review 06): nwidth keys a widen()'s symbol by its base with the reader unnamed (tsv and csv), as the kernel's identity and vranges do (decide.py +1, 9271 -> 9272); measured.
# 9272 -> 9277 by BB on Patsak's behalf (unit A08, 1 Nov 2026, reversible; Argon review 08 and KNOWN-OPEN's CSV memory item): json()/json_file() meet room() with their known charge before parsing (_cached pre), a TSV/CSV/BIDS table is room-checked at its accounted size so far as each row is built (readers._table), and begin_program drops the memo at each program (9272 -> 9277); measured.
# 9277 -> 9283 by BB on Patsak's behalf (unit A10, 1 Nov 2026, reversible; Argon review 10): make_manifest stops with ManifestError (exit 2, nothing written) on a folder or file it cannot read, never a partial manifest or a traceback (readers.py +6, 9277 -> 9283); measured.
# 9283 -> 9286 by BB on Patsak's behalf (unit B01, 1 Nov 2026, reversible; Argon review 2 01): cert.pin_split accepts only two pixdim variables (('z', 'pix', s), fwin's pair) that occur in the parent's atoms; a pin of naturals or of a byte range's number let search.py alone certify S008/S011 (cert.py +3); measured.
# 9286 -> 9286 by BB on Patsak's behalf (unit B06, 1 Nov 2026, reversible; Argon review 2 06): cert.prange_split's first rows split of the option's own PAtom starts at most at its a0 (a greater a0 left [P.a0, a0) uncovered; with search writing Model.rb, search.py alone certified S008); cert.py +0 (one condition in an existing line); measured.
# 9286 -> 9294 by BB on Patsak's behalf (unit B07, 1 Nov 2026, reversible; Argon review 2 07): cert.py calls the model's methods by its class (cert.mcall), so a piece_facts (or base, tail, disjunction) the search set on the instance is never read, and Model.find compares the model's own attributes before and after the search (decide.SEARCH_SETS excepted): a search.py that forged piece facts or wrote Model.rb certified S008 (cert.py +5, decide.py +3); measured.
# 9294 -> 9306 by BB on Patsak's behalf (unit B05, 1 Nov 2026, reversible; Argon review 2 05): a .nii.gz read whole (nifti_read full: the BIDS gate's image check, and witness.MemStore's) is counted per 4096 decompressed bytes as it is read (R002 there) and charged beside its size on every use (Store._nifti); measured.
# 9306 -> 9328 by BB on Patsak's behalf (unit B02, 1 Nov 2026, reversible; Argon review 2 02): Decide.input copies build.py's store from exact types (decide.plain: exact dict and str names, exact bytes by their sha256, a Periodic class rebuilt from exact arguments and used, datasets by recomputed keys; Store, which Decide.run requires), replacing store_ok, whose isinstance tests and __dict__ comparison a dict, tuple, bytes or str subclass passed (decide.py +22); measured.
# 9328 -> 9329 by BB on Patsak's behalf (unit B09, 2 Nov 2026, reversible; Argon review 2 09): Model.lchars counts an other-text cell as ceil(least bytes / 4) characters (a UTF-8 character has at most 4 bytes; literals and decimals exact), so the memory bound is a lower bound; measured.
# 9329 -> 9329 by BB on Patsak's behalf (unit B08, 2 Nov 2026, reversible; Argon review 2 08): kernel.c_header's Header sort names no reader (meta ("header", reads, k), as Cell's and Model.ident's), so number(header(tsv(f), k)) and number(header(csv(f), k)) are one value: their widen() symbols cancel and two tolerances on it are S012; kernel.py 0 (one line changed); measured.
# 9329 -> 9394 by BB on Patsak's behalf (unit B0304, 2 Nov 2026, reversible; Argon review 2 03 and 04): the memory a statement starts from leaves out every structure made from its files, keyed or not (readers.Store.held, anon_by by the files where() rows come from), and each certificate runs the earlier lets and claims that read them again on its candidate, in program order (decide.prefix, witness.evaluate, MemStore's base for the program's other files); A03's used_lets and store.anon removed; measured.
# 9394 -> 9474 by BB on Patsak's behalf (unit C01, 2 Nov 2026, reversible; review 3 01): cert.exact, the one exact copy of every value the search hands the checker (Tree, check, proved, options_closed, Model.find's point); a node's case for the model is the model's own (Tree.mcase); measured.
# 9474 -> 9479 by BB on Patsak's behalf (unit C02, 2 Nov 2026, reversible; review 3 02): held() leaves out every where() row of the earlier statements a certificate runs again (store.anon_by by statement, kernel.st_ix); measured.
# 9479 -> 9532 by BB on Patsak's behalf (unit D01, 2 Nov 2026, reversible; review 4 01): no search-derived field is trusted: decide.frange_in reads a float's range from the atoms' forms, cert.prange_split reads a parent's range only as its atoms state it (integer ends), cert.exact rejects merged dict keys and drops failed partial copies; measured.
# 9532 -> 9539 by BB on Patsak's behalf (unit D02, 2 Nov 2026, reversible; review 4 02): a certificate's re-run of earlier statements takes the program's value of every let that reads none of the judged files (decide.prefix lets, witness.evaluate), so it charges exactly what held() leaves out; measured.


def imports(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name.split(".")[0], 0
        elif isinstance(node, ast.ImportFrom):
            yield (node.module or "").split(".")[0], node.level


def test_trusted_base_size():
    n = sum(len(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read().splitlines()) for f in TRUSTED)
    assert n <= CAP, n


def test_readme_states_the_trusted_base_size():
    n = sum(len(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read().splitlines()) for f in TRUSTED)
    readme = open(os.path.join(SRC, "..", "README.md"), encoding="utf-8").read()
    assert f"| **total** | **{n}** |" in readme, n


def test_readme_states_the_untrusted_files_sizes():
    """(G10, Opus 5.5 max review 10) README states search.py's and build.py's wc -l; so it cannot drift from them."""
    readme = open(os.path.join(SRC, "..", "README.md"), encoding="utf-8").read()
    for f in ("search.py", "build.py"):
        n = len(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read().splitlines())
        assert f"`{f}` ({n} lines)" in readme, (f, n)


def test_stdlib_only():
    for pkg in ("reality4", "reality4_ref"):
        for f in os.listdir(os.path.join(SRC, pkg)):
            if f.endswith(".py"):
                for mod, level in imports(os.path.join(SRC, pkg, f)):
                    assert level > 0 or mod in sys.stdlib_module_names or mod == pkg, (pkg, f, mod)


def test_reference_is_separate():
    for f in os.listdir(os.path.join(SRC, "reality4_ref")):
        if f.endswith(".py"):
            assert all(m != "reality4" and lvl == 0 for m, lvl in imports(os.path.join(SRC, "reality4_ref", f))), f


def test_each_refusal_code_has_one_home():
    """A code means one rule: no code is raised from two modules (v2 once had N001 for both an
    undeclared name and a short NIfTI file)."""
    import re
    homes = {}
    for f in TRUSTED:
        text = open(os.path.join(SRC, "reality4", f), encoding="utf-8").read()
        for code in set(re.findall(r'(?:fail|Refusal|SyntaxRefusal)\("([A-Z]\d{2,3})"', text)):
            homes.setdefault(code, set()).add(f)
    # v4: W1/W2 (witness.py) is the rule for S008/S011, for every statement (BIDS ones too, since
    # Phase E). The kernel keeps three S008 checks that are facts about bytes, not searches: a
    # literal that is not UTF-8 (no cell or key holds it) and a tolerance of 0 (widens nothing).
    # exact-decision phase 3: decide.py is W1/W2 for part T (SPEC-EXACT), one rule with witness.py; its
    # X001 is the kernel's checker fault (a certificate the real code does not confirm, SPEC-EXACT 6)
    homes = {c: (h - {"decide.py"}) | ({"witness.py"} if c != "X001" else set()) if "decide.py" in h else h for c, h in homes.items()}
    if homes.get("S008") == {"kernel.py", "witness.py"}:
        homes["S008"] = {"witness.py"}
    shared = {c: h for c, h in homes.items() if len(h) > 1}
    assert not shared, shared
    assert len(homes) > 40


def test_the_checker_and_the_base_read_no_untrusted_module():
    """(I3, SPEC-EXACT 6.1) search.py is outside the base because cert.py checks what it gives: so cert.py imports
    nothing from decide.py or search.py (its checks cannot rest on the code they check), search.py is not in TRUSTED,
    and among TRUSTED only decide.py imports search.py (to attach Model's search methods)."""
    assert "search.py" not in TRUSTED
    cert = {m for m, lvl in imports(os.path.join(SRC, "reality4", "cert.py")) if lvl > 0}
    assert cert <= {"", "intstep"}, cert
    tree = ast.parse(open(os.path.join(SRC, "reality4", "cert.py"), encoding="utf-8").read())
    named = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level > 0 for a in n.names}
    assert named <= {"intstep"}, named
    users = set()
    for f in TRUSTED:
        tree = ast.parse(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read())
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.level > 0 and (n.module == "search" or any(a.name == "search" for a in n.names)):
                users.add(f)
    assert users == {"decide.py"}, users


def test_the_untrusted_files_write_no_trusted_state():
    """(B07, Argon review 2 07; SPEC-EXACT 6.1) search.py and build.py run in the checker's process, so the claim that a
    fault there gives only X001 or R013 holds for code that computes and returns: it writes no trusted module's names
    (only decide's MEM and CERTS counters, by entry), no attribute of the model but the search's own (decide.SEARCH_SETS,
    the memo and parts by entry, build's cheld, the budget), calls no setattr, delattr, exec or eval, and never names
    cert's CHECKED or an object's __dict__. Model.find checks the model's attributes at run time; this checks the rest."""
    own = {"tree", "trees", "leaf_at", "checked", "memo", "parts", "budget", "cheld"}
    for f in ("search.py", "build.py"):
        tree = ast.parse(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read())
        mods = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
        cls = {id(m) for c in tree.body if isinstance(c, ast.ClassDef) for m in ast.walk(c)}   # MSearch's and Log's own state
        bad = []
        for n in ast.walk(tree):
            tg = n.targets if isinstance(n, (ast.Assign, ast.Delete)) else [n.target] if isinstance(n, (ast.AugAssign, ast.AnnAssign)) else []
            for x in [y for x in tg for y in (x.elts if isinstance(x, ast.Tuple) else [x])]:
                sub, y = isinstance(x, ast.Subscript), x.value if isinstance(x, ast.Subscript) else x
                if not isinstance(y, ast.Attribute):
                    continue
                r = y
                while isinstance(r, ast.Attribute):
                    r = r.value
                root = r.id if isinstance(r, ast.Name) else None
                if root in mods and not (sub and ast.unparse(y) in ("D.MEM", "D.CERTS")) \
                        or root == "self" and id(x) not in cls and not (isinstance(y.value, ast.Name) and y.attr in own):
                    bad.append(f"{f}:{n.lineno} {ast.unparse(x)}")
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("setattr", "delattr", "exec", "eval", "globals"):
                bad.append(f"{f}:{n.lineno} {n.func.id}()")
            if isinstance(n, ast.Attribute) and n.attr in ("CHECKED", "__dict__"):
                bad.append(f"{f}:{n.lineno} {n.attr}")
        assert not bad, bad


def test_the_untrusted_files_subclass_no_builtin():
    """(B02, Argon review 2 02) A subclass of a built-in value type answers comparisons and reads with its own methods:
    Argon's tamper defined dict and tuple subclasses in build.py. Decide.input copies the store from exact types at run
    time (decide.plain); this makes the boundary visible in review: search.py and build.py define no such subclass."""
    for f in ("search.py", "build.py"):
        tree = ast.parse(open(os.path.join(SRC, "reality4", f), encoding="utf-8").read())
        bad = [f"{f}:{c.lineno} {c.name}" for c in ast.walk(tree) if isinstance(c, ast.ClassDef)
               for b in c.bases if ast.unparse(b).split(".")[-1] in ("dict", "list", "tuple", "set", "frozenset", "bytes", "bytearray", "str", "int", "float", "Fraction", "Periodic", "RawFile", "NiiFile", "Store", "RAtom", "PAtom")]
        assert not bad, bad

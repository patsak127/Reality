# 20. Check 2 is not independent for BIDS claims: sort and trace come from the same variable

**Category:** design issue (the "second, independent check" of the floor is not independent where
it matters most).
**Spec clause:** §1 *Floor* ("A second, independent check sits underneath. The checker recomputes
the claim's dependency set of files and positions"); §2 *Check 2* ("A disagreement between the
checks is a refusal, and also a bug report against one of them"); SPEC §2 item 11 [call].
**Severity:** medium. **Confidence:** high.

## Program

`findings\20-check2-not-independent.rl`, with the made-up dataset `findings\20-ds\` (two runs of
sub-01: run 1's first onset is 1.5, run 2's is 8.75), and the script
`findings\20-check2-not-independent.py`, which runs the same program twice: with the reader as it
is, and with one planted bug in `bids101.read` (run 1's recording is paired with run 2's events
file). `tests\test_findings.py::test_03_check2_refuses_an_unnamed_read` plants a similar bug in a
plain-TSV computation and check 2 refuses it.

```
dataset d = sha256:ccadff3cd3e7cdfd137b8e911c63f4ca125b51cb62939d2f9a218ec31d57e942
claim onset(recording(bids(d), "01", "x", "1"), 1)
```

## Command and output

```
> python -I findings\20-check2-not-independent.py
== unmodified reader
line 2: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 1: #2], #3 row 1] is recorded as 1.5 s (Recorded[s])
  #1 = sha256:ccadff3cd3e7cdfd137b8e911c63f4ca125b51cb62939d2f9a218ec31d57e942
  #2 = sha256:2332e1fb224ea541dcec22cd75345b9c9fb9b0f396c46a10cec5254eb5bbde6e
  #3 = sha256:ffcf3a726c81f082ea532526cccefedfee77767bdc69810616c801efccea5850
accepted

== reader with a planted bug (run 1 paired with run 2's events file)
line 2: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 1: #2], #3 row 1] is recorded as 8.75 s (Recorded[s])
  #1 = sha256:ccadff3cd3e7cdfd137b8e911c63f4ca125b51cb62939d2f9a218ec31d57e942
  #2 = sha256:2332e1fb224ea541dcec22cd75345b9c9fb9b0f396c46a10cec5254eb5bbde6e
  #3 = sha256:069c5df4913273d254a5504e87eb8fbe8041d3bbe2f1735c6d5ee38b4ead148c
accepted
  (manifest: sub-01/func/sub-01_task-x_run-1_events.tsv = sha256:ffcf3a72…)
  (manifest: sub-01/func/sub-01_task-x_run-2_events.tsv = sha256:069c5df4…)
```

With the bug, run 1's onset is reported from run 2's file, and check 2 passes: the sort names the
file that was read, because both come from `Recording.events`.

## Why

For BIDS claims the trace is not recomputed; it is filled in by the same code that builds the
sort: `event` reads `p, h = r.val.events` and prints `@{h}` (`kernel.py:554-560`); `touch_bold`
notes the BOLD file without reading anything so that the trace contains it (`kernel.py:525-526`);
`c_bids` and `c_recording` note the manifest hash directly (`kernel.py:454`, `:522`). Every value
the BIDS reader decides (which events file, which sidecar wins, whether the dataset conforms) is
decided in `bids101.read`, whose reads are "gate" reads that check 2 deliberately ignores
(SPEC §2 item 11). So check 2 can catch a computation that reads a file and forgets to name it,
but not a reader that picks the wrong file, which is the larger risk in a 412-line reader.

## What would fix it

Recompute the dependency set from the standard's rules, separately from the code that reads: for
`onset(r, i)`, derive the events path from the BOLD path by the 1.0.1 template and require the
trace's events file to be the manifest's file at that path; for `tr(r)`, derive the list of
applicable sidecars independently and require the named one to be the winner. A second
implementation of the BIDS reader (SPEC §6 step 5 asks for one per reader) would be the natural
home for this.

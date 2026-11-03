# Checklist: what stays judgement

Builder Bluebell, 24 Oct 2026 (Europe/Berlin). These are the review patterns that a script can't
decide. Each one is a question to answer in writing, with the evidence, before a version goes to
review. `run.py` covers the mechanical part of some of them; the question is what remains.

## The team's guidelines, applied to Reality's own work

1. **Faithful to the reasoning, not the conclusion.** For each "fixed" or "holds" in SPEC or the
   README: what is the argument, and does it still hold after the latest review? (v2: SPEC §5
   marked v1 findings 11, 12, 13 and 15 as fixed; the review found they had moved.)
2. **Explain the other judgement first.** For each review finding we disagree with: write down why
   the reviewer's reading seemed reasonable to them before saying why ours is better.
3. **Hold others to their own standards, and ourselves.** Does the code meet the standard the
   README states for it, word for word? Read every "never", "always", "every" and "exactly" in the
   README and SPEC and name the test or proof behind it. (v2: "a verdict never depends on a path,
   the order of supply…"; "The fuzzers assert X001 never occurs".)
4. **One standard of accuracy.** Wherever v2 is exact in one place (bytes read, ASCII lookalikes,
   CR), is it exact in the neighbouring place (work and memory, non-ASCII lookalikes, U+2028)? If
   not, either make it so or write down why the two places differ. `run.py --only neighbours`
   lists the places it can see; this item is for the places it cannot (JSON keys, BIDS rules,
   bounds on work).

## Independence of the second checks

5. Was the second implementation written from the spec alone, by someone who did not write the
   first? If not, say so where the README lists it.
6. For each value kind, is check 2's trace recorded by code separate from the code that writes the
   sort? (v2 finding 17: for BIDS values it is not.)
7. Does each Lean theorem's statement say something about `kernel.py`, or only about the model?
   Where the model and the code differ (v2: `let` bound once in the model, re-evaluated in Python),
   list the difference.

## Scope and floor

8. Is anything the author writes read as structure (a manifest, a selection, a frame)? If so, which
   parts are checked against the bytes, and which are trusted? (v2 findings 01, 03, 09.)
9. Does every bound count the thing that can grow (work, memory, digits, names), or only the thing
   that was easy to count? (v2 findings 04, 05, 07, 08.)
10. For every claim that forms on fabricated data: could the files named show the defect without
    the world? If yes, it is a missing check, not a false claim. (v2 finding 16.)

## Before asking for a review

11. Run the acceptance test adversarially first: for each function on the path to a verdict, ask
    "what does this trust?" (OVERALL.md, process point 3.)
12. Run `tools/gauntlet/run.py` and read every observation. Each one is either fixed or explained
    in SPEC. None is silently left.

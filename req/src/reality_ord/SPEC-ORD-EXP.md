# Experimental amendment: evidence-bounded weighted pair-orderings (SPEC-ORD-EXP 0.3)

**Status:** native **core** question form in Reality v4 (`questions.py` + `question` statement).
`reality_ord` is a thin Store+`kernel.check` entry, not a parallel dialect evaluator.
**Not** an adopted §10.1 claim-parameter change. Weight family is **question content**.

Frozen principle archive (unchanged): store `principle-nonsense-unformable.md`.

## Structural question / claim separation (0.3)

| Rule | Enforcement |
|---|---|
| Questions are **statements**, never expressions | Grammar: `question` not in EXPR; cannot appear in `let`/`claim`/Call |
| Answers are `QuestionAnswer`, not `Meaning` | Distinct type; not returned from `meaning()` |
| Name after a formed question is reserved | `env[name]=("question", answer, line)` |
| Using that name in let/claim/Call | **Q011** refuse — not a value |
| Print path | `line N: question NAME: formed` + support — never `formed: Sort value` |
| New file of derived numbers | New bytes floor (outside); not prevented; ≠ in-language laundering |

## Grammar

```
file NAME = sha256:HEX64
question weighted_pair_orderings NAME
  table NAME
  candidate_col STRING
  left STRING
  right STRING
  task1_col STRING
  task2_col STRING
  weights RATIO {"," RATIO}
  equality exact
```

Intentional grammar change: only `question` takes indented continuations (`syntax.group_program_lines`).
`file`/`dataset`/`let`/`claim` remain one line.

## Shared enforcement

`Store`, `parse_tsv`, `decimal`, header/key confusable scope; weights ∈ [0,1]; duplicate/unknown/trailing refuse; idle same-task → O010; Recorded precision wording; support positions.

## Trusted-base pin (explicit)

Measured 7 Nov 2026: trusted base **9539 → 10000** (`questions.py` +362, `syntax.py` +67, `kernel.py` +32). Cap and README total updated to match. No Unicode/confusables pin change.

## Non-goals / blocked

Weights as §10.1 claim slots — not done. Promoting answers into claims by writing a new TSV — outside language. Frozen principle file — not edited.

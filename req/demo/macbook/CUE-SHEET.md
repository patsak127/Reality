# MacBook cue sheet (req demo)

One command (Python 3.13 + OpenSSH only; throwaway `REALITY-TEST-KEY-NOT-PATSAK`):

```sh
bash req/demo/macbook/run_macbook_demo.sh
```

The script picks `python3.13` when present, else a `python3` that is ≥ 3.13. Override with `PYTHON=…`. Work dir defaults to `/tmp/reality-macbook-demo` (`REALITY_DEMO_WORK=…`).

This is **not** the live 1.8 GB Qwen judge. Judge labels stay on the machine/build they were adopted for. Data is made up by the demo scripts; say that out loud.

## What to say, step by step

### Setup (5 seconds)

- “Python 3.13 and OpenSSH only. No pip. The script mints a throwaway test key labelled `REALITY-TEST-KEY-NOT-PATSAK` — never my key.”

### Playtest arc (demo.py)

| Moment | Say |
|---|---|
| P1 adopted, then checked | “A signed adoption precedes the check in the ledger you keep. P1 asks for 80% unaided tutorial finish.” |
| DOES NOT HOLD (37/50) | “37 of 50 — DOES NOT HOLD. The arithmetic is on the logs; Reality does not invent the criterion.” |
| In-place bar edit refused | “Lowering the bar in place is refused. A change of mind is a new, later, signed line.” |
| Playtest 2, same P1 | “After a tutorial change: 42 of 50, same adopted P1 — HOLDS. The data changed, not the bar.” |
| Withdraw / adopt P1b | “A lower bar is a new measure: withdraw P1, adopt P1b at 70%, and check the first playtest — HOLDS. The original P1 result still stands, labelled with P1.” |

### AI-eval arc (demo.py)

| Moment | Say |
|---|---|
| E1 adopted, then checked | “Same pattern: adoption, then check. Prompt set pinned by sha256.” |
| E1 DOES NOT HOLD | “196 of 200 refused — 98%, below the 99% bar.” |
| Hash swap refused | “Swapping an easier set’s hash after the result is refused.” |
| Set B → NOT CHECKED | “Wrong set → no verdict, not a silent pass.” |
| Withdraw / adopt E1b | “A lower bar is a new measure (E1b at 98%) and a later, separate adoption. The E1 result still stands, labelled with E1.” |

### Composite CI gate (ai_eval_gate.py)

| Moment | Say |
|---|---|
| `pass` exit 0 | “Composite Gate (95% on A and on B) HOLDS — CI green.” |
| `fail` exit 1 | “Stricter GateFail DOES NOT HOLD — CI red. Same driver, different adopted bars.” |

## Honest limits (say these)

1. **Trusted kernel is large.** v4’s trusted base is **10,000** lines (native questions included; `search.py` / `build.py` outside). req’s trusted package is **861** of a **900** cap. Shrinking it further is a redesign after the event, not another deletion pass.
2. **EvalV2 is narrower than it looks.** A signed, informed check on a Reality-tuned Qwen3-1.7B HOLDS on its adopted bars (124/126 class_ok). The tests are about interface routing, not whether the model forms good questions, and the stock comparison was not a fair baseline. Do not oversell it. It is not in this laptop run.
3. **Judge labels are machine-bound.** A re-run on different hardware can produce different labels; adoption pins the machine and build; the check verifies those exact labels. Reality does not promise any GPU reproduces them. The 1.8 GB stock Qwen path is a separate demo, not this script.
4. **Offline peeking.** Reality cannot prove nobody looked at the data before adopting. It authenticates that a signed adoption precedes the check in the ledger you keep; that file can still be edited or deleted on disk.

## Do not claim

- That Reality keeps an archive outside the ledger file you keep.
- That criteria were fixed before data were examined in any sense stronger than ledger order.
- That this laptop run signed or adopted anything as Patsak.
- “Reality won’t let you rewrite history,” “immutable history,” or “the criterion is fixed before the experiment is run.”

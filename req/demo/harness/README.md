# Harness adapters (Inspect / DeepEval → hash-bound inputs)

**Tested versions (this cut):** adapter code only — no Inspect/DeepEval packages installed in CI.
Fixtures are generic **JSONL** that those tools can emit; the adapter writes Reality TSVs + sha256 sidecars.

## What is tested

- `jsonl_to_eval_tsv.py` converts fixture JSONL → `evals_*.tsv` shape used by E1/Gate.
- Output bytes are hash-stable for the pinned fixtures under `fixtures/`.

## What is not tested

- Live `inspect_ai` / `deepeval` package APIs (versions not pinned here).
- That a third-party harness's judge is correct — judge model + prompt must be hash-bound in a measure's `outside` / data columns when used.

## Run

```sh
python req/demo/harness/jsonl_to_eval_tsv.py \
  --jsonl req/demo/harness/fixtures/sample_inspect.jsonl \
  --prompts-out /tmp/h/prompts_A.tsv \
  --evals-out /tmp/h/evals_A.tsv \
  --set-name A
```

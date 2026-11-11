# Harness adapters (Inspect AI + DeepEval → hash-bound Reality inputs)

## Tested versions (pinned)

| Package | Version | Role |
|---|---|---|
| `inspect_ai` | **0.3.289** | Tiny eval with `mockllm/model`; writes `.eval` log |
| `deepeval` | **4.3.3** | `evaluate()` with `LLMTestCase` + non-LLM `LabelMatchMetric`; writes result JSON |

Pin file: `requirements.txt`. Install only when running real-harness generators/tests:

```sh
python -m pip install -r req/demo/harness/requirements.txt
```

These are the **only** versions this cut claims to have tested. Other versions are untested.

## What is tested

1. **Real library output** under `fixtures/real/`:
   - `inspect_tiny_refusal.eval` — produced by `run_inspect_eval.py` via `inspect_ai.eval`
   - `inspect_tiny_refusal.jsonl` — normalized from that `.eval` via `inspect_ai.log.read_eval_log`
   - `deepeval_tiny_refusal.json` — produced by `run_deepeval_eval.py` via `deepeval.evaluate`
   - `deepeval_tiny_refusal.jsonl` — normalized from that result JSON
2. Adapters `jsonl_to_eval_tsv.py`, `inspect_eval_to_jsonl.py`, `deepeval_result_to_jsonl.py`
3. Reality trials on the converted TSVs: **HOLDS** (loose 50% bar) and **DOES NOT HOLD** (strict 99% bar)

## What is not tested / not claimed

- Live OpenAI/Anthropic APIs (Inspect uses `mockllm`; DeepEval metric does not call an LLM)
- That harness labels are “correct” — Reality checks arithmetic on the adapted bytes
- Versions other than the pins above
- Immutable history or offline-peek proof

## Regenerate fixtures

```sh
python req/demo/harness/run_inspect_eval.py --out-dir req/demo/harness/fixtures/real
python req/demo/harness/run_deepeval_eval.py --out-dir req/demo/harness/fixtures/real
python req/demo/harness/run_reality_checks.py \
  --jsonl req/demo/harness/fixtures/real/inspect_tiny_refusal.jsonl \
  --work /tmp/harness-inspect --label inspect
```

Wording: adoption precedes check in the ledger you keep when you adopt; these drivers use unsigned **try** for exploratory HOLDS/DNH transcripts.

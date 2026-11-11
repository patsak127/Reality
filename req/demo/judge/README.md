# Local LLM judge (hash-bound weights + prompt + decoding)

## Tested stack

| Piece | Pin / value |
|---|---|
| `transformers` | **4.57.1** |
| Model | `sshleifer/tiny-gpt2` (weights hashed at run time into `judge_bind.tsv`) |
| Method | `logprob_argmax` over candidates `refused`,`complied` (leading-space GPT-2 tokens) |
| `do_sample` | `0` (no sampling) |
| `seed` | `20261112` (recorded; unused when not sampling) |
| `torch` | recorded at generation (`torch.__version__` in bind table) |

Install: `python -m pip install -r req/demo/judge/requirements.txt`

## What is proved

- A re-check that supplies the **same** `judge_bind.tsv` / `judge_labels.tsv` bytes (sha256 on the try/check line) and the adopted BindPin fragment sees matching `weights_sha256` / `prompt_sha256` / method / seed / do_sample cells → BindPin **HOLDS**.
- Asking for the adopted bind **sha256** when that file is absent → **NOT CHECKED**.
- Tampered bind **values** under a different file sha → BindPin **DOES NOT HOLD** (eq filters miss).
- LabelsLoose (**≥ 0.50** harmful refused) / LabelsStrict (**≥ 0.99**) give **HOLDS** / **DOES NOT HOLD** on the committed labels from the real model call.

## What is not proved / determinism limits

- **Same machine, CPU float32, same weights bytes, same prompt bytes, logprob_argmax:** labels reproduce (no sampling).
- **Across hardware / GPU kernels / torch builds:** float reductions can differ; we do **not** claim bit-identical logits on every accelerator. Re-check authenticity is the **bind + labels file hashes** in the ledger you keep, not a promise that every GPU redraws the same floats.
- The tiny model is a demo stand-in, not a production safety classifier.
- Reality does not call the model during `check`; it checks the tables the producer wrote.

## Run

```sh
python req/demo/judge/run_llm_judge.py --out-dir req/demo/judge/fixtures
python req/demo/judge/run_judge_reality_checks.py \
  --fixtures req/demo/judge/fixtures --work /tmp/judge-check
```

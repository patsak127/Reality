# Local LLM judge (Qwen3-1.7B-Q8_0 GGUF via llama.cpp)

## Primary judge (RL-16)

| Piece | Value |
|---|---|
| Weights | **`Qwen/Qwen3-1.7B-GGUF` → `Qwen3-1.7B-Q8_0.gguf`** (public HF) |
| sha256 | `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a` |
| Runtime | llama.cpp (`llama-cli` / `llama-server`) |
| Adopted agent bind | `llamacpp_version=0.9.0-dev+cb44fdb`, `backend=server` (GNU 13.3.0 Linux x86_64) |
| Decoding | greedy: `temp=0`, `top_k=1`, `seed=20261112`, grammar `refused\|complied` |
| Thinking | `--reasoning off`; completion with `--no-jinja` (raw prompt) |
| Prompt | few-shot `Verdict:` template in `run_qwen_judge.py` (prompt sha256 in bind table) |

Fetch:

```sh
# verify after download
curl -L -o Qwen3-1.7B-Q8_0.gguf \
  https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q8_0.gguf
sha256sum Qwen3-1.7B-Q8_0.gguf
# expect 061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a
```

Run:

```sh
python req/demo/judge/run_qwen_judge.py \
  --gguf /path/to/Qwen3-1.7B-Q8_0.gguf \
  --llama-cli /path/to/llama-cli \
  --llama-server /path/to/llama-server \
  --out-dir req/demo/judge/fixtures/qwen3

python req/demo/judge/run_judge_reality_checks.py \
  --fixtures req/demo/judge/fixtures/qwen3 --work /tmp/judge-qwen
```

Committed fixtures under `fixtures/qwen3/` include `judge_labels.tsv`, bind table (weights, prompt, llamacpp_version, backend), and meta (accuracy + Cohen's kappa vs `hand_labels.jsonl`).

## Stub (tiny-gpt2) — unit tests only

`run_llm_judge.py` + `fixtures/stub/` use `sshleifer/tiny-gpt2` via transformers logprob_argmax.
**Not** the production judge path. Kept for fast CI without a 1.8 GB GGUF.

## What is proved

- Bind table pins **weights sha256**, **prompt sha256**, decoding params, **llamacpp_version**, and **backend**.
- Missing bind file for the named sha → **NOT CHECKED** (F001).
- Tampered bind values → **DOES NOT HOLD**.
- LabelsLoose (≥ 0.50 harmful refused) / LabelsStrict (≥ 0.99) → **HOLDS** / **DOES NOT HOLD** on committed Qwen labels.
- Agreement vs hand labels is reported in `judge_meta.json` (judge must be informative, not only pinned).

## Hardware and build (honest)

A re-run on different hardware can produce different labels, so adoption pins the machine and build, and the check verifies those exact labels; Reality does not promise that any GPU reproduces them.

- **Same GGUF bytes + same llama.cpp build + same backend + greedy grammar + same prompt:** labels reproduce on that path.
- **CPU vs Vulkan / other GPU backends / other llama.cpp commits:** do **not** assume bit-identical logits. One PC Vulkan re-run used bind `0.9.0-dev+a01dff908` and produced a different labels sha256 than the agent CPU reference (`0.9.0-dev+cb44fdb`) while matching the same headline accuracy/κ vs hand labels. Authenticity is the bind + labels hashes a signed adoption precedes the check of in the ledger you keep.

## PC re-run pack

See `pc-rerun/` (PowerShell 5.1 script + `judge_labels.tsv` reference + `script.diff`). Live 1.8 GB GGUF inference is not the MacBook demo.

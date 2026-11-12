# PC re-run: Qwen3-1.7B-Q8_0 judge (Vulkan / CPU llama.cpp)

Windows PowerShell 5.1 kit matching the agent CPU reference under `../fixtures/qwen3/`.

## What this does

1. Calls local `llama-cli.exe` or `llama-server.exe` with the **same** public GGUF, greedy settings, grammar, and prompt as the agent CPU run.
2. Writes `pc-judge_labels.tsv`, `pc-judge_bind.tsv`, and `pc-labels.sha256`.
3. Prints whether that labels hash matches `reference-labels.sha256`.

`judge_labels.tsv` here is the agent CPU reference labels file (same bytes as `../fixtures/qwen3/judge_labels.tsv`) for item-level comparison after a PC run.

## Prerequisites

- `Qwen3-1.7B-Q8_0.gguf` from `Qwen/Qwen3-1.7B-GGUF`
  (sha256 `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`)
- A Vulkan or CPU build of llama.cpp (`llama-cli` / `llama-server`)
- Windows PowerShell 5.1 or later

## Run

```powershell
cd <this folder>
.\Run-QwenJudge.ps1 `
  -GgufPath "D:\models\Qwen3-1.7B-Q8_0.gguf" `
  -LlamaCliPath "C:\path\to\llama-cli.exe" `
  -LlamaServerPath "C:\path\to\llama-server.exe" `
  -Backend server `
  -OutDir ".\out-pc"
```

`script.diff` records the PowerShell 5.1 fixes applied on the PC (stderr `--version`, UTF-8 bodies, grammar as a plain string, `--no-jinja`, no BOM writes).

## Hardware and build (honest)

A re-run on different hardware can produce different labels, so adoption pins the machine and build, and the check verifies those exact labels; Reality does not promise that any GPU reproduces them.

Observed on one PC Vulkan re-run (bind `0.9.0-dev+a01dff908`) versus the agent CPU reference (bind `0.9.0-dev+cb44fdb`):

| Source | labels sha256 |
|---|---|
| Agent CPU reference | `2e5509490c7bc82090ac81bedf95522f0f5fd0ee2dcae96846fa023f09ee6e10` |
| PC Vulkan | `631d22b3ffb1ed9229a7133a2ae579d538141a221d1778dbdaf87a2e6b45fd49` |

Headline agreement vs `hand_labels.jsonl` was the same on both: accuracy **0.90625** (29/32), Cohen's κ **0.8125**. File hashes still differed. Authenticity for Reality is the bind + labels hashes a signed adoption precedes the check of in the ledger you keep — not a promise of bit-identical logits across backends.

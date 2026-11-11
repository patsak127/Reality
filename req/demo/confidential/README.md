# Confidential hash-only prompt sets (first cut)

## What this proves

- A measure can **pin a prompt set by `sha256:`** inside the fragment (as E1 already does).
- A check supplies the **bytes** of that set (or of an eval table that embeds the set hash) via `--files`.
- If the wrong bytes are supplied, F001/G023 / row filters yield **NOT CHECKED** or fail the row-count claims — not a silent HOLDS.
- Optional **Merkle root** (see `merkle.py`) can commit a tree of prompt-id digests; the measure can require `merkle_root` cell equality. That proves the binder knew a tree with that root, not that CI logs never saw plaintext.

## What this does **not** prove

- Reality does **not** keep an external immutable archive.
- Reality does **not** prove nobody peeked at prompts offline before adoption.
- Hash-only CI does **not** by itself prevent an operator from having plaintext elsewhere.
- Signing still requires the owner's SSH act; this demo never signs for Patsak.

## Run

```sh
export PYTHONPATH=req/src:v4/src
python req/demo/confidential/make_confidential_bundle.py --work /tmp/conf
python -m reality_req check /tmp/conf/ledger/confidential.rq --files /tmp/conf/data
# try HOLDS path uses evals whose prompt_set column matches prompts_A.tsv hash
```

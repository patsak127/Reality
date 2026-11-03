# 01 — Unstructured `@<64-hex>` regex substitution in `m.sort` collides distinct claims into identical printed sorts and falsely triggers `C001`

- **Category:** **hit** (also causes a spurious `C001` bug and a `reality2` vs `reality2_ref` disagreement)
- **Spec clauses:** Principle §1 item 2 (no two readings), §1 item 6 (no self-contradictions), §1 Floor (`trace == named`), §5 (self-contradiction & two claims sharing one canonical form), §10.1 (canonical printed form)
- **Code locations:** `src/reality2/kernel.py:22` (`HASH_RE`), `src/reality2/kernel.py:285` (`c_where`), `src/reality2/kernel.py:580–588` (`claim`, Check 2), `src/reality2/kernel.py:709–713` (`statement`, `#k` substitution)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

`kernel.py` represents every meaning's canonical sort (`M.sort`) as a flat Python `str` rather than an algebraic syntax tree (`Srt` in `metatheory/Scope.lean`). File hashes are embedded inside `m.sort` as `@<64 lowercase hex>` markers, while user-written byte literals in `where(..., eq/ne(...))`, `key(...)`, and `extra(...)` are interpolated directly into `m.sort` via `esc(lit)` (`kernel.py:285, 330, 495`).

Two places then scan the **entire** `m.sort` string with `HASH_RE = re.compile(r"@([0-9a-f]{64})")`:

1. **Check 2 (`kernel.py:580–588`):** `HASH_RE.findall(m.sort)` extracts `named` from inside quoted byte literals too:
   - If the byte literal in `eq(1, "@<H>")` happens to name a hash `H` that the claim *already* read (`H in trace`, such as `f`'s own SHA-256), `named` stays `[H]`, so Check 2 (`extra == [] and idle == []`) **passes**.
   - If the byte literal contains `@<64-hex>` for any hash *not* in `trace` (for example `@0000...0000`), `idle` is non-empty and `reality2` falsely refuses a well-formed plain-TSV filter with `[C001, floor]: ... (a refusal, and a bug report against one of them)` — whereas `reality2_ref.ref.evaluate` returns `('formed', ('count', 0))`.
2. **Canonical output rendering (`kernel.py:709–713`):** `HASH_RE.sub(lambda m: f"#{order[m.group(1)]}", line)` rewrites `@<H>` to `#1` **everywhere in the output line, including inside the quoted byte literal**!

As a result, `eq(1, "#1")` and `eq(1, "@<sha256(f)>")` evaluate **different** predicates on the bytes of `f`, yet print **byte-for-byte identical canonical claim subjects** with `#1` bound to the same hash, producing two formed claims in the same output that assert `X = 1 (Exact)` and `X = 0 (Exact)`.

## Minimal reproducing files and commands

Saved in `findings\`:
- `findings\01-sort-string-hash-collision.rl`
- `findings\01-c001-bug.rl`
- `findings\01-data.tsv` (`id\n#1\n`, SHA-256 `b7703834d1cf3facb063890dbd8826bfe438d90d528078611537012da6ade73d`)

`findings\01-sort-string-hash-collision.rl`:
```text
file f = sha256:b7703834d1cf3facb063890dbd8826bfe438d90d528078611537012da6ade73d
claim count(where(tsv(f), eq(1, "#1"))) is 1
claim count(where(tsv(f), eq(1, "@b7703834d1cf3facb063890dbd8826bfe438d90d528078611537012da6ade73d"))) is 0
```

### Command 1 (hit — contradictory formed claims with identical printed sort)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\01-sort-string-hash-collision.rl --files findings\01-data.tsv
```

### Actual output 1 (`rc = 0`)
```text
line 2: formed: Count[Rows[TSV[#1] where col 1 = "#1"]] = 1 (Exact)
  #1 = sha256:b7703834d1cf3facb063890dbd8826bfe438d90d528078611537012da6ade73d
line 3: formed: Count[Rows[TSV[#1] where col 1 = "#1"]] = 0 (Exact)
  #1 = sha256:b7703834d1cf3facb063890dbd8826bfe438d90d528078611537012da6ade73d
accepted
```

### Command 2 (companion `C001` bug on any other `@<64-hex>` byte literal)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\01-c001-bug.rl --files findings\01-data.tsv
```

### Actual output 2 (`rc = 1`)
```text
line 2: refused [C001, floor]: check 2: the claim's sort names sha256:0000000000000000000000000000000000000000000000000000000000000000, but its value was not computed from it; the sort and the dependency set disagree (a refusal, and a bug report against one of them)
refused (1 statement)
```

## Spec §5 demonstration

- **Formed text:** `findings\01-sort-string-hash-collision.rl` + `findings\01-data.tsv` (`accepted`, two formed claims).
- **§5 demonstration:**
  1. **Self-contradiction (§1 item 6):** In the checker's canonical output (where user names are erased and the printed sort + `#k` table **is** the claim's meaning, `README.md:47`, Principle §10.1), line 2 and line 3 assert of the **exact same subject** `Count[Rows[TSV[#1] where col 1 = "#1"]]` (with `#1 = sha256:b7703834...`) that it equals `1 (Exact)` and equals `0 (Exact)`.
  2. **Two readings (§1 item 2):** The canonical printed sort `Count[Rows[TSV[#1] where col 1 = "#1"]]` has two distinct readings depending on whether `"#1"` in `col 1 = "#1"` came from literal `"#1"` or from rewritten `"@<sha256(f)>"`.
- **Why neither defence applies:** The checker accepts the text (`rc = 0`), and the contradiction is visible purely from the program, bytes, and printed canonical output without consulting the world.

## Fix direction

Represent `M.sort` as a structured `Sort` tree (matching `Srt` in `metatheory/Scope.lean`) with dedicated `FileRef(hash)` nodes distinct from `ByteLit(bytes)` nodes; compute `named` by traversing `FileRef` nodes only and format `#k` placeholders only at `FileRef` nodes when rendering.

# 02 — `Store.locate` ignores `--root` without a path hint and caches verified hashes globally, making plain `file` verdicts depend on `--files` vs `--root` and on idle `let` statements

- **Category:** **hit**
- **Spec clauses:** Principle §1 item 4 (no dependence on outside factors: how bytes are supplied on disk), §1 item 1 (no idle parts bearing on verdicts), §5 (two runs differing in one outside factor)
- **Code locations:** `src/reality2/readers.py:56–62` (`Store` docstring), `src/reality2/readers.py:85–116` (`Store.locate`), `src/reality2/__main__.py:35–49`, `REVIEW.md:43`
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

`Store`'s docstring (`readers.py:56–62`) states:
> *"Files are supplied as explicit paths and/or root directories; paths are only hints for finding bytes, never trusted for content."*

However, `Store.__init__` (`readers.py:64–83`) indexes only `--files` entries into `self._by_hash` and stores `--root` directories as unindexed paths in `self.roots`. Then `Store.locate(self, h: str, hint: str | None = None)` (`readers.py:85–116`) only searches `self.roots` when `hint is not None`:

```python
if hint is not None:
    rel = PurePosixPath(hint)
    ...
    for root in self.roots:
        cand = os.path.join(root, *rel.parts)
        ...
```

When a file is found via `hint` (which happens inside `bids101.load`), `Store.locate` mutates `self._verified[h] = p` (`readers.py:113`), permanently caching that hash for the remainder of the `Store`'s lifetime.

This produces three defects:
1. **Outside-factor dependence (`--files DIR` vs `--root DIR`, §1 item 4):** Plain `file` claims pass `hint=None`. If dataset files are supplied via `--files DIR`, `Store.__init__` hashes the directory tree and the claim **forms**. If the exact same bytes on disk are supplied via `--root DIR` (plus `--files manifest`), `Store.locate(h, None)` skips `self.roots` and refuses with `F001`. (Even `REVIEW.md:43`'s own example `python -m reality2 check program.rl --root path\to\dataset` cannot locate the manifest itself because `store.manifest(mh)` calls `locate(mh, hint=None)`.)
2. **Idle statement side effect (§1 item 1):** Within a single `--root` run, a plain `file` claim on line 3 refuses with `F001`; an **unused** `let unused = bids(d)` on line 4 triggers `bids101.load`, which calls `Store.locate(h, hint="participants.tsv")` and populates `self._verified[h]`; then the **character-for-character identical** plain `file` claim on line 5 **forms**!
3. **Evaluation-order sensitivity:** Reordering independent statements (`let b = bids(d)` before vs after `claim rows(tsv(p)) is 1`) flips `claim rows(tsv(p)) is 1` between `refused [F001]` and `formed`.

## Minimal reproducing files and commands

Saved in `findings\`:
- `findings\02-store-cache-outside-factor-and-idle-let.rl`
- `findings\02-manifest.txt`
- `findings\02-root\` (`dataset_description.json`, `participants.tsv`, `sub-01/func/sub-01_task-x_bold.json`, `sub-01/func/sub-01_task-x_bold.nii`)

`findings\02-store-cache-outside-factor-and-idle-let.rl`:
```text
dataset d = sha256:7546950c74263f7dfea527df68a146fb6abdf2c3e99e577742f2c3f217f78687
file p = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
claim rows(tsv(p)) is 1
let unused = bids(d)
claim rows(tsv(p)) is 1
```

### Command A (supplying `02-root` via `--files`)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\02-store-cache-outside-factor-and-idle-let.rl --files findings\02-manifest.txt findings\02-root
```

### Actual output A (`rc = 0`)
```text
line 3: formed: RowCount[TSV[#1]] = 1 (Exact)
  #1 = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
line 5: formed: RowCount[TSV[#1]] = 1 (Exact)
  #1 = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
accepted
```

### Command B (supplying the exact same `02-root` directory via `--root`)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\02-store-cache-outside-factor-and-idle-let.rl --files findings\02-manifest.txt --root findings\02-root
```

### Actual output B (`rc = 1`)
```text
line 3: refused [F001, text]: no supplied file has sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff; the text names it, so its bytes are part of the text
line 5: formed: RowCount[TSV[#1]] = 1 (Exact)
  #1 = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
refused (1 statement)
```

## Spec §5 demonstration

- **Formed text:** `findings\02-store-cache-outside-factor-and-idle-let.rl` + `02-manifest.txt` + `02-root\` forms completely in Run A (`accepted`) and forms line 5 in Run B only because of the unused `let unused = bids(d)` on line 4.
- **§5 demonstration:**
  1. **Two runs differing in one outside factor (§1 item 4):** Run A and Run B pass the **exact same `.rl` program and the exact same bytes on disk**, differing only in the CLI flag (`--files findings\02-root` vs `--root findings\02-root`). Line 3 flips from `formed` (`accepted`, `rc = 0`) to `refused [F001]` (`rc = 1`).
  2. **Idle part changing verdicts (§1 item 1):** In Run B, line 3 and line 5 are identical (`claim rows(tsv(p)) is 1`), separated only by `let unused = bids(d)` — a binding never referenced by any claim — which changes the verdict of `claim rows(tsv(p)) is 1` from `refused [F001]` to `formed`.
- **Why neither defence applies:** Line 5 forms in Run B and both lines form in Run A; nothing about the world changed.

## Fix direction

Either (a) lazily index `self.roots` on a cache miss when `hint is None` so `Store.locate(h)` is a pure function of the supplied byte set regardless of `--files` vs `--root` or prior `hint` calls, or (b) keep `--root` strictly scoped to manifest-relative resolution without leaking `hint`-resolved paths into global `hint=None` lookups (while also indexing manifests or documenting `--files manifest` in CLI help). Option (a) matches `Store`'s docstring and Principle §1 item 4.

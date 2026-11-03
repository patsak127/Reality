# 13. A deeply nested `dataset_description.json` reaches X001 (RecursionError)

- **Category:** bug (internal error reachable; wrong code)
- **Spec clauses:** SPEC §2 item 13 ("The fuzzers assert X001 never occurs"); README "JSON is read strictly (J00x)"
- **Severity:** low. **Confidence:** high.

## What happens

`readers.parse_json` catches `RecursionError` around `json.loads`, but then validates strings with a
recursive `walk()` *outside* the `try` (`readers.py:224-237`). An array nested between about 1 000 and
some higher depth parses in CPython's C scanner, and then overflows the Python-level recursion in
`walk()`. `bids101.read` calls `parse_json` on `dataset_description.json` without catching that, so the
kernel reports X001. Depths around 200 000 are refused correctly as J001 by `json.loads` itself. On
Python 3.14 that upper threshold depends on the C stack, so the code reported (X001 or J001) can depend
on the machine. I measured only this PC: depth 990 parses, depths 1 000 and 5 000 give RecursionError,
depth 200 000 gives J001.

## Reproduce

`13-deep-json/dataset_description.json` is
`{"Name": "x", "BIDSVersion": "1.0.1", "Notes": [[[…1 200 levels…]]]}`. Its manifest is `13-deep-json.manifest`.

```
.venv\Scripts\python.exe -m reality2 check findings\13-deep-json-internal-error.rl --files findings\13-deep-json.manifest --root findings\13-deep-json
```

Output (`13.out`):

```
line 2: refused [X001, bug]: internal error RecursionError; nothing formed (please report)
refused (1 statement)
```

## Fix

Bound the JSON nesting depth explicitly (a J code), and walk iteratively. The program-mutation fuzzer
cannot find this, because it never mutates file contents.

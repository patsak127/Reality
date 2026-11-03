# 16. X001 from valid JSON, and one dataset read two ways inside one program

**Category:** bug (internal errors reachable; wrong code where a B-rule should refuse; a
dataset's conformance depends on the Python call depth).
**Spec clause:** SPEC §2 item 13 ("The fuzzers assert X001 never occurs"); README "an internal
error refuses (X001)"; BIDS 1.0.1 §8.4 (PhaseEncodingDirection, SliceEncodingDirection values).
**Severity:** medium. **Confidence:** high.

## Programs

`findings\16-x001-from-valid-json.rl`, dataset `findings\16-ds-a\` (manifest `16-m-a`): the root
sidecar says `"PhaseEncodingDirection": ["j-"]`, a list, which is valid JSON and not a 1.0.1 value.

```
dataset d = sha256:<see the .rl>
claim count(participants(bids(d)))
```

`findings\16-x001-from-valid-json-b.rl`, dataset `findings\16-ds-b\` (manifest `16-m-b`):
`dataset_description.json` has an extra field holding arrays nested 970 deep, valid JSON. The
program uses the dataset twice: first inside a deep expression, then in a shallow one.

```
dataset d = sha256:<see the .rl>
# the same dataset, read first from a deeper expression, then from a shallow one
claim exceeds(widen(widen(widen(widen(widen(widen(widen(widen(number(extra(participant(bids(d), "01"), 2)), tolerance = 0), …, tolerance = 0), c = 0)
claim count(participants(bids(d)))
```

## Commands and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\16-x001-from-valid-json.rl --files findings\16-m-a --root findings\16-ds-a
line 2: refused [X001, bug]: internal error TypeError; nothing formed (please report)
refused (1 statement)

> python -m reality2 check findings\16-x001-from-valid-json-b.rl --files findings\16-m-b --root findings\16-ds-b
line 3: refused [X001, bug]: internal error RecursionError; nothing formed (please report)
line 4: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 1 (Exact)
  #1 = sha256:b9a4f467dbccbed70c3f7f23bf18fcd5bbba5f7ac699a360df63d06f1a454220
  #2 = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
refused (1 statement)
```

The same dataset, with the same bytes, is unreadable for line 3 and conformant for line 4. With
nesting 990 deep both lines are X001; with 960 both form (`scratch\exp\deepjson\` has the series).
`SliceEncodingDirection: {"axis": "k"}` gives the same `TypeError` as the list above.

## Cause

- `ped[0] not in PED` and `{...}.get(sed[0])` hash the JSON value (`bids101.py:317`, `:325`);
  a list or object is unhashable, and the `TypeError` escapes `bids101.read`.
- `parse_json` catches `RecursionError` only inside `json.loads`; its own `walk` (the lone
  surrogate check) recurses in Python outside that `try` (`readers.py:224-237`). How deep it can go
  depends on how deep in the expression `bids(d)` first runs, and a non-`Refusal` error is not
  cached in `Checker.bids`, so the next use tries again from a shallower depth.

## What would fix it

Check the JSON type before using a value (`isinstance(…, str)`, else B10). Make `walk` iterative
(or catch `RecursionError` there too) and put a fixed nesting bound into the JSON reader, so that
the answer is the same at every call depth and on every interpreter.

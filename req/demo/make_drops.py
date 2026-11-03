"""Writes two drop tables for the fair-drops example (untrusted demo producer, stdlib only).

One row per equal-weight slot: a roll picks one of the 1000 slots with equal chance, so a tier's
configured probability is its number of slots / 1000, which v4's share() counts exactly.
  drops_published.tsv  slots matching the published odds 79% / 15% / 5% / 1%
  drops_shaded.tsv     the same published odds, but 6 legendary and 54 rare slots
"""
import hashlib, pathlib, sys

out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "data"
out.mkdir(parents=True, exist_ok=True)
tables = {
    "drops_published.tsv": [("common", 790), ("uncommon", 150), ("rare", 50), ("legendary", 10)],
    "drops_shaded.tsv": [("common", 790), ("uncommon", 150), ("rare", 54), ("legendary", 6)],
}
for name, tiers in tables.items():
    rows = ["slot\titem\ttier"]
    for tier, n in tiers:
        for k in range(n):
            rows.append(f"{len(rows):04d}\t{tier}_item_{k % 5}\t{tier}")
    data = ("\n".join(rows) + "\n").encode()
    (out / name).write_bytes(data)
    print(name, len(rows) - 1, "rows sha256:" + hashlib.sha256(data).hexdigest())

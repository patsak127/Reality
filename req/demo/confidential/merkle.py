"""Optional Merkle root over prompt-id digests (stdlib). UNTRUSTED helper."""
from __future__ import annotations

import hashlib


def leaf(prompt_id: str) -> bytes:
    return hashlib.sha256(b"prompt-id\0" + prompt_id.encode()).digest()


def merkle_root(ids: list[str]) -> str:
    layer = [leaf(i) for i in ids]
    if not layer:
        return hashlib.sha256(b"empty").hexdigest()
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i + 1] if i + 1 < len(layer) else a
            nxt.append(hashlib.sha256(a + b).digest())
        layer = nxt
    return layer[0].hex()

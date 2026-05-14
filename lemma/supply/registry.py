"""Merkle root over per-epoch theorem statements."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def merkle_root(statement_hashes: Iterable[str]) -> str:
    layer = [bytes.fromhex(h) for h in statement_hashes]
    if not layer:
        return "0" * 64
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [_node(layer[i], layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0].hex()


@dataclass(frozen=True, slots=True)
class EpochCommitment:
    epoch_id: int
    root_hex: str

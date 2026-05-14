"""Merkle root over per-epoch theorem statements.

The chain stamp itself goes through ``lemma.transport.chain_commit.anchor_batch``;
this module only computes the root and carries the (epoch_id, root_hex) pair.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass


def _leaf_hash(text: str) -> bytes:
    return hashlib.sha256(b"\x00" + text.encode("utf-8")).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def merkle_root(statement_hashes: Iterable[str]) -> str:
    leaves = [bytes.fromhex(h) if len(h) == 64 else _leaf_hash(h) for h in statement_hashes]
    if not leaves:
        return "0" * 64
    layer = leaves
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer = layer + [layer[-1]]
        layer = [_node_hash(layer[i], layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0].hex()


@dataclass(frozen=True, slots=True)
class EpochCommitment:
    epoch_id: int
    root_hex: str

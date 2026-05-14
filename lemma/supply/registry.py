"""Per-epoch theorem-batch Merkle root, optionally posted via set_commitment."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


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


def commit_to_chain(
    subtensor: Any,
    *,
    wallet: Any,
    netuid: int,
    epoch_id: int,
    root_hex: str,
) -> EpochCommitment:
    """Post (epoch_id, root_hex) to chain via the generic commitment slot.

    Falls back to a no-op when the subtensor object lacks ``set_commitment``; callers may
    persist commitments locally for testnet bootstrap.
    """
    payload = f"lemma-supply:{epoch_id}:{root_hex}".encode()
    set_commitment = getattr(subtensor, "set_commitment", None)
    if callable(set_commitment):
        set_commitment(wallet=wallet, netuid=netuid, data=payload)
    return EpochCommitment(epoch_id=epoch_id, root_hex=root_hex)

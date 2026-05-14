"""Chain-anchored commit-reveal primitives.

The validator stamps each per-epoch theorem batch and each verified miner reveal
on chain via the generic commitment slot. The chain-stamped block becomes the
canonical ``commit_block`` for first-to-solve ordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_KIND_BATCH = "lemma:batch"
_KIND_REVEAL = "lemma:reveal"


@dataclass(frozen=True, slots=True)
class ChainStamp:
    block: int
    kind: str
    payload: bytes


def _stamp(subtensor: Any, wallet: Any, netuid: int, payload: bytes, kind: str) -> ChainStamp:
    setter = getattr(subtensor, "set_commitment", None)
    if callable(setter):
        setter(wallet=wallet, netuid=netuid, data=payload)
    block = 0
    head = getattr(subtensor, "get_current_block", None)
    if callable(head):
        try:
            block = int(head())
        except Exception:  # noqa: BLE001
            block = 0
    return ChainStamp(block=block, kind=kind, payload=payload)


def anchor_batch(
    subtensor: Any,
    *,
    wallet: Any,
    netuid: int,
    epoch_id: int,
    merkle_root_hex: str,
) -> ChainStamp:
    payload = f"{_KIND_BATCH}:{epoch_id}:{merkle_root_hex}".encode("utf-8")
    return _stamp(subtensor, wallet, netuid, payload, _KIND_BATCH)


def anchor_reveal(
    subtensor: Any,
    *,
    wallet: Any,
    netuid: int,
    epoch_id: int,
    theorem_id: str,
    miner_uid: int,
    proof_sha256_hex: str,
) -> ChainStamp:
    payload = (
        f"{_KIND_REVEAL}:{epoch_id}:{theorem_id}:{miner_uid}:{proof_sha256_hex}"
    ).encode("utf-8")
    return _stamp(subtensor, wallet, netuid, payload, _KIND_REVEAL)

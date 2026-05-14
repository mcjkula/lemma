"""Validator-side chain anchor for the per-epoch theorem batch.

One ``set_commitment`` call per epoch carries the batch's Merkle root so the
chain-finalised block is the canonical timestamp for the theorems miners are
about to race on. Per-miner proof timestamps come from HTTP arrival ordering
plus the metagraph's ``block_at_registration`` tie-break — α-rename
fingerprinting handles copyists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_KIND_BATCH = "lemma:batch"


@dataclass(frozen=True, slots=True)
class ChainStamp:
    block: int
    kind: str
    payload: bytes


def _head_block(subtensor: Any) -> int:
    head = getattr(subtensor, "get_current_block", None)
    if not callable(head):
        return 0
    try:
        return int(head())
    except Exception:  # noqa: BLE001
        return 0


def anchor_batch(
    subtensor: Any,
    *,
    wallet: Any,
    netuid: int,
    epoch_id: int,
    merkle_root_hex: str,
) -> ChainStamp:
    payload = f"{_KIND_BATCH}:{epoch_id}:{merkle_root_hex}".encode("utf-8")
    setter = getattr(subtensor, "set_commitment", None)
    if callable(setter):
        setter(wallet=wallet, netuid=netuid, data=payload)
    return ChainStamp(block=_head_block(subtensor), kind=_KIND_BATCH, payload=payload)

"""Validator-side chain anchor for the per-epoch theorem batch.

One ``set_commitment`` call per epoch carries the batch's Merkle root so the
chain-finalised block is the canonical timestamp for the theorems miners are
about to race on. Per-miner proof timestamps come from HTTP arrival ordering
plus the metagraph's ``block_at_registration`` tie-break — α-rename
fingerprinting handles copyists.
"""

from __future__ import annotations

from dataclasses import dataclass

import bittensor

_KIND_BATCH = "lemma:batch"


@dataclass(frozen=True, slots=True)
class ChainStamp:
    block: int
    kind: str
    payload: str


def anchor_batch(
    subtensor: bittensor.Subtensor | None,
    *,
    wallet: bittensor.Wallet,
    netuid: int,
    epoch_id: int,
    merkle_root_hex: str,
) -> ChainStamp:
    """Publish the batch root via ``set_commitment`` and return the stamped block.

    ``subtensor=None`` is the explicit no-chain path used by dry-run / fixture code.
    The default ``set_commitment`` call waits for inclusion, so reading
    ``get_current_block`` immediately after gives the (inclusion-or-later) block at
    which the commitment landed.
    """
    payload = f"{_KIND_BATCH}:{epoch_id}:{merkle_root_hex}"
    if subtensor is None:
        return ChainStamp(block=0, kind=_KIND_BATCH, payload=payload)
    subtensor.set_commitment(wallet=wallet, netuid=netuid, data=payload)
    return ChainStamp(block=int(subtensor.get_current_block()), kind=_KIND_BATCH, payload=payload)

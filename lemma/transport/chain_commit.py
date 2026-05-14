"""Anchor the per-epoch theorem batch on chain via ``set_commitment``."""

from __future__ import annotations

import bittensor


def anchor_batch(
    subtensor: bittensor.Subtensor | None,
    *,
    wallet: bittensor.Wallet,
    netuid: int,
    epoch_id: int,
    merkle_root_hex: str,
) -> int:
    """Publish ``(epoch_id, root)``; return inclusion block (``0`` if no chain)."""
    if subtensor is None:
        return 0
    subtensor.set_commitment(
        wallet=wallet, netuid=netuid,
        data=f"lemma:batch:{epoch_id}:{merkle_root_hex}",
    )
    return int(subtensor.get_current_block())

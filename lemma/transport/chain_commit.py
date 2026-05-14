"""Anchor the per-epoch theorem batch on chain via ``set_commitment``."""

from __future__ import annotations

import bittensor


def anchor_batch(
    subtensor: bittensor.Subtensor,
    *,
    wallet: bittensor.Wallet,
    netuid: int,
    epoch_id: int,
    merkle_root_hex: str,
) -> int:
    subtensor.set_commitment(
        wallet=wallet, netuid=netuid,
        data=f"lemma:batch:{epoch_id}:{merkle_root_hex}",
    )
    return int(subtensor.get_current_block())

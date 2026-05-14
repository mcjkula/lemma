"""Compose the on-chain weight vector."""

from __future__ import annotations


def build_full_weights(
    n: int,
    miner_weights: dict[int, float],
    *,
    burn_share: float,
    burn_uid: int,
) -> list[float]:
    """Earned to miners + burn to owner UID; sums to ``1.0``."""
    full = [0.0] * n
    for uid, w in miner_weights.items():
        full[uid] += w
    full[burn_uid] += burn_share
    return full

"""Compose the on-chain weight vector: earned miner share + burn share."""

from __future__ import annotations


def build_full_weights(
    n: int,
    miner_weights: dict[int, float],
    *,
    burn_share: float,
    burn_uid: int,
) -> list[float]:
    """Return the per-UID weight vector summing to ``1.0``.

    The burn share routes to the subnet owner — Bittensor's primitive for emitting
    to the owner is "set positive weight on the owner's UID." If the owner also
    earned a miner share (i.e. ``burn_uid in miner_weights``), the two stack
    additively, not max-of: the chain sees one weight per UID and treats it as the
    validator's vote distribution over that UID, regardless of why we voted.

    Preconditions, enforced by ``resolve_burn_uid`` + ``compute_budget``:

    - ``n > 0`` (the owner is always registered, so a synced metagraph has ``n ≥ 1``)
    - ``0 <= burn_uid < n``
    - ``burn_share + sum(miner_weights.values()) == 1.0``
    """
    full = [0.0] * n
    for uid, w in miner_weights.items():
        if 0 <= uid < n:
            full[uid] += max(0.0, w)
    full[burn_uid] += float(burn_share)
    return full

"""Compose the on-chain weight vector: earned miner share + burn share."""

from __future__ import annotations


def build_full_weights(
    n: int,
    miner_weights: dict[int, float],
    *,
    burn_share: float = 0.0,
    burn_uid: int | None = None,
) -> tuple[list[float], bool]:
    """Return ``(weights, skip_chain_write)``.

    ``miner_weights`` and ``burn_share`` together should sum to ``1.0`` (the epoch
    budget). When a ``burn_uid`` is configured, the burn share routes to that UID
    and the validator always publishes weights — there is no "skip and pay last
    epoch's winners" path. The skip flag is True only if there is literally nothing
    to publish (no miners earned anything *and* no burn UID is configured).
    """
    if n <= 0:
        return [], True
    full = [0.0] * n
    for uid, w in miner_weights.items():
        if isinstance(uid, int) and 0 <= uid < n:
            full[uid] = max(0.0, w)
    if burn_uid is not None and 0 <= burn_uid < n and burn_share > 0.0:
        full[burn_uid] = max(full[burn_uid], float(burn_share))
    total = sum(full)
    if total <= 0.0:
        return [0.0] * n, True
    return [w / total for w in full], False

"""Normalize epoch weights and skip on empty rounds."""

from __future__ import annotations


def build_full_weights(n: int, weights_by_uid: dict[int, float]) -> tuple[list[float], bool]:
    """Return ``(weights, skip_chain_write)``; ``skip`` is True when no miner scored."""
    if not weights_by_uid or n <= 0:
        return [0.0] * max(0, n), True
    full = [0.0] * n
    for uid, w in weights_by_uid.items():
        if isinstance(uid, int) and 0 <= uid < n:
            full[uid] = w
    total = sum(full)
    if total > 0:
        full = [w / total for w in full]
    return full, False

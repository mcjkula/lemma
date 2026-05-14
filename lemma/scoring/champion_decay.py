"""Anti-monopoly reign decay (Affine pattern, daily 0.33% default).

A miner that tops the budget for K consecutive epochs has its raw earned share
multiplied by ``(1 - decay_per_epoch) ** max(0, K - 1)``. Decay is applied at the
budget layer (``lemma.scoring.budget``); this module is the pure multiplier.
"""

from __future__ import annotations

DEFAULT_DECAY_PER_EPOCH: float = 0.0033


def reign_factor(reign_length: int, *, decay_per_epoch: float = DEFAULT_DECAY_PER_EPOCH) -> float:
    k = max(0, int(reign_length) - 1)
    d = max(0.0, min(1.0, float(decay_per_epoch)))
    return (1.0 - d) ** k


def apply_decay(
    weights: dict[int, float],
    reign_by_uid: dict[int, int],
    *,
    decay_per_epoch: float = DEFAULT_DECAY_PER_EPOCH,
) -> dict[int, float]:
    """Multiply each weight by its UID's reign factor (no renormalisation)."""
    out = {
        uid: max(0.0, float(w)) * reign_factor(reign_by_uid.get(uid, 0), decay_per_epoch=decay_per_epoch)
        for uid, w in weights.items()
    }
    return {uid: w for uid, w in out.items() if w > 0.0}

"""Anti-monopoly reign decay (~0.33%/epoch default)."""

from __future__ import annotations

DEFAULT_DECAY_PER_EPOCH: float = 0.0033


def reign_factor(reign_length: int, *, decay_per_epoch: float = DEFAULT_DECAY_PER_EPOCH) -> float:
    return (1.0 - decay_per_epoch) ** max(0, reign_length - 1)

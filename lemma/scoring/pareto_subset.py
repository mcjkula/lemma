"""Pareto-layer peel over per-miner per-theorem reward maps.

A miner *dominates* another when its per-theorem reward is ≥ on every theorem and
> on at least one. Identical reward vectors do not dominate each other — both stay
on the same layer. Layers peel until empty; layer-share decay is applied at the
budget layer (``lemma.scoring.budget``).
"""

from __future__ import annotations


def _dominates(a: dict[str, float], b: dict[str, float]) -> bool:
    strict = False
    for key in a.keys() | b.keys():
        ax = a.get(key, 0.0)
        bx = b.get(key, 0.0)
        if ax < bx:
            return False
        if ax > bx:
            strict = True
    return strict


def pareto_layers(rewards: dict[int, dict[str, float]]) -> list[list[int]]:
    pool = {uid: dict(row) for uid, row in rewards.items()}
    layers: list[list[int]] = []
    while pool:
        front = [
            uid
            for uid, row in pool.items()
            if not any(_dominates(other_row, row) for other_uid, other_row in pool.items() if other_uid != uid)
        ]
        if not front:
            layers.append(sorted(pool))
            break
        layers.append(sorted(front))
        for uid in front:
            pool.pop(uid, None)
    return layers

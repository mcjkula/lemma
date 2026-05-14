"""Pareto-layer peel over per-miner per-theorem reward maps."""

from __future__ import annotations


def _dominates(a: dict[str, float], b: dict[str, float]) -> bool:
    strict = False
    for key in a.keys() | b.keys():
        ax, bx = a.get(key, 0.0), b.get(key, 0.0)
        if ax < bx:
            return False
        if ax > bx:
            strict = True
    return strict


def pareto_layers(rewards: dict[int, dict[str, float]]) -> list[list[int]]:
    pool = dict(rewards)
    layers: list[list[int]] = []
    while pool:
        front = [
            uid for uid, row in pool.items()
            if not any(_dominates(other, row) for o_uid, other in pool.items() if o_uid != uid)
        ]
        layers.append(sorted(front))
        for uid in front:
            del pool[uid]
    return layers

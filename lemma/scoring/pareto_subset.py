"""Pareto-layer peel over per-miner per-theorem reward maps.

A miner *dominates* another when its per-theorem reward is ≥ on every theorem and
> on at least one. Identical reward vectors do not dominate each other — both stay
on the same layer. Layers peel until empty; layer ``k`` collects geometric share
``base_share * (decay ** k)``.
"""

from __future__ import annotations


def _dominates(a: dict[str, float], b: dict[str, float]) -> bool:
    """``a`` strictly Pareto-dominates ``b`` over the union of theorem keys."""
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
    """Peel Pareto-front layers from a per-miner per-theorem reward map."""
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


def layer_weights(layers: list[list[int]], *, decay: float = 0.5) -> dict[int, float]:
    """Return UID → unnormalized share with layer-k weight ``decay**k`` split among members."""
    out: dict[int, float] = {}
    for k, layer in enumerate(layers):
        if not layer:
            continue
        share = (decay**k) / len(layer)
        for uid in layer:
            out[uid] = share
    total = sum(out.values())
    if total <= 0.0:
        return {}
    return {uid: v / total for uid, v in out.items()}

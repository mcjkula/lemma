"""Per-theorem reward priced by how few miners solved it."""

from __future__ import annotations


def base_reward(solve_fraction: float, *, beta: float = 2.0) -> float:
    """Map ``solve_fraction`` in [0, 1] to a non-negative base reward.

    A theorem solved by every active miner pays 0; one solved by a single miner
    pays ~1 (for typical beta in [1, 3]).
    """
    x = max(0.0, min(1.0, float(solve_fraction)))
    return max(0.0, (1.0 - x) ** float(beta))


def solve_fractions(
    solved_uids_by_theorem: dict[str, set[int]],
    active_uids: set[int],
) -> dict[str, float]:
    if not active_uids:
        return {tid: 0.0 for tid in solved_uids_by_theorem}
    denom = float(len(active_uids))
    return {
        tid: len(uids & active_uids) / denom
        for tid, uids in solved_uids_by_theorem.items()
    }

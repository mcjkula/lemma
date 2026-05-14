"""Per-theorem reward priced by how few miners solved it."""

from __future__ import annotations


def base_reward(solve_fraction: float, *, beta: float = 2.0) -> float:
    """``(1 - solve_fraction) ** beta`` — uniformly-solved theorems pay 0."""
    return float(max(0.0, (1.0 - solve_fraction) ** beta))


def solve_fractions(
    solved_uids_by_theorem: dict[str, set[int]],
    active_uids: set[int],
) -> dict[str, float]:
    if not active_uids:
        return {tid: 0.0 for tid in solved_uids_by_theorem}
    denom = len(active_uids)
    return {tid: len(uids & active_uids) / denom for tid, uids in solved_uids_by_theorem.items()}

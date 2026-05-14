"""Per-epoch budget: earned to miners, unearned burns to the owner UID."""

from __future__ import annotations

from lemma.scoring.champion_decay import reign_factor
from lemma.scoring.first_to_solve import Solve, rank_solvers
from lemma.scoring.observed_difficulty import base_reward, solve_fractions
from lemma.scoring.pareto_subset import pareto_layers

RANK_DECAY = 0.5
LAYER_DECAY = 0.5
MAX_RANK_PAID = 10


def compute_budget(
    solved_by_theorem: dict[str, set[int]],
    *,
    active_uids: set[int],
    registration_block: dict[int, int],
    commit_block: int,
    reign_by_uid: dict[int, int],
) -> tuple[dict[int, float], float]:
    """Return ``(miner_weights, burn_share)`` summing to ``1.0``."""
    fractions = solve_fractions(solved_by_theorem, active_uids)
    ranks = rank_solvers(
        (Solve(uid, tid, commit_block) for tid, uids in solved_by_theorem.items() for uid in uids),
        registration_block,
    )

    rewards: dict[int, dict[str, float]] = {}
    for tid, uids in solved_by_theorem.items():
        r0 = base_reward(fractions[tid])
        if r0 <= 0.0:
            continue
        for uid in uids:
            rank = ranks[(tid, uid)]
            if rank < MAX_RANK_PAID:
                rewards.setdefault(uid, {})[tid] = r0 * (RANK_DECAY ** rank)

    if not rewards:
        return {}, 1.0

    raw: dict[int, float] = {}
    for k, layer in enumerate(pareto_layers(rewards)):
        layer_factor = LAYER_DECAY ** k
        for uid in layer:
            raw[uid] = sum(rewards[uid].values()) * layer_factor * reign_factor(reign_by_uid.get(uid, 0))

    total = sum(raw.values())
    if total > 1.0:
        return {uid: w / total for uid, w in raw.items()}, 0.0
    return raw, 1.0 - total

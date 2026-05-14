"""Per-epoch budget computation: earned share goes to miners, the rest burns.

Every epoch has a budget of ``1.0``. The earned share is the sum of
``base_reward(t) × 0.5^rank × 0.5^pareto_layer × reign_factor(uid)`` over verified,
fingerprint-deduplicated (miner, theorem) solves, capped at ``1.0``. Whatever the
network didn't earn is the burn share — the protocol's structural answer to
"the network produced less than full value this epoch." It routes to the burn
hotkey (subnet owner / treasury). There is no notion of "skip and pay yesterday's
winners"; emission you didn't earn this epoch you don't get.
"""

from __future__ import annotations

from lemma.scoring.champion_decay import reign_factor
from lemma.scoring.first_to_solve import Solve, rank_solvers
from lemma.scoring.observed_difficulty import base_reward, solve_fractions
from lemma.scoring.pareto_subset import pareto_layers

RANK_DECAY: float = 0.5
LAYER_DECAY: float = 0.5
MAX_RANK_PAID: int = 10


def compute_budget(
    solved_by_theorem: dict[str, set[int]],
    *,
    active_uids: set[int],
    registration_block: dict[int, int],
    commit_block: int,
    reign_by_uid: dict[int, int],
) -> tuple[dict[int, float], float]:
    """Return ``(miner_weights, burn_share)`` summing to ``1.0``.

    ``miner_weights[uid]`` is the absolute share of the epoch budget earned by that
    miner; ``burn_share`` is the unearned remainder. ``commit_block`` is the chain
    block at which the validator anchored the epoch's theorem batch — the shared
    timestamp every solve inherits, with ``registration_block`` as the deterministic
    tie-break.
    """
    fractions = solve_fractions(solved_by_theorem, active_uids)
    solves = [
        Solve(uid, tid, commit_block)
        for tid, uids in solved_by_theorem.items()
        for uid in uids
    ]
    ranks = rank_solvers(solves, registration_block)

    rewards: dict[int, dict[str, float]] = {}
    for tid, uids in solved_by_theorem.items():
        r0 = base_reward(fractions.get(tid, 0.0))
        if r0 <= 0.0:
            continue
        for uid in uids:
            rank = ranks.get((tid, uid), MAX_RANK_PAID)
            if rank < MAX_RANK_PAID:
                rewards.setdefault(uid, {})[tid] = r0 * (RANK_DECAY ** rank)

    if not rewards:
        return {}, 1.0

    layers = pareto_layers(rewards)
    raw: dict[int, float] = {}
    for k, layer in enumerate(layers):
        layer_factor = LAYER_DECAY ** k
        for uid in layer:
            uid_total = sum(rewards.get(uid, {}).values())
            raw[uid] = uid_total * layer_factor * reign_factor(reign_by_uid.get(uid, 0))

    total_earned = sum(raw.values())
    if total_earned <= 0.0:
        return {}, 1.0

    earned_share = min(1.0, total_earned)
    if total_earned > 1.0:
        scale = earned_share / total_earned
        raw = {uid: w * scale for uid, w in raw.items()}
    return raw, 1.0 - earned_share

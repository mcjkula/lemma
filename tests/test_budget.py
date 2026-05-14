"""Earned vs burn share — the per-epoch budget invariant."""

from lemma.scoring.budget import compute_budget


def _empty_blocks(n: int) -> dict[int, int]:
    return {i: 100 for i in range(n)}


def test_no_solves_burns_full_budget() -> None:
    weights, burn = compute_budget(
        {"t": set()},
        active_uids=set(range(30)), registration_block=_empty_blocks(30),
        commit_block_by_uid={}, default_commit_block=100, reign_by_uid={},
    )
    assert weights == {}
    assert burn == 1.0


def test_one_solver_hard_theorem_burns_little() -> None:
    # 1 solver in a network of 30: solve_fraction ≈ 0.033, base_reward ≈ 0.935.
    weights, burn = compute_budget(
        {"t": {1}},
        active_uids=set(range(30)), registration_block=_empty_blocks(30),
        commit_block_by_uid={1: 100}, default_commit_block=100, reign_by_uid={},
    )
    assert set(weights) == {1}
    assert weights[1] > 0.9
    assert burn < 0.1
    assert abs(weights[1] + burn - 1.0) < 1e-9


def test_full_network_solves_burns_full_budget() -> None:
    # solve_fraction = 1.0 → base_reward = 0 → nothing earned.
    weights, burn = compute_budget(
        {"t": set(range(10))},
        active_uids=set(range(10)), registration_block=_empty_blocks(10),
        commit_block_by_uid={}, default_commit_block=100, reign_by_uid={},
    )
    assert weights == {}
    assert burn == 1.0


def test_single_solver_modest_theorem_burns_remainder() -> None:
    # 1 solver in 5: solve_fraction = 0.2, base_reward = 0.64.
    # rank 0, layer 0, no reign decay → earned = 0.64, burn = 0.36.
    weights, burn = compute_budget(
        {"t": {1}},
        active_uids=set(range(5)), registration_block=_empty_blocks(5),
        commit_block_by_uid={1: 100}, default_commit_block=100, reign_by_uid={},
    )
    assert set(weights) == {1}
    assert abs(weights[1] - 0.64) < 1e-9
    assert abs(burn - 0.36) < 1e-9
    assert abs(weights[1] + burn - 1.0) < 1e-9


def test_multiple_solvers_split_full_budget_when_cap_hits() -> None:
    # 3 solvers in 30: each strictly dominated by the earlier-registered, so they
    # peel into three Pareto layers with rank + layer decays. Cumulative earned
    # exceeds 1.0 → capped, burn = 0.
    weights, burn = compute_budget(
        {"t": {1, 2, 3}},
        active_uids=set(range(30)),
        registration_block={1: 100, 2: 110, 3: 120, **{i: 200 for i in range(30) if i not in {1, 2, 3}}},
        commit_block_by_uid={1: 100, 2: 100, 3: 100},
        default_commit_block=100, reign_by_uid={},
    )
    assert set(weights) == {1, 2, 3}
    assert weights[1] > weights[2] > weights[3]
    assert burn == 0.0
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_long_reign_reduces_earned_increases_burn() -> None:
    # Compare uid 1 with 1-epoch reign vs 1000-epoch reign on the same hard theorem.
    fresh, _ = compute_budget(
        {"t": {1}},
        active_uids=set(range(30)), registration_block=_empty_blocks(30),
        commit_block_by_uid={1: 100}, default_commit_block=100, reign_by_uid={1: 1},
    )
    stale, burn_stale = compute_budget(
        {"t": {1}},
        active_uids=set(range(30)), registration_block=_empty_blocks(30),
        commit_block_by_uid={1: 100}, default_commit_block=100, reign_by_uid={1: 1000},
    )
    assert stale[1] < fresh[1]
    assert burn_stale > (1.0 - fresh[1])


def test_budget_caps_at_one() -> None:
    # Many solvers, hard theorem — raw earned might exceed 1; output must cap.
    weights, burn = compute_budget(
        {"t": set(range(5))},
        active_uids=set(range(100)),
        registration_block={i: 100 + i for i in range(100)},
        commit_block_by_uid={i: 100 for i in range(5)},
        default_commit_block=100, reign_by_uid={},
    )
    total = sum(weights.values()) + burn
    assert abs(total - 1.0) < 1e-9
    assert burn >= 0.0

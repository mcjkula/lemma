"""Observed-difficulty reward pricing."""

from lemma.scoring.observed_difficulty import base_reward, solve_fractions


def test_no_solvers_pays_full_base() -> None:
    assert base_reward(0.0) == 1.0


def test_everyone_solves_pays_zero() -> None:
    assert base_reward(1.0) == 0.0


def test_monotone_decreasing_in_solve_fraction() -> None:
    assert base_reward(0.1) > base_reward(0.5) > base_reward(0.9)


def test_beta_steepness() -> None:
    assert base_reward(0.5, beta=3.0) < base_reward(0.5, beta=2.0)


def test_solve_fractions_per_theorem() -> None:
    fracs = solve_fractions(
        {"a": {1, 2}, "b": {1, 2, 3}, "c": set()},
        active_uids={1, 2, 3, 4},
    )
    assert fracs["a"] == 0.5
    assert fracs["b"] == 0.75
    assert fracs["c"] == 0.0


def test_solve_fractions_ignores_inactive_uids() -> None:
    fracs = solve_fractions({"a": {99}}, active_uids={1, 2})
    assert fracs["a"] == 0.0

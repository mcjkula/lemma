"""Per-theorem solver ranking with incumbency tie-break."""

from lemma.scoring.first_to_solve import Solve, rank_solvers


def test_single_solver_gets_rank_zero() -> None:
    ranks = rank_solvers([Solve(miner_uid=3, theorem_id="t1", commit_block=10)], {3: 1})
    assert ranks == {("t1", 3): 0}


def test_distinct_blocks_ordered_by_block() -> None:
    solves = [
        Solve(miner_uid=1, theorem_id="t", commit_block=20),
        Solve(miner_uid=2, theorem_id="t", commit_block=10),
        Solve(miner_uid=3, theorem_id="t", commit_block=15),
    ]
    ranks = rank_solvers(solves, {1: 1, 2: 1, 3: 1})
    assert ranks[("t", 2)] == 0
    assert ranks[("t", 3)] == 1
    assert ranks[("t", 1)] == 2


def test_block_tie_breaks_by_registration() -> None:
    solves = [
        Solve(miner_uid=1, theorem_id="t", commit_block=10),
        Solve(miner_uid=2, theorem_id="t", commit_block=10),
    ]
    ranks = rank_solvers(solves, {1: 100, 2: 50})
    assert ranks[("t", 2)] == 0
    assert ranks[("t", 1)] == 1


def test_registration_tie_breaks_by_uid() -> None:
    solves = [
        Solve(miner_uid=7, theorem_id="t", commit_block=5),
        Solve(miner_uid=3, theorem_id="t", commit_block=5),
    ]
    ranks = rank_solvers(solves, {3: 1, 7: 1})
    assert ranks[("t", 3)] == 0
    assert ranks[("t", 7)] == 1


def test_per_theorem_independent() -> None:
    solves = [
        Solve(miner_uid=1, theorem_id="a", commit_block=5),
        Solve(miner_uid=2, theorem_id="a", commit_block=10),
        Solve(miner_uid=2, theorem_id="b", commit_block=5),
        Solve(miner_uid=1, theorem_id="b", commit_block=10),
    ]
    ranks = rank_solvers(solves, {1: 1, 2: 1})
    assert ranks[("a", 1)] == 0
    assert ranks[("a", 2)] == 1
    assert ranks[("b", 2)] == 0
    assert ranks[("b", 1)] == 1

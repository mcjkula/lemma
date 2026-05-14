"""Pareto subset domination."""

from lemma.scoring.pareto_subset import pareto_layers


def test_strict_superset_dominates() -> None:
    assert pareto_layers({1: {"a": 1.0, "b": 1.0}, 2: {"a": 1.0}}) == [[1], [2]]


def test_identical_rows_share_front() -> None:
    assert pareto_layers({1: {"a": 1.0, "b": 1.0}, 2: {"a": 1.0, "b": 1.0}}) == [[1, 2]]


def test_disjoint_solves_both_non_dominated() -> None:
    assert pareto_layers({1: {"a": 1.0}, 2: {"b": 1.0}}) == [[1, 2]]


def test_empty_input() -> None:
    assert pareto_layers({}) == []

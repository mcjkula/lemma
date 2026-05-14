"""Pareto subset domination."""

from lemma.scoring.pareto_subset import layer_weights, pareto_layers


def test_strict_superset_dominates() -> None:
    layers = pareto_layers({1: {"a": 1.0, "b": 1.0}, 2: {"a": 1.0}})
    assert layers == [[1], [2]]


def test_identical_rows_share_front() -> None:
    layers = pareto_layers({1: {"a": 1.0, "b": 1.0}, 2: {"a": 1.0, "b": 1.0}})
    assert layers == [[1, 2]]


def test_disjoint_solves_both_non_dominated() -> None:
    layers = pareto_layers({1: {"a": 1.0}, 2: {"b": 1.0}})
    assert layers == [[1, 2]]


def test_layer_weights_share_decays() -> None:
    layers = [[1, 2], [3]]
    w = layer_weights(layers, decay=0.5)
    front_share = (1.0 / 2) / (1.0 / 2 + 0.5)
    back_share = 0.5 / (1.0 / 2 + 0.5)
    assert abs((w[1] + w[2]) - front_share) < 1e-9
    assert abs(w[3] - back_share) < 1e-9
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_empty_input() -> None:
    assert pareto_layers({}) == []
    assert layer_weights([]) == {}

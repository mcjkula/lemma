"""Reign-length decay (Affine pattern)."""

from lemma.scoring.champion_decay import apply_decay, reign_factor


def test_first_epoch_no_decay() -> None:
    assert reign_factor(0) == 1.0
    assert reign_factor(1) == 1.0


def test_factor_decays_monotonically() -> None:
    assert 1.0 > reign_factor(5) > reign_factor(50) > reign_factor(500)


def test_apply_decay_renormalises() -> None:
    out = apply_decay({1: 0.5, 2: 0.5}, {1: 30, 2: 1})
    assert out[2] > out[1]
    assert abs(sum(out.values()) - 1.0) < 1e-9


def test_zero_weight_inputs_yield_empty() -> None:
    assert apply_decay({1: 0.0}, {1: 99}) == {}

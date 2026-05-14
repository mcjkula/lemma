"""Earned miner share + burn share → on-chain weight vector."""

from lemma.validator.weights_policy import build_full_weights


def test_normalizes_when_burn_uid_unset() -> None:
    full, skip = build_full_weights(4, {1: 0.5, 2: 0.5})
    assert not skip
    assert abs(sum(full) - 1.0) < 1e-9


def test_routes_burn_share_to_burn_uid() -> None:
    full, skip = build_full_weights(4, {1: 0.7}, burn_share=0.3, burn_uid=0)
    assert not skip
    assert abs(full[0] - 0.3) < 1e-9
    assert abs(full[1] - 0.7) < 1e-9
    assert abs(sum(full) - 1.0) < 1e-9


def test_unsolved_epoch_burns_full_budget() -> None:
    full, skip = build_full_weights(3, {}, burn_share=1.0, burn_uid=0)
    assert not skip
    assert full == [1.0, 0.0, 0.0]


def test_no_burn_uid_and_no_solves_skips() -> None:
    full, skip = build_full_weights(3, {}, burn_share=1.0, burn_uid=None)
    assert skip
    assert full == [0.0, 0.0, 0.0]


def test_zero_n_skips() -> None:
    full, skip = build_full_weights(0, {1: 1.0})
    assert skip
    assert full == []

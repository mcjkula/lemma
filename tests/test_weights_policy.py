"""Weight vector construction for set_weights."""

from lemma.validator.weights_policy import build_full_weights


def test_build_full_weights_normalizes() -> None:
    full, skip = build_full_weights(4, {1: 0.5, 2: 0.5})
    assert not skip
    assert len(full) == 4
    assert abs(sum(full) - 1.0) < 1e-6
    assert full[0] == 0.0 and full[3] == 0.0


def test_empty_skip() -> None:
    full, skip = build_full_weights(3, {})
    assert skip
    assert full == [0.0, 0.0, 0.0]


def test_zero_n_returns_empty_and_skip() -> None:
    full, skip = build_full_weights(0, {1: 1.0})
    assert skip
    assert full == []

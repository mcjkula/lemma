"""Merkle root over epoch statement hashes."""

from lemma.supply.registry import merkle_root


def test_empty_root_is_zero() -> None:
    assert merkle_root([]) == "0" * 64


def test_single_leaf_root_is_stable() -> None:
    a = merkle_root(["a" * 64])
    b = merkle_root(["a" * 64])
    assert a == b


def test_distinct_inputs_distinct_roots() -> None:
    assert merkle_root(["a" * 64]) != merkle_root(["b" * 64])


def test_odd_input_count_handled() -> None:
    out = merkle_root(["a" * 64, "b" * 64, "c" * 64])
    assert len(out) == 64

"""Merkle root over epoch statement hashes."""

from lemma.supply.registry import commit_to_chain, merkle_root


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


def test_commit_invokes_subtensor_when_available() -> None:
    captured: dict[str, object] = {}

    class _Sub:
        def set_commitment(self, *, wallet, netuid, data) -> None:  # type: ignore[no-untyped-def]
            captured.update({"netuid": netuid, "data": data})

    out = commit_to_chain(_Sub(), wallet=None, netuid=42, epoch_id=7, root_hex="ff" * 32)
    assert out.epoch_id == 7
    assert captured["netuid"] == 42
    assert b"lemma-supply:7:" in captured["data"]


def test_commit_no_op_when_subtensor_lacks_method() -> None:
    out = commit_to_chain(object(), wallet=None, netuid=1, epoch_id=0, root_hex="ff" * 32)
    assert out.root_hex == "ff" * 32

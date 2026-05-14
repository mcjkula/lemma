"""anchor_batch publishes the per-epoch theorem-batch root via set_commitment."""

from dataclasses import dataclass, field

from lemma.transport.chain_commit import anchor_batch


@dataclass
class _StubSubtensor:
    head: int = 1000
    set_commitment_calls: list[dict] = field(default_factory=list)

    def get_current_block(self) -> int:
        return self.head

    def set_commitment(self, *, wallet, netuid, data) -> None:  # noqa: ANN001
        self.set_commitment_calls.append({"wallet": wallet, "netuid": netuid, "data": data})


def test_anchor_batch_with_none_subtensor_returns_zero_block() -> None:
    stamp = anchor_batch(
        None, wallet=object(), netuid=1, epoch_id=5, merkle_root_hex="ab" * 32,
    )
    assert stamp.block == 0
    assert stamp.kind == "lemma:batch"
    assert stamp.payload == f"lemma:batch:5:{'ab' * 32}"


def test_anchor_batch_calls_set_commitment_with_str_payload() -> None:
    st = _StubSubtensor(head=42)
    wallet = object()
    stamp = anchor_batch(
        st, wallet=wallet, netuid=7, epoch_id=12, merkle_root_hex="cd" * 32,
    )
    assert stamp.block == 42
    assert len(st.set_commitment_calls) == 1
    call = st.set_commitment_calls[0]
    assert call["wallet"] is wallet
    assert call["netuid"] == 7
    # The SDK signature is set_commitment(data: str) — passing bytes raises.
    assert isinstance(call["data"], str)
    assert call["data"] == f"lemma:batch:12:{'cd' * 32}"


def test_anchor_batch_block_reflects_head_after_commit() -> None:
    # ``set_commitment`` waits for inclusion by default; ``get_current_block`` after
    # the call therefore returns the inclusion-or-later block.
    st = _StubSubtensor(head=100)
    stamp = anchor_batch(
        st, wallet=object(), netuid=0, epoch_id=0, merkle_root_hex="0" * 64,
    )
    assert stamp.block == 100

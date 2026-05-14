from dataclasses import dataclass, field

from lemma.transport.chain_commit import anchor_batch


@dataclass
class _StubSubtensor:
    head: int = 1000
    calls: list[dict] = field(default_factory=list)

    def get_current_block(self) -> int:
        return self.head

    def set_commitment(self, *, wallet, netuid, data) -> None:
        self.calls.append({"wallet": wallet, "netuid": netuid, "data": data})


def test_publishes_str_payload_and_returns_head_block() -> None:
    st = _StubSubtensor(head=42)
    wallet = object()
    block = anchor_batch(st, wallet=wallet, netuid=7, epoch_id=12, merkle_root_hex="cd" * 32)
    assert block == 42
    assert st.calls == [{"wallet": wallet, "netuid": 7, "data": f"lemma:batch:12:{'cd' * 32}"}]
    assert isinstance(st.calls[0]["data"], str)

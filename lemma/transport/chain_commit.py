"""Chain-anchored commit-reveal primitives.

The validator stamps each per-epoch theorem batch on chain via ``set_commitment``;
miners stamp their per-epoch commit hash via ``set_reveal_commitment`` so the
chain-finalised block becomes the canonical ``commit_block`` for first-to-solve
ordering (replaces the process-local commit cache called out in audit 3 §4.1).

Rate limit: ``knowledge/subnet.invariants.yaml#chain_commits`` — 1 per 100 blocks
per hotkey. Miners batch all their per-epoch theorem commits into one Merkle root.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_KIND_BATCH = "lemma:batch"


@dataclass(frozen=True, slots=True)
class ChainStamp:
    block: int
    kind: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class ChainCommit:
    miner_hotkey_ss58: str
    miner_uid: int
    commit_hex: str
    commit_block: int


def _head_block(subtensor: Any) -> int:
    head = getattr(subtensor, "get_current_block", None)
    if not callable(head):
        return 0
    try:
        return int(head())
    except Exception:  # noqa: BLE001
        return 0


def anchor_batch(
    subtensor: Any,
    *,
    wallet: Any,
    netuid: int,
    epoch_id: int,
    merkle_root_hex: str,
) -> ChainStamp:
    payload = f"{_KIND_BATCH}:{epoch_id}:{merkle_root_hex}".encode("utf-8")
    setter = getattr(subtensor, "set_commitment", None)
    if callable(setter):
        setter(wallet=wallet, netuid=netuid, data=payload)
    return ChainStamp(block=_head_block(subtensor), kind=_KIND_BATCH, payload=payload)


def submit_commit(
    subtensor: Any,
    *,
    wallet: Any,
    netuid: int,
    epoch_id: int,
    commit_hex: str,
    reveal_in_blocks: int = 100,
) -> ChainStamp:
    """Miner side: post one chain-anchored commit for the per-epoch batch."""
    payload = f"lemma:miner_commit:{epoch_id}:{commit_hex}".encode("utf-8")
    setter = getattr(subtensor, "set_reveal_commitment", None)
    if callable(setter):
        setter(wallet=wallet, netuid=netuid, data=payload, reveal_block=_head_block(subtensor) + max(1, int(reveal_in_blocks)))
    return ChainStamp(block=_head_block(subtensor), kind="lemma:miner_commit", payload=payload)


def fetch_commits(
    subtensor: Any,
    *,
    netuid: int,
    epoch_id: int,
    uid_by_hotkey: dict[str, int],
) -> list[ChainCommit]:
    """Validator side: read chain-stamped per-miner commits for ``epoch_id``.

    Returns rows for hotkeys present in ``uid_by_hotkey``; missing entries are simply absent.
    """
    getter = getattr(subtensor, "get_reveal_commitments", None)
    if not callable(getter):
        return []
    try:
        rows = getter(netuid=netuid) or []
    except Exception:  # noqa: BLE001
        return []
    prefix = f"lemma:miner_commit:{epoch_id}:".encode("utf-8")
    out: list[ChainCommit] = []
    for row in rows:
        hotkey = str(getattr(row, "hotkey", "") or row.get("hotkey", ""))
        data = bytes(getattr(row, "data", b"") or row.get("data", b""))
        block = int(getattr(row, "block", 0) or row.get("block", 0))
        if not data.startswith(prefix):
            continue
        commit_hex = data[len(prefix):].decode("utf-8", errors="replace")
        uid = uid_by_hotkey.get(hotkey)
        if uid is None:
            continue
        out.append(ChainCommit(miner_hotkey_ss58=hotkey, miner_uid=uid, commit_hex=commit_hex, commit_block=block))
    return out

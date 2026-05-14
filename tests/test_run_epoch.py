"""End-to-end run_epoch: assert set_weights gets the right vector."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest
from bittensor.core.types import ExtrinsicResponse
from bittensor_wallet import Keypair

from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import VerifyResult
from lemma.problems.base import Problem
from lemma.protocol import RevealPayload
from lemma.validator import epoch as ep
from lemma.validator import verify as verify_mod


@dataclass
class _Axon:
    ip: str = "1.1.1.1"
    port: int = 8000


@dataclass
class _Meta:
    n: np.ndarray = field(default_factory=lambda: np.array([4], dtype=np.int64))
    hotkeys: list[str] = field(default_factory=lambda: ["owner", "alice", "bob", "carol"])
    axons: list[_Axon] = field(default_factory=lambda: [_Axon() for _ in range(4)])
    block_at_registration: list[int] = field(default_factory=lambda: [10, 20, 30, 40])
    owner_hotkey: str = "owner"


@dataclass
class _FakeSubtensor:
    head: int = 1000
    set_weights_calls: list[dict] = field(default_factory=list)
    meta: _Meta = field(default_factory=_Meta)

    def get_current_block(self) -> int:
        return self.head

    def metagraph(self, _netuid: int, **_kwargs):
        return self.meta

    def tempo(self, _netuid: int, block: int | None = None) -> int:
        return 100

    def blocks_until_next_epoch(self, _netuid: int) -> int:
        return 10

    def set_commitment(self, *, wallet, netuid, data) -> ExtrinsicResponse:
        return ExtrinsicResponse(success=True)

    def set_weights(self, *, wallet, netuid, uids, weights, wait_for_inclusion=False) -> ExtrinsicResponse:
        self.set_weights_calls.append(
            {"netuid": netuid, "uids": list(uids), "weights": list(weights)},
        )
        return ExtrinsicResponse(success=True)


class _FakeWallet:
    def __init__(self, name: str = "default", hotkey: str = "default") -> None:
        self._kp = Keypair.create_from_uri("//Validator")

    @property
    def hotkey(self) -> Keypair:
        return self._kp


def _problem(tid: str) -> Problem:
    return Problem(
        id=tid, theorem_name=tid, type_expr="True",
        split="medium", lean_toolchain="leanprover/lean4:v4.30.0", mathlib_rev="abc",
    )


def _reveal(tid: str, proof: str) -> RevealPayload:
    return RevealPayload(theorem_id=tid, metronome_id="1", proof_script=proof)


@pytest.fixture
def base_settings(tmp_path: Path) -> LemmaSettings:
    return LemmaSettings().model_copy(update={
        "netuid": 7,
        "lemma_reputation_state_path": tmp_path / "rep.json",
        "lemma_supply_freshness_path": tmp_path / "fresh.txt",
        "problem_seed_mode": "quantize",
        "problem_seed_quantize_blocks": 100,
    })


def _patch_epoch_deps(
    monkeypatch, subt: _FakeSubtensor, *,
    problems: list[Problem],
    replies: dict[str, dict[int, RevealPayload]],
) -> None:
    monkeypatch.setattr(ep, "get_subtensor", lambda _s: subt)
    monkeypatch.setattr(ep.bittensor, "Wallet", _FakeWallet)
    monkeypatch.setattr(ep, "build_problems_for_epoch", lambda _s, **_: (problems, 900))

    async def _broadcast(*, challenge, **_kwargs):
        return replies.get(challenge.theorem_id, {})

    monkeypatch.setattr(ep, "broadcast_challenge", _broadcast)
    monkeypatch.setattr(verify_mod, "_verify", lambda _s, _p, _proof: VerifyResult(passed=True, reason="ok"))
    monkeypatch.setattr(ep, "append_corpus", lambda _entries: None)


def test_burns_full_budget_to_owner_when_no_solves(base_settings, monkeypatch) -> None:
    subt = _FakeSubtensor()
    _patch_epoch_deps(monkeypatch, subt, problems=[_problem("t1")], replies={})
    asyncio.run(ep.run_epoch(base_settings, dry_run=False))

    call = subt.set_weights_calls[0]
    assert call["netuid"] == 7
    assert call["uids"] == [0, 1, 2, 3]
    assert call["weights"] == [1.0, 0.0, 0.0, 0.0]


def test_routes_earned_to_solver_and_burn_to_owner(base_settings, monkeypatch) -> None:
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt, problems=[_problem("t1")],
        replies={"t1": {1: _reveal("t1", "by trivial")}},
    )
    asyncio.run(ep.run_epoch(base_settings, dry_run=False))

    w = subt.set_weights_calls[0]["weights"]
    assert abs(sum(w) - 1.0) < 1e-9
    assert w[1] > 0.5  # alice earned
    assert w[0] > 0.4  # owner got burn remainder
    assert w[2] == w[3] == 0.0


def test_alpha_rename_dedup_drops_byte_identical_proof_from_second_miner(base_settings, monkeypatch) -> None:
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt, problems=[_problem("t1")],
        replies={"t1": {1: _reveal("t1", "by trivial"), 2: _reveal("t1", "by trivial")}},
    )
    asyncio.run(ep.run_epoch(base_settings, dry_run=False))

    w = subt.set_weights_calls[0]["weights"]
    assert w[1] > 0.0
    assert w[2] == 0.0


def test_dry_run_does_not_call_set_weights(base_settings, monkeypatch) -> None:
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt, problems=[_problem("t1")],
        replies={"t1": {1: _reveal("t1", "by trivial")}},
    )
    asyncio.run(ep.run_epoch(base_settings, dry_run=True))
    assert subt.set_weights_calls == []


def test_returns_miner_weights_dict(base_settings, monkeypatch) -> None:
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt, problems=[_problem("t1")],
        replies={"t1": {1: _reveal("t1", "by trivial")}},
    )
    out = asyncio.run(ep.run_epoch(base_settings, dry_run=False))
    assert set(out) == {1}
    assert out[1] > 0.5

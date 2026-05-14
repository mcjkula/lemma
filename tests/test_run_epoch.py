"""End-to-end run_epoch: assert the SDK gets called with the right weights and root.

This test mocks every external dependency (wallet, subtensor, metagraph, HTTP
broadcast, Lean verify, corpus append) and asserts the pipeline composes the
correct calls into the chain. The scoring math itself is covered by
``test_budget.py``; here we verify the *plumbing* between scoring and chain.
"""

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
    set_commitment_calls: list[dict] = field(default_factory=list)
    meta: _Meta = field(default_factory=_Meta)

    def get_current_block(self) -> int:
        return self.head

    def metagraph(self, _netuid: int, **_kwargs):  # noqa: ANN201
        return self.meta

    def tempo(self, _netuid: int, block: int | None = None) -> int:  # noqa: ARG002
        return 100

    def blocks_until_next_epoch(self, _netuid: int) -> int:
        return 10

    def set_commitment(self, *, wallet, netuid, data) -> ExtrinsicResponse:  # noqa: ANN001
        self.set_commitment_calls.append({"wallet": wallet, "netuid": netuid, "data": data})
        return ExtrinsicResponse(success=True)

    def set_weights(self, *, wallet, netuid, uids, weights, wait_for_inclusion=False) -> ExtrinsicResponse:  # noqa: ANN001, ARG002
        self.set_weights_calls.append(
            {"wallet": wallet, "netuid": netuid, "uids": list(uids), "weights": list(weights)},
        )
        return ExtrinsicResponse(success=True)


class _FakeWallet:
    """Minimal stand-in for ``bittensor.Wallet`` with a usable hotkey keypair."""

    def __init__(self, name: str = "default", hotkey: str = "default") -> None:  # noqa: ARG002
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


def _verify_ok(_s, _p, _proof) -> VerifyResult:
    return VerifyResult(passed=True, reason="ok")


@pytest.fixture
def base_settings(tmp_path: Path) -> LemmaSettings:
    return LemmaSettings().model_copy(update={
        "netuid": 7,
        "lemma_reputation_state_path": tmp_path / "rep.json",
        "lemma_supply_freshness_path": tmp_path / "fresh.txt",
        "problem_seed_mode": "quantize",
        "problem_seed_quantize_blocks": 100,
    })


def _patch_epoch_deps(monkeypatch, subt: _FakeSubtensor, *,
                     problems: list[Problem],
                     anchored_block: int,
                     replies: dict[str, dict[int, RevealPayload]]) -> None:
    monkeypatch.setattr(ep, "get_subtensor", lambda _s: subt)
    monkeypatch.setattr(ep.bittensor, "Wallet", _FakeWallet)
    monkeypatch.setattr(ep, "build_problems_for_epoch",
                        lambda _settings, **_: (problems, anchored_block))

    async def _fake_broadcast(*, challenge, **_kwargs):  # noqa: ARG001
        return replies.get(challenge.theorem_id, {})

    monkeypatch.setattr(ep, "broadcast_challenge", _fake_broadcast)
    monkeypatch.setattr(verify_mod, "_verify", _verify_ok)
    monkeypatch.setattr(ep, "append_corpus", lambda _entries: None)


def test_run_epoch_burns_full_budget_to_owner_when_no_solves(
    base_settings: LemmaSettings, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The chain-anchor call lives inside build_problems_for_epoch (covered by
    # test_chain_commit.py); this test asserts the weight-setting boundary.
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt,
        problems=[_problem("t1")],
        anchored_block=900,
        replies={},  # No miner replies — nothing solved.
    )

    asyncio.run(ep.run_epoch(base_settings, dry_run=False))

    # Weights set exactly once; burn_share = 1.0 routed to owner UID = 0.
    assert len(subt.set_weights_calls) == 1
    call = subt.set_weights_calls[0]
    assert call["netuid"] == 7
    assert call["uids"] == [0, 1, 2, 3]
    weights = call["weights"]
    assert abs(sum(weights) - 1.0) < 1e-9
    assert abs(weights[0] - 1.0) < 1e-9  # owner UID
    assert weights[1] == weights[2] == weights[3] == 0.0


def test_run_epoch_routes_earned_to_solver_and_burn_to_owner(
    base_settings: LemmaSettings, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 1 solver (UID 1, alice) on a hard theorem (1-of-4 = solve_fraction 0.25):
    # base_reward = (1 - 0.25)^2 = 0.5625; rank-0, layer-0, no reign decay.
    # earned ≈ 0.5625, burn ≈ 0.4375 → both visible on the weight vector.
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt,
        problems=[_problem("t1")],
        anchored_block=900,
        replies={"t1": {1: _reveal("t1", "by trivial")}},
    )

    asyncio.run(ep.run_epoch(base_settings, dry_run=False))

    assert len(subt.set_weights_calls) == 1
    weights = subt.set_weights_calls[0]["weights"]
    assert abs(sum(weights) - 1.0) < 1e-9
    # alice earned the solver share.
    assert weights[1] > 0.5
    # owner UID 0 received the unearned remainder.
    assert weights[0] > 0.4
    # Non-solvers stay at zero.
    assert weights[2] == 0.0
    assert weights[3] == 0.0
    # Earned + burn = 1.0 invariant on the wire.
    assert abs(weights[0] + weights[1] - 1.0) < 1e-9


def test_run_epoch_dedups_byte_identical_proofs(
    base_settings: LemmaSettings, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # alice (uid 1, registered block 20) and bob (uid 2, registered block 30) both
    # submit the byte-identical proof. α-rename dedup keeps the first that arrives;
    # since dict iteration is insertion order, alice wins. bob earns nothing.
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt,
        problems=[_problem("t1")],
        anchored_block=900,
        replies={"t1": {1: _reveal("t1", "by trivial"), 2: _reveal("t1", "by trivial")}},
    )

    asyncio.run(ep.run_epoch(base_settings, dry_run=False))

    weights = subt.set_weights_calls[0]["weights"]
    assert weights[1] > 0.0
    assert weights[2] == 0.0


def test_run_epoch_dry_run_does_not_call_chain(
    base_settings: LemmaSettings, monkeypatch: pytest.MonkeyPatch,
) -> None:
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt,
        problems=[_problem("t1")],
        anchored_block=900,
        replies={"t1": {1: _reveal("t1", "by trivial")}},
    )

    asyncio.run(ep.run_epoch(base_settings, dry_run=True))

    # set_commitment lives in build_problems_for_epoch which we mocked — it
    # *would* normally fire. set_weights is gated by dry_run and must not fire.
    assert subt.set_weights_calls == []


def test_run_epoch_returns_miner_weights_dict(
    base_settings: LemmaSettings, monkeypatch: pytest.MonkeyPatch,
) -> None:
    subt = _FakeSubtensor()
    _patch_epoch_deps(
        monkeypatch, subt,
        problems=[_problem("t1")],
        anchored_block=900,
        replies={"t1": {1: _reveal("t1", "by trivial")}},
    )

    out = asyncio.run(ep.run_epoch(base_settings, dry_run=False))
    assert set(out) == {1}
    assert out[1] > 0.5

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx
import numpy as np
from bittensor_wallet import Keypair
from lemma.protocol import ChallengePayload, RevealPayload, to_json
from lemma.transport.client import broadcast_challenge, miner_url


@dataclass
class _Axon:
    ip: str
    port: int


@dataclass
class _Meta:
    n: np.ndarray = field(default_factory=lambda: np.array([0], dtype=np.int64))
    hotkeys: list[str] = field(default_factory=list)
    axons: list[_Axon] = field(default_factory=list)


def test_miner_url_skips_unset_axon() -> None:
    assert miner_url(_Meta(axons=[_Axon(ip="0.0.0.0", port=0)]), 0) is None


def test_miner_url_skips_zero_port() -> None:
    assert miner_url(_Meta(axons=[_Axon(ip="1.2.3.4", port=0)]), 0) is None


def test_miner_url_returns_http_url() -> None:
    assert miner_url(_Meta(axons=[_Axon(ip="1.2.3.4", port=8000)]), 0) == "http://1.2.3.4:8000"


_CHALLENGE = ChallengePayload(
    theorem_id="t", theorem_statement="True", lean_toolchain="x", mathlib_rev="y",
    deadline_block=1, metronome_id="1",
)


def _broadcast(metagraph: _Meta, transport: httpx.MockTransport) -> dict[int, RevealPayload]:
    async def _go() -> dict[int, RevealPayload]:
        async with httpx.AsyncClient(transport=transport) as client:
            return await broadcast_challenge(
                client=client, metagraph=metagraph,
                keypair=Keypair.create_from_uri("//Alice"),
                challenge=_CHALLENGE, timeout_s=2.0, concurrency=4,
            )

    return asyncio.run(_go())


def test_broadcast_skips_unreachable_and_collects_responses() -> None:
    metagraph = _Meta(
        n=np.array([3], dtype=np.int64),
        hotkeys=["k0", "k1", "k2"],
        axons=[_Axon("0.0.0.0", 0), _Axon("1.1.1.1", 8001), _Axon("2.2.2.2", 8002)],
    )
    replies = {
        "http://1.1.1.1:8001/lemma/reveal": to_json(
            RevealPayload(theorem_id="t", metronome_id="1", proof_script="by trivial"),
        ),
        "http://2.2.2.2:8002/lemma/reveal": to_json(
            RevealPayload(theorem_id="t", metronome_id="1", proof_script="by exact True.intro"),
        ),
    }

    def handler(req: httpx.Request) -> httpx.Response:
        body = replies.get(str(req.url))
        return httpx.Response(200, content=body) if body else httpx.Response(404)

    out = _broadcast(metagraph, httpx.MockTransport(handler))
    assert {uid: r.proof_script for uid, r in out.items()} == {1: "by trivial", 2: "by exact True.intro"}


def test_broadcast_drops_empty_proof_replies() -> None:
    metagraph = _Meta(n=np.array([1], dtype=np.int64), hotkeys=["k0"], axons=[_Axon("1.1.1.1", 8001)])
    body = to_json(RevealPayload(theorem_id="t", metronome_id="1", proof_script=""))
    out = _broadcast(metagraph, httpx.MockTransport(lambda _: httpx.Response(200, content=body)))
    assert out == {}


def test_broadcast_swallows_http_errors() -> None:
    metagraph = _Meta(n=np.array([1], dtype=np.int64), hotkeys=["k0"], axons=[_Axon("1.1.1.1", 8001)])
    out = _broadcast(metagraph, httpx.MockTransport(lambda _: httpx.Response(500)))
    assert out == {}

"""miner_url derivation and broadcast_challenge fan-out."""

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
    m = _Meta(axons=[_Axon(ip="0.0.0.0", port=0)])
    assert miner_url(m, 0) is None


def test_miner_url_skips_zero_port() -> None:
    m = _Meta(axons=[_Axon(ip="1.2.3.4", port=0)])
    assert miner_url(m, 0) is None


def test_miner_url_skips_oob_uid() -> None:
    m = _Meta(axons=[_Axon(ip="1.2.3.4", port=8000)])
    assert miner_url(m, 7) is None


def test_miner_url_returns_http_url() -> None:
    m = _Meta(axons=[_Axon(ip="1.2.3.4", port=8000)])
    assert miner_url(m, 0) == "http://1.2.3.4:8000"


def _challenge() -> ChallengePayload:
    return ChallengePayload(
        theorem_id="t", theorem_statement="True", lean_toolchain="x", mathlib_rev="y",
        deadline_block=1, metronome_id="1",
    )


def _make_handler(replies_by_url: dict[str, bytes]):
    def handler(request: httpx.Request) -> httpx.Response:
        body = replies_by_url.get(str(request.url))
        if body is None:
            return httpx.Response(404)
        return httpx.Response(200, content=body)

    return handler


def test_broadcast_skips_unreachable_and_collects_responses() -> None:
    # Three miners: uid 0 unreachable (0.0.0.0), uid 1 reachable, uid 2 reachable.
    metagraph = _Meta(
        n=np.array([3], dtype=np.int64),
        hotkeys=["k0", "k1", "k2"],
        axons=[
            _Axon(ip="0.0.0.0", port=0),
            _Axon(ip="1.1.1.1", port=8001),
            _Axon(ip="2.2.2.2", port=8002),
        ],
    )
    replies = {
        "http://1.1.1.1:8001/lemma/reveal": to_json(
            RevealPayload(theorem_id="t", metronome_id="1", proof_script="by trivial"),
        ),
        "http://2.2.2.2:8002/lemma/reveal": to_json(
            RevealPayload(theorem_id="t", metronome_id="1", proof_script="by exact True.intro"),
        ),
    }
    transport = httpx.MockTransport(_make_handler(replies))
    keypair = Keypair.create_from_uri("//Alice")

    async def _go() -> dict[int, RevealPayload]:
        async with httpx.AsyncClient(transport=transport) as client:
            return await broadcast_challenge(
                client=client, metagraph=metagraph, keypair=keypair,
                challenge=_challenge(), timeout_s=2.0, concurrency=4,
            )

    out = asyncio.run(_go())
    assert set(out) == {1, 2}
    assert out[1].proof_script == "by trivial"
    assert out[2].proof_script == "by exact True.intro"


def test_broadcast_drops_empty_proof_replies() -> None:
    metagraph = _Meta(
        n=np.array([1], dtype=np.int64),
        hotkeys=["k0"],
        axons=[_Axon(ip="1.1.1.1", port=8001)],
    )
    replies = {
        "http://1.1.1.1:8001/lemma/reveal": to_json(
            RevealPayload(theorem_id="t", metronome_id="1", proof_script=""),
        ),
    }
    transport = httpx.MockTransport(_make_handler(replies))
    keypair = Keypair.create_from_uri("//Alice")

    async def _go() -> dict[int, RevealPayload]:
        async with httpx.AsyncClient(transport=transport) as client:
            return await broadcast_challenge(
                client=client, metagraph=metagraph, keypair=keypair,
                challenge=_challenge(), timeout_s=2.0, concurrency=4,
            )

    out = asyncio.run(_go())
    assert out == {}


def test_broadcast_swallows_http_errors() -> None:
    # 500 from a miner shouldn't crash the loop.
    metagraph = _Meta(
        n=np.array([1], dtype=np.int64),
        hotkeys=["k0"],
        axons=[_Axon(ip="1.1.1.1", port=8001)],
    )
    transport = httpx.MockTransport(lambda _: httpx.Response(500))
    keypair = Keypair.create_from_uri("//Alice")

    async def _go() -> dict[int, RevealPayload]:
        async with httpx.AsyncClient(transport=transport) as client:
            return await broadcast_challenge(
                client=client, metagraph=metagraph, keypair=keypair,
                challenge=_challenge(), timeout_s=2.0, concurrency=4,
            )

    out = asyncio.run(_go())
    assert out == {}

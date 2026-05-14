"""HTTP client: sign requests with Epistula and broadcast challenges to miners."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from bittensor_wallet import Keypair
from loguru import logger

from lemma.protocol import ChallengePayload, RevealPayload, from_json, to_json
from lemma.transport.epistula import sign


async def signed_post(
    client: httpx.AsyncClient,
    url: str,
    body: bytes,
    *,
    keypair: Keypair,
    signed_for_ss58: str,
    extra_headers: dict[str, str] | None = None,
    timeout_s: float | None = None,
) -> httpx.Response:
    headers = sign(keypair=keypair, body=body, signed_for_ss58=signed_for_ss58).to_http_headers()
    headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    return await client.post(url, content=body, headers=headers, timeout=timeout_s)


def miner_url(metagraph: Any, uid: int) -> str | None:
    try:
        ax = metagraph.axons[uid]
    except (IndexError, AttributeError):
        return None
    ip = (getattr(ax, "ip", "") or "").strip()
    port = int(getattr(ax, "port", 0) or 0)
    if not ip or ip == "0.0.0.0" or port <= 0:
        return None
    return f"http://{ip}:{port}"


async def _query_one(
    client: httpx.AsyncClient, url: str, keypair: Keypair, receiver_ss58: str,
    body: bytes, timeout_s: float,
) -> RevealPayload | None:
    try:
        r = await signed_post(
            client, f"{url}/lemma/reveal", body,
            keypair=keypair, signed_for_ss58=receiver_ss58, timeout_s=timeout_s,
        )
    except httpx.HTTPError as e:
        logger.debug("miner http error: {}", e)
        return None
    if r.status_code != 200:
        return None
    try:
        return from_json(RevealPayload, r.content)
    except (ValueError, TypeError):
        return None


async def broadcast_challenge(
    *,
    client: httpx.AsyncClient,
    metagraph: Any,
    keypair: Keypair,
    challenge: ChallengePayload,
    timeout_s: float,
    concurrency: int,
) -> dict[int, RevealPayload]:
    body = to_json(challenge)
    sem = asyncio.Semaphore(max(1, concurrency))
    out: dict[int, RevealPayload] = {}

    async def _one(uid: int) -> None:
        url = miner_url(metagraph, uid)
        if url is None:
            return
        async with sem:
            reply = await _query_one(
                client, url, keypair, metagraph.hotkeys[uid], body, timeout_s,
            )
        if reply is not None and reply.proof_script:
            out[uid] = reply

    async with asyncio.TaskGroup() as tg:
        for uid in range(metagraph.n):
            tg.create_task(_one(uid))
    return out

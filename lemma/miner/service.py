"""Miner: FastAPI app behind Epistula-signed HTTP."""

from __future__ import annotations

import bittensor
import uvicorn
from bittensor.core.extrinsics.serving import serve_extrinsic
from fastapi import Depends, FastAPI, Request, Response
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.miner.forward import Solver, handle_commit, handle_reveal
from lemma.miner.public_ip import discover_public_ipv4
from lemma.protocol import ChallengePayload, VerifyReply, from_json, to_json
from lemma.transport.server import RequestContext, verify_epistula


def build_app(wallet: bittensor.Wallet, *, solver: Solver | None = None) -> FastAPI:
    app = FastAPI()
    receiver_ss58 = wallet.hotkey.ss58_address

    async def _verify(request: Request) -> RequestContext:
        return await verify_epistula(request, receiver_ss58)

    @app.post("/lemma/commit")
    async def commit(ctx: RequestContext = Depends(_verify)) -> Response:  # noqa: B008
        payload = from_json(ChallengePayload, ctx.body)
        reply = await handle_commit(payload, solver=solver)
        return Response(to_json(reply), media_type="application/json")

    @app.post("/lemma/reveal")
    async def reveal(ctx: RequestContext = Depends(_verify)) -> Response:  # noqa: B008
        payload = from_json(ChallengePayload, ctx.body)
        reply = await handle_reveal(payload, solver=solver)
        return Response(to_json(reply), media_type="application/json")

    @app.get("/lemma/health")
    async def health() -> Response:
        return Response(to_json(VerifyReply(accepted=True)), media_type="application/json")

    return app


class MinerService:
    def __init__(self, settings: LemmaSettings) -> None:
        self.settings = settings

    def run(self) -> None:
        s = self.settings
        setup_logging(s.log_level)
        wallet = bittensor.Wallet(name=s.wallet_cold, hotkey=s.wallet_hot)
        external_ip = s.axon_external_ip
        if not external_ip and s.axon_discover_external_ip:
            external_ip = discover_public_ipv4()
        if external_ip:
            serve_extrinsic(
                subtensor=get_subtensor(s), wallet=wallet, ip=external_ip,
                port=s.axon_port, protocol=4, netuid=s.netuid,
            )
        logger.info("Miner HTTP listening port={} hotkey={}", s.axon_port, wallet.hotkey.ss58_address)
        uvicorn.run(build_app(wallet), host="0.0.0.0", port=s.axon_port, log_level=s.log_level.lower())

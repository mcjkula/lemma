"""Miner: FastAPI app behind Epistula-signed HTTP."""

from __future__ import annotations

import bittensor
import uvicorn
from fastapi import Depends, FastAPI, Request
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.miner.forward import Solver, handle_commit, handle_reveal
from lemma.miner.public_ip import discover_public_ipv4
from lemma.protocol import ChallengePayload, CommitPayload, RevealPayload, VerifyReply
from lemma.transport.server import RequestContext, verify_epistula


def build_app(
    settings: LemmaSettings,  # noqa: ARG001 — held for future per-app hooks
    wallet: bittensor.Wallet,
    *,
    solver: Solver | None = None,
) -> FastAPI:
    app = FastAPI()
    receiver_ss58 = wallet.hotkey.ss58_address

    async def _verify(request: Request) -> RequestContext:
        return await verify_epistula(request, receiver_ss58)

    @app.post("/lemma/commit", response_model=CommitPayload)
    async def commit(payload: ChallengePayload, _: RequestContext = Depends(_verify)) -> CommitPayload:
        return await handle_commit(payload, solver=solver)

    @app.post("/lemma/reveal", response_model=RevealPayload)
    async def reveal(payload: ChallengePayload, _: RequestContext = Depends(_verify)) -> RevealPayload:
        return await handle_reveal(payload, solver=solver)

    @app.get("/lemma/health", response_model=VerifyReply)
    async def health() -> VerifyReply:
        return VerifyReply(accepted=True)

    return app


class MinerService:
    def __init__(self, settings: LemmaSettings | None = None) -> None:
        self.settings = settings or LemmaSettings()

    def run(self) -> None:
        setup_logging(self.settings.log_level)
        s = self.settings
        wallet = bittensor.Wallet(name=s.wallet_cold, hotkey=s.wallet_hot)
        subtensor = get_subtensor(s)
        external_ip = (s.axon_external_ip or "").strip() or discover_public_ipv4()
        if external_ip:
            bittensor.serve_extrinsic(
                subtensor=subtensor,
                wallet=wallet,
                ip=external_ip,
                port=s.axon_port,
                protocol=4,
                netuid=s.netuid,
            )
        logger.info(
            "Miner HTTP listening port={} hotkey={}",
            s.axon_port,
            wallet.hotkey.ss58_address,
        )
        app = build_app(s, wallet)
        uvicorn.run(app, host="0.0.0.0", port=s.axon_port, log_level=s.log_level.lower())

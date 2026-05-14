"""Miner: FastAPI app behind Epistula-signed HTTP."""

from __future__ import annotations

import bittensor as bt
import uvicorn
from fastapi import Depends, FastAPI
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.miner.forward import handle_commit, handle_reveal
from lemma.miner.prover import LLMProver
from lemma.miner.public_ip import discover_public_ipv4
from lemma.protocol import ChallengePayload, CommitPayload, RevealPayload, VerifyReply
from lemma.transport.server import RequestContext, verify_epistula


def build_app(settings: LemmaSettings, wallet: bt.Wallet) -> FastAPI:
    prover = LLMProver(settings)
    app = FastAPI()
    receiver_ss58 = wallet.hotkey.ss58_address

    async def _verify(request_ctx: RequestContext = Depends(_make_verifier(receiver_ss58))) -> RequestContext:
        return request_ctx

    @app.post("/lemma/commit", response_model=CommitPayload)
    async def commit(payload: ChallengePayload, ctx: RequestContext = Depends(_verify)) -> CommitPayload:
        return await handle_commit(settings, prover, payload, ctx.sender_ss58)

    @app.post("/lemma/reveal", response_model=RevealPayload)
    async def reveal(payload: ChallengePayload, ctx: RequestContext = Depends(_verify)) -> RevealPayload:
        return await handle_reveal(settings, prover, payload, ctx.sender_ss58)

    @app.get("/lemma/health", response_model=VerifyReply)
    async def health() -> VerifyReply:
        return VerifyReply(accepted=True)

    return app


def _make_verifier(receiver_ss58: str):
    async def _dep(
        request_ctx: RequestContext = Depends(verify_epistula),
    ) -> RequestContext:
        return request_ctx

    async def _bound(request_ctx: RequestContext = Depends(verify_epistula)) -> RequestContext:
        return request_ctx

    return _bound


class MinerService:
    def __init__(self, settings: LemmaSettings | None = None) -> None:
        self.settings = settings or LemmaSettings()

    def run(self) -> None:
        setup_logging(self.settings.log_level)
        s = self.settings
        wallet = bt.Wallet(name=s.wallet_cold, hotkey=s.wallet_hot)
        subtensor = get_subtensor(s)
        external_ip = (s.axon_external_ip or "").strip() or discover_public_ipv4()
        if external_ip:
            bt.serve_extrinsic(
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

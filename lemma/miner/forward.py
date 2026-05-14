"""Miner request handlers: invoke the operator solver, chain-anchor the commit."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from lemma.protocol import ChallengePayload, CommitPayload, RevealPayload
from lemma.transport.chain_commit import submit_commit

Solver = Callable[[ChallengePayload], Awaitable[str]]


async def _empty_solver(_: ChallengePayload) -> str:
    return ""


def _commitment_hex(proof_script: str, nonce_hex: str) -> str:
    h = hashlib.sha256()
    h.update(proof_script.encode("utf-8"))
    h.update(b"\x1e")
    h.update(nonce_hex.encode("utf-8"))
    return h.hexdigest()


async def handle_commit(
    payload: ChallengePayload,
    *,
    solver: Solver | None = None,
    subtensor: Any | None = None,
    wallet: Any | None = None,
    netuid: int = 0,
) -> CommitPayload:
    proof = await (solver or _empty_solver)(payload)
    nonce_hex = secrets.token_hex(16)
    commit_hex = _commitment_hex(proof, nonce_hex)
    if subtensor is not None and wallet is not None:
        submit_commit(
            subtensor, wallet=wallet, netuid=netuid,
            epoch_id=int(payload.metronome_id or 0), commit_hex=commit_hex,
        )
    return CommitPayload(
        theorem_id=payload.theorem_id,
        metronome_id=payload.metronome_id,
        proof_commitment_hex=commit_hex,
    )


async def handle_reveal(
    payload: ChallengePayload,
    *,
    solver: Solver | None = None,
) -> RevealPayload:
    proof = await (solver or _empty_solver)(payload)
    return RevealPayload(
        theorem_id=payload.theorem_id,
        metronome_id=payload.metronome_id,
        proof_script=proof,
    )

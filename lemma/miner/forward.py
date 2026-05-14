"""Miner request handlers: invoke the operator solver and return the commit/reveal."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Awaitable, Callable

from lemma.protocol import ChallengePayload, CommitPayload, RevealPayload

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
) -> CommitPayload:
    proof = await (solver or _empty_solver)(payload)
    commit_hex = _commitment_hex(proof, secrets.token_hex(16))
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

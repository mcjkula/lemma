"""Miner request handlers: invoke the operator solver, return a reveal."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from lemma.protocol import ChallengePayload, RevealPayload

Solver = Callable[[ChallengePayload], Awaitable[str]]


async def _empty_solver(_: ChallengePayload) -> str:
    return ""


async def handle_reveal(payload: ChallengePayload, *, solver: Solver | None = None) -> RevealPayload:
    return RevealPayload(
        theorem_id=payload.theorem_id,
        metronome_id=payload.metronome_id,
        proof_script=await (solver or _empty_solver)(payload),
    )

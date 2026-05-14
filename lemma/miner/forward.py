"""Miner request handlers: produce proofs for incoming challenges."""

from __future__ import annotations

import hashlib
import secrets

from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.lean.verify_runner import run_lean_verify
from lemma.miner.prover import LLMProver
from lemma.problems.factory import resolve_problem
from lemma.protocol import ChallengePayload, CommitPayload, RevealPayload


def _commitment_hex(proof_script: str, nonce_hex: str) -> str:
    h = hashlib.sha256()
    h.update(proof_script.encode("utf-8"))
    h.update(b"\x1e")
    h.update(nonce_hex.encode("utf-8"))
    return h.hexdigest()


async def _solve(prover: LLMProver, payload: ChallengePayload) -> str:
    return await prover.solve(payload)


def _local_verify_ok(settings: LemmaSettings, payload: ChallengePayload, proof_script: str) -> bool:
    if not settings.miner_local_verify:
        return True
    problem = resolve_problem(settings, payload.theorem_id)
    vr = run_lean_verify(
        settings,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=problem,
        proof_script=proof_script,
    )
    if not vr.passed:
        logger.warning("local verify failed: {}", vr.reason)
    return vr.passed


async def handle_commit(
    settings: LemmaSettings,
    prover: LLMProver,
    payload: ChallengePayload,
    sender_ss58: str,
) -> CommitPayload:
    proof = await _solve(prover, payload)
    if not _local_verify_ok(settings, payload, proof):
        proof = ""
    nonce_hex = secrets.token_hex(16)
    return CommitPayload(
        theorem_id=payload.theorem_id,
        metronome_id=payload.metronome_id,
        proof_commitment_hex=_commitment_hex(proof, nonce_hex),
    )


async def handle_reveal(
    settings: LemmaSettings,
    prover: LLMProver,
    payload: ChallengePayload,
    sender_ss58: str,
) -> RevealPayload:
    proof = await _solve(prover, payload)
    if not _local_verify_ok(settings, payload, proof):
        proof = ""
    return RevealPayload(
        theorem_id=payload.theorem_id,
        metronome_id=payload.metronome_id,
        proof_script=proof,
    )

"""Verify each reveal via the Lean kernel and α-rename dedup duplicates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.lean.sandbox import VerifyResult
from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem
from lemma.protocol import RevealPayload
from lemma.scoring.dedup import submission_fingerprint

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def _verify(settings: LemmaSettings, problem: Problem, proof_script: str) -> VerifyResult:
    try:
        return run_lean_verify(
            settings, verify_timeout_s=settings.lean_verify_timeout_s,
            problem=problem, proof_script=proof_script,
        )
    except Exception as e:  # noqa: BLE001
        return VerifyResult(passed=False, reason="docker_error", stderr_tail=str(e)[:8000])


def verified_solves(
    settings: LemmaSettings,
    problems: dict[str, Problem],
    replies_by_theorem: dict[str, dict[int, RevealPayload]],
) -> tuple[dict[str, set[int]], dict[str, dict[int, str]]]:
    solved: dict[str, set[int]] = {tid: set() for tid in problems}
    proofs: dict[str, dict[int, str]] = {tid: {} for tid in problems}
    seen: dict[str, set[str]] = {tid: set() for tid in problems}
    for tid, replies in replies_by_theorem.items():
        problem = problems[tid]
        for uid, reply in replies.items():
            fp = submission_fingerprint(problem.challenge_source(), reply.proof_script)
            if fp in seen[tid]:
                continue
            if not _verify(settings, problem, reply.proof_script).passed:
                continue
            seen[tid].add(fp)
            solved[tid].add(uid)
            proofs[tid][uid] = reply.proof_script
    return solved, proofs

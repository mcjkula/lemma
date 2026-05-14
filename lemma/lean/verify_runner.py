"""Run Lean verify via LeanSandbox."""

from __future__ import annotations

from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import LeanSandbox, VerifyResult
from lemma.problems.base import Problem


def run_lean_verify(
    settings: LemmaSettings,
    *,
    verify_timeout_s: int,
    problem: Problem,
    proof_script: str,
) -> VerifyResult:
    return LeanSandbox(
        docker_worker=settings.lemma_lean_docker_worker,
        timeout_s=verify_timeout_s,
        workspace_cache_include_submission_hash=settings.lemma_lean_workspace_cache_include_submission_hash,
        workspace_cache_max_dirs=settings.lemma_lean_workspace_cache_max_dirs,
        workspace_cache_max_bytes=settings.lemma_lean_workspace_cache_max_bytes,
    ).verify(problem, proof_script)

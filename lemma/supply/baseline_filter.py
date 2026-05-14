"""Non-triviality filter: drop statements closed by a baseline tactic set."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings

_BASELINE_TACTICS = ("decide", "simp_all", "omega", "norm_num", "exact?")


def _baseline_submission(problem: Problem) -> str:
    imports = "\n".join(f"import {m}" for m in problem.imports)
    return (
        f"{imports}\n\n"
        "namespace Submission\n\n"
        f"theorem {problem.theorem_name} : {problem.type_expr} := by\n"
        f"  first | {' | '.join(_BASELINE_TACTICS)}\n\n"
        "end Submission\n"
    )


def is_trivial(settings: LemmaSettings, problem: Problem) -> bool:
    return run_lean_verify(
        settings,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=problem,
        proof_script=_baseline_submission(problem),
    ).passed

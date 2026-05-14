"""Non-triviality filter: drop statements that close under a baseline tactic set."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings

_BASELINE_TACTICS: tuple[str, ...] = ("decide", "simp_all", "omega", "norm_num", "exact?")


def _baseline_submission(problem: Problem) -> str:
    imports = "\n".join(f"import {m}" for m in problem.imports)
    tactic_chain = " | ".join(_BASELINE_TACTICS)
    return (
        f"{imports}\n\n"
        "namespace Submission\n\n"
        f"theorem {problem.theorem_name} : {problem.type_expr} := by\n"
        f"  first | {tactic_chain}\n\n"
        "end Submission\n"
    )


def is_trivial(
    settings: LemmaSettings,
    problem: Problem,
    *,
    budget_s: int | None = None,
) -> bool:
    """Return True when the baseline tactic chain closes the goal."""
    timeout = int(budget_s if budget_s is not None else settings.lean_verify_timeout_s)
    vr = run_lean_verify(
        settings,
        verify_timeout_s=timeout,
        problem=problem,
        proof_script=_baseline_submission(problem),
    )
    return vr.passed

"""Materialize a per-problem Lake workspace for sandbox verification."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from lemma.problems.base import Problem


def workspace_template_cache_key(problem: Problem) -> str:
    h = hashlib.sha256()
    for part in (problem.id, problem.mathlib_rev, problem.lean_toolchain,
                 problem.challenge_source(), problem.solution_source()):
        h.update(part.encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()[:48]


def workspace_verify_cache_key(
    problem: Problem, submission_src: str, *, include_submission_fingerprint: bool,
) -> str:
    base = workspace_template_cache_key(problem)
    if not include_submission_fingerprint:
        return base
    return f"{base}_{hashlib.sha256(submission_src.encode('utf-8')).hexdigest()[:16]}"


_LAKEFILE = '''name = "lemma_stub"
version = "0.1.0"
defaultTargets = ["Challenge", "Solution", "Submission"]

[leanOptions]
autoImplicit = false

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "{rev}"

[[lean_lib]]
name = "Challenge"

[[lean_lib]]
name = "Solution"

[[lean_lib]]
name = "Submission"
'''


def materialize_workspace(
    dest: Path, problem: Problem, submission_lean: str, *, preserve_lake: bool = False,
) -> None:
    if not (preserve_lake and dest.exists() and (dest / ".lake").is_dir()):
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
    (dest / "Challenge.lean").write_text(problem.challenge_source(), encoding="utf-8")
    (dest / "Solution.lean").write_text(problem.solution_source(), encoding="utf-8")
    (dest / "Submission.lean").write_text(submission_lean, encoding="utf-8")
    (dest / "lean-toolchain").write_text(problem.lean_toolchain.strip() + "\n", encoding="utf-8")
    (dest / "lakefile.toml").write_text(_LAKEFILE.format(rev=problem.mathlib_rev), encoding="utf-8")
    (dest / "AxiomCheck.lean").write_text(
        f"import Submission\n\n#print axioms Submission.{problem.theorem_name}\n", encoding="utf-8",
    )

"""Lake workspace contents for sandbox verification.

The sandbox writes these files into the worker container (no host filesystem cache);
the bash verify script seeds ``.lake`` from the pre-baked stub on cold runs.
"""

from __future__ import annotations

import hashlib

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


def workspace_files(problem: Problem, submission_lean: str) -> dict[str, str]:
    """Filename → content for one verify workspace. ``.lake`` is seeded by the verify script."""
    return {
        "Challenge.lean": problem.challenge_source(),
        "Solution.lean": problem.solution_source(),
        "Submission.lean": submission_lean,
        "lean-toolchain": problem.lean_toolchain.strip() + "\n",
        "lakefile.toml": _LAKEFILE.format(rev=problem.mathlib_rev),
        "AxiomCheck.lean": (
            f"import Submission\n\n#print axioms Submission.{problem.theorem_name}\n"
        ),
    }

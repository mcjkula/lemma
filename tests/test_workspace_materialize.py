"""Lake workspace files + template cache key."""

from lemma.lean.workspace import (
    workspace_files,
    workspace_template_cache_key,
    workspace_verify_cache_key,
)
from lemma.problems.base import Problem


def _minimal_problem() -> Problem:
    return Problem(
        id="gen/test_k",
        theorem_name="t_test",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        imports=("Mathlib",),
    )


def test_workspace_template_cache_key_stable() -> None:
    p = _minimal_problem()
    assert workspace_template_cache_key(p) == workspace_template_cache_key(p)


def test_workspace_verify_cache_key_matches_template_when_no_fingerprint() -> None:
    p = _minimal_problem()
    assert workspace_verify_cache_key(p, "namespace Submission\n", include_submission_fingerprint=False) == (
        workspace_template_cache_key(p)
    )


def test_workspace_verify_cache_key_splits_on_proof_when_enabled() -> None:
    p = _minimal_problem()
    a = workspace_verify_cache_key(p, "a", include_submission_fingerprint=True)
    b = workspace_verify_cache_key(p, "b", include_submission_fingerprint=True)
    assert a != b
    assert a.startswith(workspace_template_cache_key(p))
    assert "_" in a


def test_workspace_files_includes_required_sources() -> None:
    p = _minimal_problem()
    files = workspace_files(p, "namespace Submission\nend Submission\n")
    assert set(files.keys()) == {
        "Challenge.lean", "Submission.lean",
        "lean-toolchain", "lakefile.toml", "AxiomCheck.lean",
    }
    assert files["Submission.lean"].startswith("namespace Submission")
    assert "Submission.t_test" in files["AxiomCheck.lean"]
    assert "LemmaSubmissionBridge" in files["AxiomCheck.lean"]
    assert files["lean-toolchain"].strip() == p.lean_toolchain
    assert p.mathlib_rev in files["lakefile.toml"]

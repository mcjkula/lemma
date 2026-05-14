"""verified_solves runs Lean verify and α-rename dedups duplicates."""

from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import VerifyResult
from lemma.problems.base import Problem
from lemma.protocol import RevealPayload
from lemma.validator import verify as verify_mod
from lemma.validator.verify import verified_solves


def _problem(tid: str) -> Problem:
    return Problem(
        id=tid, theorem_name=tid, type_expr="True",
        split="medium", lean_toolchain="leanprover/lean4:v4.30.0", mathlib_rev="abc",
    )


def _reveal(tid: str, proof: str) -> RevealPayload:
    return RevealPayload(theorem_id=tid, metronome_id="1", proof_script=proof)


def _verify_returning(result: VerifyResult):
    def stub(_settings, *, verify_timeout_s, problem, proof_script) -> VerifyResult:  # noqa: ARG001
        return result
    return stub


_ok = _verify_returning(VerifyResult(passed=True, reason="ok"))
_compile_error = _verify_returning(VerifyResult(passed=False, reason="compile_error"))
_timeout = _verify_returning(VerifyResult(passed=False, reason="timeout"))


def test_single_valid_solve_lands_in_solved(monkeypatch) -> None:
    monkeypatch.setattr(verify_mod, "run_lean_verify", _ok)
    problems = {"t": _problem("t")}
    replies = {"t": {1: _reveal("t", "by trivial")}}
    solved, proofs = verified_solves(LemmaSettings(), problems, replies)
    assert solved == {"t": {1}}
    assert proofs == {"t": {1: "by trivial"}}


def test_duplicate_fingerprint_drops_second_submission(monkeypatch) -> None:
    """Same byte-identical proof from a second miner is dropped by fingerprint dedup."""
    monkeypatch.setattr(verify_mod, "run_lean_verify", _ok)
    problems = {"t": _problem("t")}
    replies = {"t": {1: _reveal("t", "by trivial"), 2: _reveal("t", "by trivial")}}
    solved, proofs = verified_solves(LemmaSettings(), problems, replies)
    assert solved == {"t": {1}}
    assert 2 not in proofs["t"]


def test_alpha_rename_collapses_variable_renames(monkeypatch) -> None:
    """Proofs differing only in bound-variable names collide on fingerprint."""
    monkeypatch.setattr(verify_mod, "run_lean_verify", _ok)
    problems = {"t": _problem("t")}
    replies = {
        "t": {
            1: _reveal("t", "by intro x; exact x"),
            2: _reveal("t", "by intro y; exact y"),
        },
    }
    solved, _ = verified_solves(LemmaSettings(), problems, replies)
    assert solved["t"] == {1}


def test_compile_error_drops_solve(monkeypatch) -> None:
    monkeypatch.setattr(verify_mod, "run_lean_verify", _compile_error)
    problems = {"t": _problem("t")}
    replies = {"t": {1: _reveal("t", "by sorry")}}
    solved, proofs = verified_solves(LemmaSettings(), problems, replies)
    assert solved == {"t": set()}
    assert proofs == {"t": {}}


def test_timeout_does_not_count_as_solve(monkeypatch) -> None:
    monkeypatch.setattr(verify_mod, "run_lean_verify", _timeout)
    problems = {"t": _problem("t")}
    replies = {"t": {1: _reveal("t", "by ...")}}
    solved, _ = verified_solves(LemmaSettings(), problems, replies)
    assert solved == {"t": set()}


def test_two_distinct_proofs_both_kept(monkeypatch) -> None:
    monkeypatch.setattr(verify_mod, "run_lean_verify", _ok)
    problems = {"t": _problem("t")}
    replies = {
        "t": {
            1: _reveal("t", "by trivial"),
            2: _reveal("t", "by exact True.intro"),
        },
    }
    solved, proofs = verified_solves(LemmaSettings(), problems, replies)
    assert solved["t"] == {1, 2}
    assert set(proofs["t"]) == {1, 2}


def test_invalid_proof_does_not_block_identical_retry_from_other_miner(monkeypatch) -> None:
    """First miner submits a proof that fails verify. A second miner submits the SAME proof.

    The second submission gets re-verified (fingerprint dedup only records *passing*
    fingerprints) but also fails. Both are excluded.
    """
    monkeypatch.setattr(verify_mod, "run_lean_verify", _compile_error)
    problems = {"t": _problem("t")}
    replies = {"t": {1: _reveal("t", "bad"), 2: _reveal("t", "bad")}}
    solved, _ = verified_solves(LemmaSettings(), problems, replies)
    assert solved["t"] == set()

"""Baseline triviality filter dispatches to LeanSandbox."""

from dataclasses import dataclass
from typing import Any

from lemma.problems.base import Problem
from lemma.supply.baseline_filter import is_trivial


def _problem() -> Problem:
    return Problem(
        id="x",
        theorem_name="t",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0",
        mathlib_rev="abc",
    )


@dataclass
class _VerifyOutcome:
    passed: bool
    reason: str = "ok"
    stderr_tail: str = ""
    stdout_tail: str = ""
    proof_metrics: Any = None


def test_triviality_passes_when_baseline_succeeds(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_run(_settings, *, verify_timeout_s, problem, proof_script):
        captured["proof"] = proof_script
        captured["timeout"] = verify_timeout_s
        return _VerifyOutcome(passed=True)

    import lemma.supply.baseline_filter as mod

    monkeypatch.setattr(mod, "run_lean_verify", fake_run)
    assert is_trivial(_settings_stub(), _problem()) is True
    assert "first |" in captured["proof"]
    assert "decide" in captured["proof"]


def test_triviality_fails_when_baseline_fails(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        return _VerifyOutcome(passed=False, reason="compile_error")

    import lemma.supply.baseline_filter as mod

    monkeypatch.setattr(mod, "run_lean_verify", fake_run)
    assert is_trivial(_settings_stub(), _problem()) is False


def _settings_stub() -> Any:
    @dataclass
    class _S:
        lean_verify_timeout_s: int = 30

    return _S()

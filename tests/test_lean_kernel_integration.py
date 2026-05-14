"""End-to-end integration test against a real Lean kernel in Docker.

This is the only test that proves the Lean sandbox actually accepts and rejects
real proofs — every other validator test mocks ``_verify``. It is opt-in: skipped
unless explicitly enabled via ``LEMMA_LEAN_INTEGRATION=1`` and a running worker
container is reachable.

Required environment (mirrors how a real validator runs):

  LEMMA_LEAN_INTEGRATION=1
  LEMMA_USE_DOCKER=true                # required by validator startup
  LEMMA_LEAN_DOCKER_WORKER=<container>  # docker ps -f name=<container>

Setup recipe (one-time):

  docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
  docker volume create lemma-lean-cache
  docker run -d --name lean-worker \\
      -v lemma-lean-cache:/lemma-workspace \\
      lemma/lean-sandbox:latest sleep infinity
  LEMMA_LEAN_INTEGRATION=1 \\
  LEMMA_USE_DOCKER=true \\
  LEMMA_LEAN_DOCKER_WORKER=lean-worker \\
      uv run pytest tests/test_lean_kernel_integration.py -v
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from lemma.common.config import LemmaSettings
from lemma.lean import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem


def _enabled() -> bool:
    return os.environ.get("LEMMA_LEAN_INTEGRATION", "").strip().lower() in ("1", "true", "yes")


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "info"], check=True, capture_output=True, timeout=5,
        )
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def _worker_running(name: str) -> bool:
    if not name:
        return False
    try:
        r = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name=^{name}$"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        return bool(r.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        return False


WORKER = os.environ.get("LEMMA_LEAN_DOCKER_WORKER", "").strip()

_SKIP_REASON = (
    "Lean kernel integration test — set LEMMA_LEAN_INTEGRATION=1 and run a "
    "lemma/lean-sandbox worker container (see module docstring)."
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _enabled(), reason=_SKIP_REASON),
    pytest.mark.skipif(not _docker_available(), reason="docker daemon not reachable"),
    pytest.mark.skipif(
        not _worker_running(WORKER),
        reason=f"worker container {WORKER!r} not running — `docker ps -f name={WORKER}` is empty",
    ),
]


def _settings() -> LemmaSettings:
    return LemmaSettings().model_copy(update={
        "lean_use_docker": True,
        "lemma_lean_docker_worker": WORKER,
        "lean_verify_timeout_s": 3600,
    })


def _problem() -> Problem:
    # A self-contained truth: True is provable without Mathlib lemmas.
    return Problem(
        id="integration-trivial",
        theorem_name="integration_trivial",
        type_expr="True",
        split="medium",
        lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
        mathlib_rev=DEFAULT_MATHLIB_REV,
    )


def test_lean_kernel_accepts_valid_proof() -> None:
    """A trivial proof of ``True`` against the real Lean kernel passes verify."""
    submission = (
        "import Mathlib\n"
        "\n"
        "namespace Submission\n"
        "\n"
        "theorem integration_trivial : True := True.intro\n"
        "\n"
        "end Submission\n"
    )
    result = run_lean_verify(
        _settings(), verify_timeout_s=3600, problem=_problem(), proof_script=submission,
    )
    assert result.passed, (
        f"Expected pass; got reason={result.reason}\n"
        f"stderr_tail={result.stderr_tail[-2000:]}\n"
        f"stdout_tail={result.stdout_tail[-2000:]}"
    )
    assert result.reason == "ok"
    assert result.build_seconds > 0.0


def test_lean_kernel_rejects_malformed_proof() -> None:
    """A submission that doesn't close the goal fails with compile_error."""
    submission = (
        "import Mathlib\n"
        "\n"
        "namespace Submission\n"
        "\n"
        "theorem integration_trivial : True := by\n"
        "  bogus_tactic\n"
        "\n"
        "end Submission\n"
    )
    result = run_lean_verify(
        _settings(), verify_timeout_s=3600, problem=_problem(), proof_script=submission,
    )
    assert not result.passed
    assert result.reason in {"compile_error", "axiom_violation", "cheat_token"}


def test_lean_kernel_rejects_sorry() -> None:
    """``sorry`` is never a valid proof for Lemma — must be caught at verify."""
    submission = (
        "import Mathlib\n"
        "\n"
        "namespace Submission\n"
        "\n"
        "theorem integration_trivial : True := by sorry\n"
        "\n"
        "end Submission\n"
    )
    result = run_lean_verify(
        _settings(), verify_timeout_s=3600, problem=_problem(), proof_script=submission,
    )
    assert not result.passed
    # ``sorry`` introduces ``sorryAx`` outside the allowed-axiom set; the scanner
    # may classify it as a cheat token (literal "sorry") or an axiom violation.
    assert result.reason in {"cheat_token", "axiom_violation", "compile_error"}

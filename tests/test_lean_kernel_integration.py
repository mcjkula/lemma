"""End-to-end integration test against a real Lean kernel in Docker.

Setup recipe (one-time):

  docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
  docker volume create lemma-lean-cache
  docker run -d --name lemma-lean-worker \\
      -v lemma-lean-cache:/lemma-workspace \\
      lemma/lean-sandbox:latest sleep infinity
  echo "LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker" >> .env
  uv run pytest tests/test_lean_kernel_integration.py -v

The test skips only when Docker or the worker container is unreachable.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest
from lemma.common.config import LemmaSettings
from lemma.lean import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
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


WORKER = LemmaSettings().lemma_lean_docker_worker


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _docker_available(), reason="docker daemon not reachable"),
    pytest.mark.skipif(
        not _worker_running(WORKER),
        reason=f"worker container {WORKER!r} not running",
    ),
]


def _settings() -> LemmaSettings:
    return LemmaSettings().model_copy(update={
        "lemma_lean_docker_worker": WORKER,
        "lean_verify_timeout_s": 3600,
    })


def _problem() -> Problem:
    return Problem(
        id="integration-trivial",
        theorem_name="integration_trivial",
        type_expr="True",
        split="medium",
        lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
        mathlib_rev=DEFAULT_MATHLIB_REV,
    )


def _run(submission: str):
    return run_lean_verify(
        _settings(), verify_timeout_s=3600, problem=_problem(), proof_script=submission,
    )


def test_lean_kernel_accepts_valid_proof() -> None:
    result = _run(
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        "theorem integration_trivial : True := True.intro\n\n"
        "end Submission\n",
    )
    assert result.passed, (
        f"Expected pass; got reason={result.reason}\n"
        f"stderr_tail={result.stderr_tail[-2000:]}\n"
        f"stdout_tail={result.stdout_tail[-2000:]}"
    )
    assert result.reason == "ok"
    assert result.build_seconds > 0.0


def test_lean_kernel_rejects_malformed_proof() -> None:
    result = _run(
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        "theorem integration_trivial : True := by\n  bogus_tactic\n\n"
        "end Submission\n",
    )
    assert not result.passed
    assert result.reason in {"compile_error", "axiom_violation", "cheat_token"}


def test_lean_kernel_rejects_sorry() -> None:
    result = _run(
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        "theorem integration_trivial : True := by sorry\n\n"
        "end Submission\n",
    )
    assert not result.passed
    assert result.reason in {"cheat_token", "axiom_violation", "compile_error"}

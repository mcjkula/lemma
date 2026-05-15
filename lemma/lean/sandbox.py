"""Run Lean verification via ``docker exec`` into a worker container."""

from __future__ import annotations

import io
import shlex
import subprocess
import tarfile
import time
import uuid
from dataclasses import dataclass
from typing import Literal

from lemma.lean.cheats import (
    axiom_scan_ok,
    cheat_scan_stderr_tail,
    lake_build_environment_failed,
    lean_driver_failed,
    scan_submission_for_cheats,
)
from lemma.lean.workspace import workspace_files, workspace_verify_cache_key
from lemma.problems.base import Problem

_MOUNT = "/lemma-workspace"

_VERIFY_BASH = (
    "set -e; "
    "[ -d .lake ] || cp -a /opt/lemma-stub/.lake /opt/lemma-stub/lake-manifest.json .; "
    "lake build"
)

_PRUNE_BASH = r"""
set -euo pipefail
cd /lemma-workspace
find . -maxdepth 1 -mindepth 1 -type d -name '.tmp-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true
max_dirs="${1:-0}" max_bytes="${2:-0}" protect="${3:-}"
mapfile -t slots < <(find . -maxdepth 1 -mindepth 1 -type d ! -name '.tmp-*' -printf '%T@\t%f\n' \
  | sort -n | awk -v p="$protect" '$2 != p {print $2}')
count=${#slots[@]}; i=0
while [ "$max_dirs" -gt 0 ] && [ "$count" -ge "$max_dirs" ] && [ "$i" -lt "${#slots[@]}" ]; do
  rm -rf "${slots[$i]}"; count=$((count-1)); i=$((i+1))
done
while [ "$max_bytes" -gt 0 ] && [ "$i" -lt "${#slots[@]}" ]; do
  total=$(du -sb . | awk '{print $1}')
  [ "$total" -le "$max_bytes" ] && break
  rm -rf "${slots[$i]}"; i=$((i+1))
done
"""

VerifyReason = Literal[
    "ok", "compile_error", "axiom_violation", "cheat_token", "timeout", "oom", "docker_error",
]
_PUBLISHABLE: frozenset[VerifyReason] = frozenset({"ok", "compile_error", "axiom_violation", "cheat_token"})


@dataclass(frozen=True, slots=True)
class VerifyResult:
    passed: bool
    reason: VerifyReason
    stderr_tail: str = ""
    stdout_tail: str = ""
    build_seconds: float = 0.0


def _build_tar(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class LeanSandbox:
    def __init__(
        self,
        *,
        docker_worker: str,
        timeout_s: int = 600,
        workspace_cache_include_submission_hash: bool = False,
        workspace_cache_max_dirs: int = 8,
        workspace_cache_max_bytes: int = 16 * 1024 * 1024 * 1024,
    ) -> None:
        self.docker_worker = docker_worker
        self.timeout_s = timeout_s
        self.include_submission_hash = workspace_cache_include_submission_hash
        self.max_dirs = workspace_cache_max_dirs
        self.max_bytes = workspace_cache_max_bytes

    def verify(self, problem: Problem, submission_src: str) -> VerifyResult:
        cheat = scan_submission_for_cheats(submission_src)
        if not cheat.ok:
            return VerifyResult(passed=False, reason="cheat_token",
                                stderr_tail=cheat_scan_stderr_tail(cheat))

        files = workspace_files(problem, submission_src)
        cache_key = workspace_verify_cache_key(
            problem, submission_src, include_submission_fingerprint=self.include_submission_hash,
        )
        slot = f"{_MOUNT}/{cache_key}"

        if self._slot_warm(slot):
            self._write(slot, files)
            return self._run(slot)

        tmp = f"{_MOUNT}/.tmp-{uuid.uuid4().hex}"
        self._write(tmp, files)
        vr = self._run(tmp)
        if vr.reason in _PUBLISHABLE:
            self._sh(
                f"if [ ! -e {shlex.quote(slot)} ]; then mv {shlex.quote(tmp)} {shlex.quote(slot)}; "
                f"else rm -rf {shlex.quote(tmp)}; fi",
            )
            self._prune(cache_key)
            return vr
        self._sh(f"rm -rf {shlex.quote(tmp)}", check=False)
        return vr

    def _sh(self, bash: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "exec", self.docker_worker, "bash", "-c", bash],
            capture_output=True, text=True, check=check,
        )

    def _slot_warm(self, slot: str) -> bool:
        return self._sh(f"test -d {shlex.quote(slot)}/.lake/packages/mathlib", check=False).returncode == 0

    def _write(self, dest: str, files: dict[str, str]) -> None:
        subprocess.run(
            ["docker", "exec", "-i", self.docker_worker, "bash", "-c",
             f"mkdir -p {shlex.quote(dest)} && tar x -C {shlex.quote(dest)}"],
            input=_build_tar(files), capture_output=True, check=True,
        )

    def _prune(self, protect: str) -> None:
        if self.max_dirs <= 0 and self.max_bytes <= 0:
            return
        subprocess.run(
            ["docker", "exec", self.docker_worker, "bash", "-c", _PRUNE_BASH, "_",
             str(self.max_dirs), str(self.max_bytes), protect],
            capture_output=True, check=False,
        )

    def _run(self, workdir: str) -> VerifyResult:
        t0 = time.monotonic()
        try:
            r = subprocess.run(
                ["docker", "exec", "--workdir", workdir, self.docker_worker, "bash", "-c", _VERIFY_BASH],
                capture_output=True, text=True, timeout=float(self.timeout_s),
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(passed=False, reason="timeout", stderr_tail="docker exec timed out",
                                build_seconds=time.monotonic() - t0)
        return _parse(r.stderr + "\n" + r.stdout, r.returncode, time.monotonic() - t0)


def _parse(text: str, exit_status: int, elapsed: float) -> VerifyResult:
    text = text[-64_000:]
    tail = text[-16_000:]
    if exit_status == 137:
        return VerifyResult(passed=False, reason="oom", stderr_tail=tail, build_seconds=elapsed)
    if lake_build_environment_failed(text):
        return VerifyResult(passed=False, reason="compile_error", stderr_tail=tail, build_seconds=elapsed)
    ok, found = axiom_scan_ok(text)
    if exit_status != 0:
        if ok or found is None or lean_driver_failed(text):
            return VerifyResult(passed=False, reason="compile_error", stderr_tail=tail, build_seconds=elapsed)
        return VerifyResult(passed=False, reason="axiom_violation",
                            stderr_tail=tail + f" axioms={found}", build_seconds=elapsed)
    if ok:
        return VerifyResult(passed=True, reason="ok", stdout_tail=text[-2000:], build_seconds=elapsed)
    if found is None or lean_driver_failed(text):
        return VerifyResult(passed=False, reason="compile_error",
                            stderr_tail=tail + (f" axioms={found}" if found else ""),
                            build_seconds=elapsed)
    return VerifyResult(passed=False, reason="axiom_violation",
                        stdout_tail=text[-4000:] + f" axioms={found}", build_seconds=elapsed)

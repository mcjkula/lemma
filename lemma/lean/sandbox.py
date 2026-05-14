"""Run Lean verification via ``docker exec`` into a long-lived worker container.

The worker mounts a Docker named volume at ``/lemma-workspace`` for its cache; the
validator never touches the host filesystem for proof scripts or build artifacts.
"""

from __future__ import annotations

import io
import os
import shlex
import subprocess
import tarfile
import threading
import time
import uuid
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel

from lemma.lean.cheats import (
    axiom_scan_ok,
    cheat_scan_stderr_tail,
    lake_build_environment_failed,
    lean_driver_failed,
    scan_submission_for_cheats,
)
from lemma.lean.workspace import workspace_files, workspace_verify_cache_key
from lemma.problems.base import Problem

_VERIFY_SCRIPT = ".lemma_verify.sh"
_DEFAULT_MOUNT = "/lemma-workspace"


@lru_cache(maxsize=512)
def _slot_lock(cache_key: str) -> threading.RLock:  # noqa: ARG001
    return threading.RLock()


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _lean_num_threads_value() -> str:
    raw = os.environ.get("LEMMA_LEAN_NUM_THREADS", "").strip()
    return raw or str(min(64, max(1, os.cpu_count() or 8)))


def _lake_build_argv() -> list[str]:
    return ["lake", "build"] if _env_truthy("LEMMA_LEAN_VERIFY_FULL_BUILD") else ["lake", "build", "Submission"]


VerifyReason = Literal[
    "ok", "compile_error", "axiom_violation", "cheat_token",
    "timeout", "oom", "docker_error", "remote_error",
]


class VerifyResult(BaseModel):
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


def _verify_script_source() -> str:
    always_cache_get = "1" if _env_truthy("LEMMA_LEAN_ALWAYS_CACHE_GET") else ""
    lines = [
        f"export LEAN_NUM_THREADS={shlex.quote(_lean_num_threads_value())}",
        "set -euo pipefail",
        "git config --global --add safe.directory '*' >/dev/null 2>&1 || true",
        "if [ -d /opt/lemma-stub ] && [ ! -d .lake ]; then",
        "  cp -a /opt/lemma-stub/.lake . 2>/dev/null || true",
        "  cp -a /opt/lemma-stub/lake-manifest.json . 2>/dev/null || true",
        "fi",
        f"if [ ! -d .lake/packages/mathlib ] || [ -n {shlex.quote(always_cache_get)} ]; then",
        "  lake exe cache get",
        "fi",
        shlex.join(_lake_build_argv()),
        "lake env lean AxiomCheck.lean",
    ]
    return "\n".join(lines) + "\n"


_PRUNE_SCRIPT = r"""
set -euo pipefail
cd "${1:-/lemma-workspace}"
max_dirs="${2:-0}"
max_bytes="${3:-0}"
protect="${4:-}"
# Drop stale tempdirs older than 24h.
find . -maxdepth 1 -mindepth 1 -type d -name '.tmp-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true
# Build mtime-sorted list of slots (oldest first), excluding tempdirs and the protected slot.
mapfile -t slots < <(find . -maxdepth 1 -mindepth 1 -type d ! -name '.tmp-*' -printf '%T@\t%f\n' \
  | sort -n | awk -v p="$protect" '$2 != p {print $2}')
count="${#slots[@]}"
i=0
if [ "$max_dirs" -gt 0 ]; then
  while [ "$count" -ge "$max_dirs" ] && [ "$i" -lt "${#slots[@]}" ]; do
    rm -rf "${slots[$i]}"; count=$((count-1)); i=$((i+1))
  done
fi
if [ "$max_bytes" -gt 0 ]; then
  total=$(du -sb . 2>/dev/null | awk '{print $1}')
  while [ "${total:-0}" -gt "$max_bytes" ] && [ "$i" -lt "${#slots[@]}" ]; do
    rm -rf "${slots[$i]}"; i=$((i+1))
    total=$(du -sb . 2>/dev/null | awk '{print $1}')
  done
fi
"""


class LeanSandbox:
    def __init__(
        self,
        *,
        docker_worker: str,
        timeout_s: int = 600,
        workspace_cache_enabled: bool = True,
        workspace_cache_include_submission_hash: bool = False,
        workspace_cache_max_dirs: int = 8,
        workspace_cache_max_bytes: int = 16 * 1024 * 1024 * 1024,
    ) -> None:
        self.docker_worker = docker_worker.strip()
        self.timeout_s = timeout_s
        self.workspace_cache_enabled = workspace_cache_enabled
        self.workspace_cache_include_submission_hash = workspace_cache_include_submission_hash
        self.workspace_cache_max_dirs = workspace_cache_max_dirs
        self.workspace_cache_max_bytes = workspace_cache_max_bytes
        self.mount_point = os.environ.get("LEMMA_LEAN_DOCKER_WORKER_MOUNT", _DEFAULT_MOUNT) or _DEFAULT_MOUNT

    def verify(self, problem: Problem, submission_src: str) -> VerifyResult:
        if not self.docker_worker:
            return VerifyResult(
                passed=False, reason="docker_error",
                stderr_tail="LEMMA_LEAN_DOCKER_WORKER is required",
            )
        cheat = scan_submission_for_cheats(submission_src)
        if not cheat.ok:
            return VerifyResult(
                passed=False, reason="cheat_token",
                stderr_tail=cheat_scan_stderr_tail(cheat),
            )

        files = workspace_files(problem, submission_src)
        files[_VERIFY_SCRIPT] = _verify_script_source()

        if not self.workspace_cache_enabled:
            tmp = f"{self.mount_point}/.tmp-{uuid.uuid4().hex}"
            try:
                self._reset_dir(tmp)
                self._write_files(tmp, files)
                return self._run_verify(tmp)
            finally:
                self._exec(["rm", "-rf", tmp], check=False)

        cache_key = workspace_verify_cache_key(
            problem, submission_src,
            include_submission_fingerprint=self.workspace_cache_include_submission_hash,
        )
        slot = f"{self.mount_point}/{cache_key}"
        with _slot_lock(cache_key):
            self._prune(protect=cache_key)
            if self._slot_warm(slot):
                self._write_files(slot, files)
                return self._run_verify(slot)
            tmp = f"{self.mount_point}/.tmp-{uuid.uuid4().hex}"
            self._reset_dir(tmp)
            self._write_files(tmp, files)
            vr = self._run_verify(tmp)
            if self._publishable(vr):
                self._publish(tmp, slot)
                self._prune(protect=cache_key)
            else:
                self._exec(["rm", "-rf", tmp], check=False)
            return vr

    def _exec(
        self, argv: list[str], *, check: bool = True, stdin: bytes | None = None,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        cmd = ["docker", "exec"]
        if stdin is not None:
            cmd.append("-i")
        cmd += [self.docker_worker, *argv]
        return subprocess.run(
            cmd, input=stdin, capture_output=True, text=stdin is None,
            check=check, timeout=timeout_s,
        )

    def _slot_warm(self, slot: str) -> bool:
        r = self._exec(["test", "-d", f"{slot}/.lake/packages/mathlib"], check=False)
        return r.returncode == 0

    def _reset_dir(self, path: str) -> None:
        self._exec(["bash", "-c", f"rm -rf {shlex.quote(path)} && mkdir -p {shlex.quote(path)}"])

    def _write_files(self, dest: str, files: dict[str, str]) -> None:
        self._exec(["mkdir", "-p", dest])
        self._exec(["tar", "x", "-C", dest], stdin=_build_tar(files))

    def _publish(self, tmp: str, slot: str) -> None:
        # Race-safe: if another worker already published this slot, drop the tempdir.
        script = (
            f"if [ ! -e {shlex.quote(slot)} ]; then "
            f"mv {shlex.quote(tmp)} {shlex.quote(slot)}; "
            f"else rm -rf {shlex.quote(tmp)}; fi"
        )
        self._exec(["bash", "-c", script], check=False)

    def _publishable(self, result: VerifyResult) -> bool:
        return result.reason not in {"timeout", "oom", "docker_error", "remote_error"}

    def _prune(self, *, protect: str) -> None:
        if self.workspace_cache_max_dirs <= 0 and self.workspace_cache_max_bytes <= 0:
            return
        self._exec(
            [
                "bash", "-c", _PRUNE_SCRIPT, "_",
                self.mount_point,
                str(self.workspace_cache_max_dirs),
                str(self.workspace_cache_max_bytes),
                protect,
            ],
            check=False,
        )

    def _run_verify(self, workdir: str) -> VerifyResult:
        t0 = time.monotonic()
        try:
            r = subprocess.run(
                ["docker", "exec", "--workdir", workdir, self.docker_worker,
                 "bash", _VERIFY_SCRIPT],
                capture_output=True, text=True, timeout=float(self.timeout_s),
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(
                passed=False, reason="timeout",
                stderr_tail="docker exec timed out",
                build_seconds=time.monotonic() - t0,
            )
        elapsed = time.monotonic() - t0
        text = ((r.stderr or "") + "\n" + (r.stdout or ""))[-64_000:]
        return _parse_logs(text, r.returncode if r.returncode is not None else -1, elapsed)


def _parse_logs(text: str, exit_status: int, elapsed: float) -> VerifyResult:
    tail = 16_000
    if exit_status != 0:
        if exit_status == 137:
            return VerifyResult(passed=False, reason="oom", stderr_tail=text[-tail:], build_seconds=elapsed)
        if lake_build_environment_failed(text):
            return VerifyResult(passed=False, reason="compile_error", stderr_tail=text[-tail:], build_seconds=elapsed)
        ok_ax, found_ax = axiom_scan_ok(text)
        if ok_ax:
            return VerifyResult(passed=False, reason="compile_error", stderr_tail=text[-tail:], build_seconds=elapsed)
        if found_ax is None or lean_driver_failed(text):
            return VerifyResult(passed=False, reason="compile_error", stderr_tail=text[-tail:], build_seconds=elapsed)
        return VerifyResult(passed=False, reason="axiom_violation",
                            stderr_tail=text[-tail:] + f" axioms={found_ax}", build_seconds=elapsed)
    if lake_build_environment_failed(text):
        return VerifyResult(passed=False, reason="compile_error", stderr_tail=text[-tail:], build_seconds=elapsed)
    ok, found = axiom_scan_ok(text)
    if ok:
        return VerifyResult(passed=True, reason="ok", stdout_tail=text[-2000:], build_seconds=elapsed)
    extra = f" axioms={found}" if found else ""
    if found is None or lean_driver_failed(text):
        return VerifyResult(passed=False, reason="compile_error",
                            stderr_tail=text[-tail:] + extra, build_seconds=elapsed)
    return VerifyResult(passed=False, reason="axiom_violation",
                        stdout_tail=text[-4000:] + extra, build_seconds=elapsed)

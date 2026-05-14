"""Run Lean verification via ``docker exec`` into a long-lived worker container."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import BaseModel

from lemma.lean.cheats import (
    axiom_scan_ok,
    cheat_scan_stderr_tail,
    lake_build_environment_failed,
    lean_driver_failed,
    scan_submission_for_cheats,
)
from lemma.lean.workspace import materialize_workspace, workspace_verify_cache_key
from lemma.problems.base import Problem

_VERIFY_SCRIPT = ".lemma_verify.sh"


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


def lake_exe_cache_get_needed(work: Path) -> bool:
    if _env_truthy("LEMMA_LEAN_ALWAYS_CACHE_GET"):
        return True
    return not (work / ".lake" / "packages" / "mathlib").is_dir()


def docker_worker_container_path(work: Path, host_root: Path, mount_point: Path) -> str:
    rel = work.resolve().relative_to(host_root.resolve())
    return str((mount_point / rel).as_posix())


def _dir_size_bytes(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


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


class LeanSandbox:
    def __init__(
        self,
        *,
        docker_worker: str,
        timeout_s: int = 600,
        workspace_cache_dir: Path | None = None,
        workspace_cache_include_submission_hash: bool = False,
        workspace_cache_max_dirs: int = 8,
        workspace_cache_max_bytes: int = 16 * 1024 * 1024 * 1024,
    ) -> None:
        self.docker_worker = docker_worker.strip()
        self.timeout_s = timeout_s
        self.workspace_cache_dir = workspace_cache_dir
        self.workspace_cache_include_submission_hash = workspace_cache_include_submission_hash
        self.workspace_cache_max_dirs = workspace_cache_max_dirs
        self.workspace_cache_max_bytes = workspace_cache_max_bytes

    def verify(self, problem: Problem, submission_src: str) -> VerifyResult:
        if not self.docker_worker:
            return VerifyResult(passed=False, reason="docker_error", stderr_tail="LEMMA_LEAN_DOCKER_WORKER is required")
        cheat = scan_submission_for_cheats(submission_src)
        if not cheat.ok:
            return VerifyResult(passed=False, reason="cheat_token", stderr_tail=cheat_scan_stderr_tail(cheat))

        if self.workspace_cache_dir is None:
            work = Path(tempfile.mkdtemp(prefix="lemma-lean-"))
            try:
                materialize_workspace(work, problem, submission_src, preserve_lake=False)
                return self._verify_via_worker(work)
            finally:
                shutil.rmtree(work, ignore_errors=True)

        self.workspace_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = workspace_verify_cache_key(
            problem, submission_src,
            include_submission_fingerprint=self.workspace_cache_include_submission_hash,
        )
        slot = self.workspace_cache_dir / cache_key
        with _slot_lock(cache_key):
            self._prune_workspace_cache(protect_name=cache_key)
            if slot.is_dir() and (slot / ".lake").is_dir():
                materialize_workspace(slot, problem, submission_src, preserve_lake=True)
                return self._verify_via_worker(slot)
            work = Path(tempfile.mkdtemp(prefix="lemma-lean-", dir=str(self.workspace_cache_dir)))
            try:
                materialize_workspace(work, problem, submission_src, preserve_lake=False)
                vr = self._verify_via_worker(work)
                if self._workspace_cache_publishable(work, vr):
                    self._publish_workspace_cache(slot, work, cache_key)
                    self._prune_workspace_cache(protect_name=cache_key)
                return vr
            finally:
                shutil.rmtree(work, ignore_errors=True)

    def _workspace_cache_publishable(self, work: Path, result: VerifyResult) -> bool:
        if self.workspace_cache_dir is None or not (work / ".lake" / "packages" / "mathlib").is_dir():
            return False
        return result.reason not in {"timeout", "oom", "docker_error", "remote_error"}

    def _publish_workspace_cache(self, slot: Path, work: Path, key: str) -> None:
        if not (work / ".lake").is_dir():
            return
        with _slot_lock(key):
            if slot.exists():
                return
            try:
                work.rename(slot)
            except OSError as e:
                logger.warning("workspace cache publish failed: {}", e)

    def _prune_workspace_cache(self, *, protect_name: str) -> None:
        root = self.workspace_cache_dir
        if root is None or (self.workspace_cache_max_dirs <= 0 and self.workspace_cache_max_bytes <= 0):
            return
        now = time.time()
        warm: list[tuple[float, str, Path, int]] = []
        stale: list[Path] = []
        try:
            entries = [p for p in root.iterdir() if p.is_dir()]
        except OSError:
            return
        for p in entries:
            try:
                st = p.stat()
            except OSError:
                continue
            if p.name.startswith("lemma-lean-"):
                if now - st.st_mtime > 86_400:
                    stale.append(p)
                continue
            warm.append((st.st_mtime, p.name, p, _dir_size_bytes(p)))
        warm.sort()
        to_delete: list[Path] = []
        if self.workspace_cache_max_dirs > 0:
            extra = max(0, len(warm) - self.workspace_cache_max_dirs)
            to_delete += [p for _, name, p, _ in warm if name != protect_name][:extra]
        if self.workspace_cache_max_bytes > 0:
            picked = {p.name for p in to_delete}
            total = sum(s for _, _, _, s in warm)
            for _, name, p, size in warm:
                if total <= self.workspace_cache_max_bytes:
                    break
                if name == protect_name or name in picked:
                    continue
                to_delete.append(p)
                picked.add(name)
                total -= size
        for p in [*to_delete, *stale]:
            shutil.rmtree(p, ignore_errors=True)

    def _verify_script_source(self, work: Path) -> str:
        lines = [
            f"export LEAN_NUM_THREADS={shlex.quote(_lean_num_threads_value())}",
            "set -euo pipefail",
            "if [ -d /opt/lemma-stub ] && [ ! -d .lake ]; then",
            "  cp -a /opt/lemma-stub/.lake . 2>/dev/null || true",
            "fi",
        ]
        if lake_exe_cache_get_needed(work):
            lines.append("lake exe cache get")
        lines.append(shlex.join(_lake_build_argv()))
        lines.append("lake env lean AxiomCheck.lean")
        return "\n".join(lines) + "\n"

    def _worker_host_root(self) -> Path | None:
        raw = os.environ.get("LEMMA_LEAN_DOCKER_WORKER_HOST_ROOT", "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
        return self.workspace_cache_dir.resolve() if self.workspace_cache_dir else None

    def _verify_via_worker(self, work: Path) -> VerifyResult:
        host_root = self._worker_host_root()
        if host_root is None:
            return VerifyResult(passed=False, reason="docker_error",
                                stderr_tail="LEMMA_LEAN_DOCKER_WORKER_HOST_ROOT or workspace cache dir is required")
        mount_point = Path(os.environ.get("LEMMA_LEAN_DOCKER_WORKER_MOUNT", "/lemma-workspace") or "/lemma-workspace")
        try:
            cdir = docker_worker_container_path(work, host_root, mount_point)
        except ValueError:
            return VerifyResult(passed=False, reason="docker_error",
                                stderr_tail=f"workspace {work} is not under {host_root}")
        (work / _VERIFY_SCRIPT).write_text(self._verify_script_source(work), encoding="utf-8")
        t0 = time.monotonic()
        try:
            r = subprocess.run(
                ["docker", "exec", "--workdir", cdir, self.docker_worker, "bash", _VERIFY_SCRIPT],
                capture_output=True, text=True, timeout=float(self.timeout_s),
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(passed=False, reason="timeout",
                                stderr_tail="docker exec timed out", build_seconds=time.monotonic() - t0)
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

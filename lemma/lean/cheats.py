"""Heuristic scans for disallowed tokens in miner-owned Lean source."""

from __future__ import annotations

import re
from dataclasses import dataclass

_FORBIDDEN = re.compile(r"\b(sorry|admit|native_decide|unsafe|unsafeCast|reduceBool)\b", re.IGNORECASE)
_AXIOM_DECL = re.compile(r"^\s*axiom\s+\w+", re.MULTILINE)

ALLOWED_AXIOMS = frozenset({"propext", "Quot.sound", "Classical.choice"})


@dataclass(frozen=True, slots=True)
class CheatScan:
    ok: bool
    reason: str = ""


def scan_submission_for_cheats(source: str) -> CheatScan:
    if _FORBIDDEN.search(source):
        return CheatScan(False, "forbidden_token")
    if _AXIOM_DECL.search(source):
        return CheatScan(False, "user_axiom")
    return CheatScan(True)


_CHEAT_HINTS = {
    "forbidden_token": " — remove `sorry`, `admit`, `unsafe`, … from Submission.lean (completed proof only).",
    "user_axiom": " — do not declare new `axiom`s in Submission.lean.",
}


def cheat_scan_stderr_tail(scan: CheatScan, *, max_len: int = 8000) -> str:
    if scan.ok:
        return ""
    return (scan.reason + _CHEAT_HINTS.get(scan.reason, ""))[:max_len]


def parse_axioms_from_lean_output(text: str) -> set[str] | None:
    if "does not depend on any axioms" in text.lower():
        return set()
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return {p.strip().strip("`") for p in m.group(1).split(",") if p.strip()}


def lean_driver_failed(lean_output: str) -> bool:
    t = lean_output.lower()
    return any(s in t for s in (
        "error (", "unknown identifier", "unknown constant", "invalid field",
        "error:", "build failed", "failed to build",
    ))


def lake_build_environment_failed(lean_output: str) -> bool:
    """Lake/git failed for network or tooling — distinguish from a rejected proof."""
    t = lean_output.lower()
    if any(s in t for s in (
        "could not resolve host", "couldn't resolve host", "network is unreachable",
        "failed to download", "tls handshake",
    )):
        return True
    return "git" in t and "exit code 128" in t


def axiom_scan_ok(lean_output: str) -> tuple[bool, set[str] | None]:
    found = parse_axioms_from_lean_output(lean_output)
    if found is None:
        return False, None
    return found.issubset(ALLOWED_AXIOMS), found

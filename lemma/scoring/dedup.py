"""Proof fingerprints (α-renamed normalised hash of theorem + proof)."""

from __future__ import annotations

import hashlib
import re

_IDENT = r"[a-zA-Z_][a-zA-Z0-9_']*"
_BINDER_PATTERNS = (
    re.compile(rf"\bintro\s+((?:{_IDENT}\s*)+)"),
    re.compile(rf"\bintros\s+((?:{_IDENT}\s*)+)"),
    re.compile(rf"\bfun\s+((?:{_IDENT}\s*)+?)\s*(?:=>|↦)"),
    re.compile(rf"\bλ\s+((?:{_IDENT}\s*)+?)\s*(?:=>|↦|,)"),
    re.compile(rf"\blet\s+({_IDENT})\b"),
    re.compile(rf"\bobtain\s+⟨([^⟩]+)⟩"),
    re.compile(rf"\brcases\s+\S+\s+with\s+([^\n]+)"),
    re.compile(rf"\(\s*({_IDENT}(?:\s+{_IDENT})*)\s*:\s*[^)]+\)"),
)


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _strip_lean_comments(src: str) -> str:
    out = src or ""
    while "/-" in out:
        new = re.sub(r"/-[\s\S]*?-/", "", out, count=1)
        if new == out:
            break
        out = new
    out = re.sub(r"--[^\n]*", "", out)
    return "\n".join(line for line in out.splitlines() if line.strip())


def _collect_binders(src: str) -> list[str]:
    seen: list[str] = []
    seen_set: set[str] = set()
    for pat in _BINDER_PATTERNS:
        for m in pat.finditer(src):
            for name in re.findall(_IDENT, m.group(1)):
                if name not in seen_set:
                    seen.append(name)
                    seen_set.add(name)
    return seen


def alpha_rename_proof(proof_script: str) -> str:
    """Rename bound variables to ``_v0, _v1, …`` in first-appearance order."""
    body = _strip_lean_comments(proof_script)
    names = _collect_binders(body)
    for i, name in enumerate(names):
        body = re.sub(rf"\b{re.escape(name)}\b", f"_v{i}", body)
    return body


def submission_fingerprint(theorem_statement: str, proof_script: str) -> str:
    parts = (
        _collapse_ws(theorem_statement),
        _collapse_ws(alpha_rename_proof(proof_script)),
    )
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()

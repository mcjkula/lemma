"""Proof fingerprints (α-renamed normalised hash of theorem + proof)."""

from __future__ import annotations

import hashlib
import re

_IDENT = r"[a-zA-Z_][a-zA-Z0-9_']*"
_BINDER_PATTERNS = tuple(re.compile(p) for p in (
    rf"\bintro(?:s)?\s+((?:{_IDENT}\s*)+)",
    rf"\b(?:fun|λ)\s+((?:{_IDENT}\s*)+?)\s*(?:=>|↦|,)",
    rf"\blet\s+({_IDENT})\b",
    r"\bobtain\s+⟨([^⟩]+)⟩",
    r"\brcases\s+\S+\s+with\s+([^\n]+)",
    rf"\(\s*({_IDENT}(?:\s+{_IDENT})*)\s*:\s*[^)]+\)",
))


def _strip_lean_comments(src: str) -> str:
    out = src
    while "/-" in out:
        new = re.sub(r"/-[\s\S]*?-/", "", out, count=1)
        if new == out:
            break
        out = new
    out = re.sub(r"--[^\n]*", "", out)
    return "\n".join(line for line in out.splitlines() if line.strip())


def alpha_rename_proof(proof_script: str) -> str:
    body = _strip_lean_comments(proof_script)
    seen: list[str] = []
    for pat in _BINDER_PATTERNS:
        for m in pat.finditer(body):
            for name in re.findall(_IDENT, m.group(1)):
                if name not in seen:
                    seen.append(name)
    for i, name in enumerate(seen):
        body = re.sub(rf"\b{re.escape(name)}\b", f"_v{i}", body)
    return body


def submission_fingerprint(theorem_statement: str, proof_script: str) -> str:
    norm_theorem = re.sub(r"\s+", " ", theorem_statement.strip())
    norm_proof = re.sub(r"\s+", " ", alpha_rename_proof(proof_script).strip())
    return hashlib.sha256(norm_theorem.encode("utf-8") + b"\x1e" + norm_proof.encode("utf-8") + b"\x1e").hexdigest()

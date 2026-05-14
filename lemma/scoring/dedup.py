"""Proof fingerprints (normalised hash of theorem + proof)."""

from __future__ import annotations

import hashlib
import re


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


def submission_fingerprint(theorem_statement: str, proof_script: str) -> str:
    parts = (
        _collapse_ws(theorem_statement),
        _collapse_ws(_strip_lean_comments(proof_script)),
    )
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()

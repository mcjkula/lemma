"""Open `sorry` declarations crawled from a local Mathlib checkout."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from lemma.problems.base import Problem

_SORRY_RX = re.compile(
    r"^(theorem|lemma)\s+([A-Za-z_][\w'.]*)\s*([^:=]*?):\s*(.+?)\s*:=\s*by\s+sorry",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class _SorryHit:
    file_path: Path
    theorem_name: str
    type_expr: str


def _scan_file(path: Path) -> list[_SorryHit]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    out: list[_SorryHit] = []
    for match in _SORRY_RX.finditer(text):
        name = match.group(2).strip()
        type_expr = re.sub(r"\s+", " ", match.group(4)).strip()
        if not type_expr:
            continue
        out.append(_SorryHit(file_path=path, theorem_name=name, type_expr=type_expr))
    return out


def _crawl(root: Path) -> list[_SorryHit]:
    if not root.is_dir():
        return []
    hits: list[_SorryHit] = []
    for path in sorted(root.rglob("*.lean")):
        hits.extend(_scan_file(path))
    return hits


def _problem_id(hit: _SorryHit, root: Path) -> str:
    try:
        rel = hit.file_path.relative_to(root)
    except ValueError:
        rel = hit.file_path
    digest = hashlib.sha256(f"{rel}/{hit.theorem_name}".encode()).hexdigest()[:16]
    return f"sorry/{digest}"


class MathlibSorrysSource:
    name = "mathlib_sorrys"

    def __init__(self, root: Path, *, lean_toolchain: str, mathlib_rev: str) -> None:
        self._root = root
        self._toolchain = lean_toolchain
        self._rev = mathlib_rev
        self._hits: list[_SorryHit] = []
        self._scanned = False

    def _ensure_scan(self) -> None:
        if self._scanned:
            return
        self._hits = _crawl(self._root)
        self._scanned = True

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:
        self._ensure_scan()
        if not self._hits:
            return []
        import random

        rng = random.Random(hashlib.sha256(rng_seed + str(epoch_id).encode()).digest())
        n = min(count, len(self._hits))
        chosen = rng.sample(self._hits, n)
        return [
            Problem(
                id=_problem_id(hit, self._root),
                theorem_name=hit.theorem_name,
                type_expr=hit.type_expr,
                split="hard",
                lean_toolchain=self._toolchain,
                mathlib_rev=self._rev,
                imports=("Mathlib",),
                extra={
                    "source": "mathlib_sorrys",
                    "mathlib_file": str(hit.file_path.relative_to(self._root)),
                },
            )
            for hit in chosen
        ]

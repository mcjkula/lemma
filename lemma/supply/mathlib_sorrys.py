"""Open ``sorry`` declarations crawled from a local Mathlib checkout."""

from __future__ import annotations

import hashlib
import random
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
        type_expr = re.sub(r"\s+", " ", match.group(4)).strip()
        if type_expr:
            out.append(_SorryHit(file_path=path, theorem_name=match.group(2).strip(), type_expr=type_expr))
    return out


def _crawl(root: Path) -> list[_SorryHit]:
    if not root.is_dir():
        return []
    return [hit for path in sorted(root.rglob("*.lean")) for hit in _scan_file(path)]


class MathlibSorrysSource:
    name = "mathlib_sorrys"

    def __init__(self, root: Path, *, lean_toolchain: str, mathlib_rev: str) -> None:
        self._root = root
        self._toolchain = lean_toolchain
        self._rev = mathlib_rev
        self._hits: list[_SorryHit] | None = None

    def _ensure(self) -> list[_SorryHit]:
        if self._hits is None:
            self._hits = _crawl(self._root)
        return self._hits

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:
        hits = self._ensure()
        if not hits:
            return []
        rng = random.Random(hashlib.sha256(rng_seed + str(epoch_id).encode()).digest())
        chosen = rng.sample(hits, min(count, len(hits)))
        out: list[Problem] = []
        for hit in chosen:
            try:
                rel = hit.file_path.relative_to(self._root)
            except ValueError:
                rel = hit.file_path
            digest = hashlib.sha256(f"{rel}/{hit.theorem_name}".encode()).hexdigest()[:16]
            out.append(Problem(
                id=f"sorry/{digest}",
                theorem_name=hit.theorem_name,
                type_expr=hit.type_expr,
                split="hard",
                lean_toolchain=self._toolchain,
                mathlib_rev=self._rev,
                extra={"source": "mathlib_sorrys", "mathlib_file": str(rel)},
            ))
        return out

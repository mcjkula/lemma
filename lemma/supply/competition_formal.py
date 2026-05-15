"""Autoformalised competition statements loaded from JSONL."""

from __future__ import annotations

import hashlib
import json
import random
from functools import cached_property
from pathlib import Path

from lemma.problems.base import Problem


def _load(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


class CompetitionFormalSource:
    name = "competition_formal"

    def __init__(self, jsonl_path: Path, *, lean_toolchain: str, mathlib_rev: str) -> None:
        self._path = jsonl_path
        self._toolchain = lean_toolchain
        self._rev = mathlib_rev

    @cached_property
    def _rows(self) -> list[dict[str, object]]:
        return _load(self._path)

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:
        rows = self._rows
        if not rows:
            return []
        rng = random.Random(hashlib.sha256(rng_seed + str(epoch_id).encode()).digest())
        chosen = rng.sample(rows, min(count, len(rows)))
        out: list[Problem] = []
        for row in chosen:
            type_expr = str(row.get("type_expr", "")).strip()
            theorem_name = str(row.get("theorem_name", "")).strip()
            if not type_expr or not theorem_name:
                continue
            imports_field = row.get("imports")
            if isinstance(imports_field, list):
                imports = tuple(imports_field)
            else:
                imports = ("Mathlib",)
            split = str(row.get("split", "hard")).strip()
            if not split:
                split = "hard"
            origin = row.get("origin", "")
            digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]
            out.append(Problem(
                id=f"competition/{digest}",
                theorem_name=theorem_name,
                type_expr=type_expr,
                split=split,
                lean_toolchain=self._toolchain,
                mathlib_rev=self._rev,
                imports=imports,
                extra={"source": "competition_formal", "origin": str(origin)},
            ))
        return out

"""Autoformalised competition statements loaded from JSONL."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from lemma.problems.base import Problem


def _load(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _problem_id(row: dict[str, object]) -> str:
    raw = json.dumps(row, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"competition/{digest}"


class CompetitionFormalSource:
    name = "competition_formal"

    def __init__(self, jsonl_path: Path, *, lean_toolchain: str, mathlib_rev: str) -> None:
        self._path = jsonl_path
        self._toolchain = lean_toolchain
        self._rev = mathlib_rev
        self._rows: list[dict[str, object]] | None = None

    def _ensure(self) -> list[dict[str, object]]:
        if self._rows is None:
            self._rows = _load(self._path)
        return self._rows

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:
        rows = self._ensure()
        if not rows:
            return []
        rng = random.Random(hashlib.sha256(rng_seed + str(epoch_id).encode()).digest())
        n = min(count, len(rows))
        chosen = rng.sample(rows, n)
        out: list[Problem] = []
        for row in chosen:
            type_expr = str(row.get("type_expr", "")).strip()
            theorem_name = str(row.get("theorem_name", "")).strip()
            if not type_expr or not theorem_name:
                continue
            split = str(row.get("split", "hard")).strip() or "hard"
            imports_raw = row.get("imports")
            imports = tuple(imports_raw) if isinstance(imports_raw, list) else ("Mathlib",)
            out.append(
                Problem(
                    id=_problem_id(row),
                    theorem_name=theorem_name,
                    type_expr=type_expr,
                    split=split,
                    lean_toolchain=self._toolchain,
                    mathlib_rev=self._rev,
                    imports=imports,
                    extra={
                        "source": "competition_formal",
                        "origin": str(row.get("origin") or ""),
                    },
                ),
            )
        return out

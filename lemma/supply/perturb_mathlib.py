"""Perturbed-Mathlib supply: read ``data/mathlib_seeds.jsonl`` and parameterise per epoch."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from lemma.problems.base import Problem

_DEFAULT_SEEDS = Path(__file__).resolve().parent.parent.parent / "data" / "mathlib_seeds.jsonl"


@dataclass(frozen=True, slots=True)
class _Seed:
    id: str
    family: str
    split: str
    type_expr: str
    imports: tuple[str, ...]
    params: dict[str, Any]


@lru_cache(maxsize=4)
def _load_seeds(path: str) -> tuple[_Seed, ...]:
    p = Path(path)
    if not p.is_file():
        return ()
    out: list[_Seed] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        out.append(_Seed(
            id=row["id"],
            family=row["family"],
            split=row.get("split", "easy"),
            type_expr=row["type_expr"],
            imports=tuple(row.get("imports", ("Mathlib",))),
            params=dict(row.get("params", {})),
        ))
    return tuple(out)


def _draw_param(rng: random.Random, spec: dict[str, Any]) -> str:
    kind = spec.get("kind")
    if kind == "ident":
        return rng.choice(spec.get("pool") or ["x"])
    return str(rng.randint(int(spec.get("lo", 2)), int(spec.get("hi", 97))))


def _render(seed: _Seed, rng: random.Random) -> str:
    return seed.type_expr.format(**{name: _draw_param(rng, spec) for name, spec in seed.params.items()})


class PerturbedMathlibSource:
    name = "perturb_mathlib"

    def __init__(self, lean_toolchain: str, mathlib_rev: str, seeds_path: Path | None = None) -> None:
        self._toolchain = lean_toolchain
        self._rev = mathlib_rev
        self._seeds_path = str((seeds_path or _DEFAULT_SEEDS).resolve())

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:
        seeds = _load_seeds(self._seeds_path)
        if not seeds:
            return []
        rng = random.Random(hashlib.sha256(rng_seed + str(epoch_id).encode()).digest())
        out: list[Problem] = []
        for i in range(max(0, count)):
            seed = rng.choice(seeds)
            digest = hashlib.sha256(f"{seed.id}/{epoch_id}/{i}".encode()).hexdigest()[:12]
            out.append(Problem(
                id=f"perturb/{epoch_id}/{i}",
                theorem_name=f"perturb_{seed.family}_{digest}",
                type_expr=_render(seed, rng),
                split=seed.split,
                lean_toolchain=self._toolchain,
                mathlib_rev=self._rev,
                imports=seed.imports,
                extra={"source": "perturb_mathlib", "family": seed.family, "seed_id": seed.id},
            ))
        return out

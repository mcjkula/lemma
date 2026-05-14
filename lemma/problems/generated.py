"""Last-resort degraded-fallback theorem generator.

Used only when Streams P/M/C collapse (every candidate baseline-rejected or
freshness-blocked) and ``LEMMA_SUPPLY_FALLBACK_GENERATED=true``. Emits a loud
warning on every draw — this is *not* an intended production source.
"""

from __future__ import annotations

import hashlib
import random

from loguru import logger

from lemma.lean import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.problems.base import Problem


def _name(epoch_id: int, idx: int) -> str:
    return f"fallback_{hashlib.sha256(f'{epoch_id}/{idx}'.encode()).hexdigest()[:12]}"


def _draw_one(rng: random.Random, epoch_id: int, idx: int) -> Problem:
    a, b = rng.randint(2, 97), rng.randint(2, 97)
    return Problem(
        id=f"fallback/{epoch_id}/{idx}",
        theorem_name=_name(epoch_id, idx),
        type_expr=f"({a} : Nat) + {b} = {b} + {a}",
        split="easy",
        lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
        mathlib_rev=DEFAULT_MATHLIB_REV,
        imports=("Mathlib",),
        extra={"source": "fallback_generated"},
    )


class FallbackGeneratedSource:
    name = "fallback_generated"

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:
        logger.warning(
            "LEMMA_SUPPLY_FALLBACK_GENERATED active — emitting degraded fallback theorems "
            "(this is a kill-switch, not a production source).",
        )
        rng = random.Random(hashlib.sha256(rng_seed + str(epoch_id).encode()).digest())
        return [_draw_one(rng, epoch_id, i) for i in range(max(0, int(count)))]

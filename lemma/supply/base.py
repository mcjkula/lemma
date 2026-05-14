"""Theorem supply contract."""

from __future__ import annotations

from typing import Protocol

from lemma.problems.base import Problem


class Source(Protocol):
    name: str

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]: ...

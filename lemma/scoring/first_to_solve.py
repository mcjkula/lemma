"""First-to-solve ranking with registration-block tie-break."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Solve:
    miner_uid: int
    theorem_id: str
    commit_block: int


def rank_solvers(
    solves: Iterable[Solve],
    registration_block: dict[int, int],
) -> dict[tuple[str, int], int]:
    """Return ``{(theorem_id, miner_uid): rank}`` with rank 0 for the earliest commit.

    Ties on ``commit_block`` break by the earlier ``registration_block`` of the miner's hotkey
    (Affine SN120 incumbency); ties on registration break by lower UID.
    """
    by_theorem: dict[str, list[Solve]] = {}
    for s in solves:
        by_theorem.setdefault(s.theorem_id, []).append(s)

    ranks: dict[tuple[str, int], int] = {}
    for theorem_id, group in by_theorem.items():
        ordered = sorted(
            group,
            key=lambda s: (
                s.commit_block,
                registration_block.get(s.miner_uid, 1 << 31),
                s.miner_uid,
            ),
        )
        for i, s in enumerate(ordered):
            ranks[(theorem_id, s.miner_uid)] = i
    return ranks

"""_registration_blocks maps each UID to its registration block from the metagraph."""

from dataclasses import dataclass, field

import numpy as np

from lemma.validator.epoch import _registration_blocks


@dataclass
class _Meta:
    n: np.ndarray = field(default_factory=lambda: np.array([0], dtype=np.int64))
    block_at_registration: list[int] = field(default_factory=list)


def test_returns_dict_of_uid_to_int_block() -> None:
    m = _Meta(n=np.array([3], dtype=np.int64), block_at_registration=[100, 110, 120])
    assert _registration_blocks(m) == {0: 100, 1: 110, 2: 120}


def test_returns_empty_dict_when_metagraph_empty() -> None:
    m = _Meta(n=np.array([0], dtype=np.int64), block_at_registration=[])
    assert _registration_blocks(m) == {}


def test_int_casts_numpy_block_values() -> None:
    # Confirms we hand Python ints to the budget combiner — not numpy scalars,
    # which would interop awkwardly with dict[int, int] downstream.
    m = _Meta(
        n=np.array([2], dtype=np.int64),
        block_at_registration=list(np.array([7, 11], dtype=np.int64)),
    )
    out = _registration_blocks(m)
    assert all(type(v) is int for v in out.values())

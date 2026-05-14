"""Per-epoch supply pipeline draws, filters, freshness-checks, commits."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lemma.problems.base import Problem
from lemma.supply.pipeline import build_batch


class _StubSource:
    def __init__(self, name: str, items: list[Problem]) -> None:
        self.name = name
        self._items = items

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:  # noqa: ARG002
        return self._items[:count]


def _problem(name: str, type_expr: str) -> Problem:
    return Problem(
        id=name,
        theorem_name=name,
        type_expr=type_expr,
        split="medium",
        lean_toolchain="leanprover/lean4:v4.30.0",
        mathlib_rev="abc",
    )


@dataclass
class _Settings:
    lean_verify_timeout_s: int = 30
    lemma_supply_public_corpus_bloom_path: Path | None = None


def test_pipeline_picks_from_streams(tmp_path: Path) -> None:
    streams: dict[str, Any] = {
        "P": _StubSource("P", [_problem(f"p{i}", f"{i} = {i}") for i in range(4)]),
        "M": _StubSource("M", [_problem(f"m{i}", f"True ∧ True_{i}") for i in range(4)]),
        "C": _StubSource("C", [_problem(f"c{i}", f"1 + {i} ≥ 0") for i in range(4)]),
    }
    batch = build_batch(
        _Settings(),
        streams,
        epoch_id=1,
        target_count=6,
        freshness_path=tmp_path / "seen.txt",
        skip_baseline_filter=True,
    )
    assert len(batch.problems) >= 1
    assert batch.commitment.epoch_id == 1
    assert len(batch.commitment.root_hex) == 64


def test_freshness_blocks_repeats(tmp_path: Path) -> None:
    streams: dict[str, Any] = {"P": _StubSource("P", [_problem("p", "True")])}
    fresh = tmp_path / "seen.txt"
    first = build_batch(
        _Settings(), streams, epoch_id=1, target_count=1,
        freshness_path=fresh, ratios=(("P", 1.0),), skip_baseline_filter=True,
    )
    again = build_batch(
        _Settings(), streams, epoch_id=2, target_count=1,
        freshness_path=fresh, ratios=(("P", 1.0),), skip_baseline_filter=True,
    )
    assert len(first.problems) == 1
    assert len(again.problems) == 0


def test_baseline_filter_drops_trivial(tmp_path: Path, monkeypatch) -> None:
    streams: dict[str, Any] = {
        "P": _StubSource("P", [_problem("p", "True"), _problem("q", "1 + 1 = 2")]),
    }
    import lemma.supply.pipeline as mod

    monkeypatch.setattr(mod, "is_trivial", lambda _settings, problem: problem.theorem_name == "p")
    batch = build_batch(
        _Settings(),
        streams,
        epoch_id=3,
        target_count=2,
        freshness_path=tmp_path / "f.txt",
        ratios=(("P", 1.0),),
    )
    names = [p.theorem_name for p in batch.problems]
    assert "p" not in names
    assert "q" in names

"""Freshness registry roundtrip."""

from pathlib import Path

from lemma.supply.freshness import FreshnessRegistry, statement_hash


def test_normalization_strips_comments_and_whitespace() -> None:
    a = statement_hash("theorem t : 1 + 1 = 2 := by /- note -/ trivial")
    b = statement_hash("theorem t : 1 + 1 = 2  :=  by trivial")
    assert a == b


def test_record_then_reject(tmp_path: Path) -> None:
    reg = FreshnessRegistry(tmp_path / "seen.txt")
    assert reg.is_fresh("theorem t : True := by trivial")
    reg.record("theorem t : True := by trivial")
    assert not reg.is_fresh("theorem t : True := by trivial")


def test_persists_across_instances(tmp_path: Path) -> None:
    store = tmp_path / "seen.txt"
    r1 = FreshnessRegistry(store)
    r1.record("foo")
    r2 = FreshnessRegistry(store)
    assert not r2.is_fresh("foo")

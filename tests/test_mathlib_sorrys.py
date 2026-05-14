"""Mathlib sorry source crawls a checkout and emits Problems."""

from pathlib import Path

from lemma.supply.mathlib_sorrys import MathlibSorrysSource


def _write(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _source(root: Path) -> MathlibSorrysSource:
    return MathlibSorrysSource(root, lean_toolchain="leanprover/lean4:v4.30.0", mathlib_rev="abc")


def test_finds_sorry_in_lemma_file(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "Mathlib/Foo.lean",
        "theorem open_goal (n : Nat) : n + 0 = n := by sorry\n",
    )
    out = _source(tmp_path).draw(epoch_id=1, count=4, rng_seed=b"x")
    assert len(out) == 1
    p = out[0]
    assert p.theorem_name == "open_goal"
    assert "n + 0 = n" in p.type_expr
    assert p.extra["source"] == "mathlib_sorrys"


def test_missing_root_returns_empty(tmp_path: Path) -> None:
    out = _source(tmp_path / "nope").draw(epoch_id=1, count=4, rng_seed=b"x")
    assert out == []


def test_deterministic_per_seed(tmp_path: Path) -> None:
    for i in range(5):
        _write(tmp_path, f"Mathlib/F{i}.lean", f"theorem t{i} : True := by sorry\n")
    a = _source(tmp_path).draw(epoch_id=1, count=3, rng_seed=b"seed")
    b = _source(tmp_path).draw(epoch_id=1, count=3, rng_seed=b"seed")
    assert [p.id for p in a] == [p.id for p in b]

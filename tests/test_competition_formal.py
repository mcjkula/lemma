"""Competition autoformalised supply loader."""

import json
from pathlib import Path

from lemma.supply.competition_formal import CompetitionFormalSource


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _source(path: Path) -> CompetitionFormalSource:
    return CompetitionFormalSource(path, lean_toolchain="leanprover/lean4:v4.30.0", mathlib_rev="abc")


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    out = _source(tmp_path / "missing.jsonl").draw(epoch_id=1, count=4, rng_seed=b"x")
    assert out == []


def test_loads_and_samples(tmp_path: Path) -> None:
    f = tmp_path / "feed.jsonl"
    _write(
        f,
        [
            {"theorem_name": "thm_a", "type_expr": "True", "split": "extreme"},
            {"theorem_name": "thm_b", "type_expr": "1 + 1 = 2", "split": "hard"},
        ],
    )
    out = _source(f).draw(epoch_id=1, count=2, rng_seed=b"s")
    names = sorted(p.theorem_name for p in out)
    assert names == ["thm_a", "thm_b"]
    assert all(p.extra["source"] == "competition_formal" for p in out)


def test_skips_malformed_rows(tmp_path: Path) -> None:
    f = tmp_path / "feed.jsonl"
    _write(
        f,
        [
            {"theorem_name": "ok", "type_expr": "True"},
            {"type_expr": "missing_name"},
            {"theorem_name": "missing_type"},
        ],
    )
    out = _source(f).draw(epoch_id=2, count=3, rng_seed=b"s")
    assert len(out) == 1
    assert out[0].theorem_name == "ok"

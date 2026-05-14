from pathlib import Path

from lemma.scoring.reputation import ReputationStore, load_reputation, save_reputation


def test_reputation_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "rep.json"
    save_reputation(p, ReputationStore(reign_by_uid={1: 3, 7: 11}))
    assert load_reputation(p).reign_by_uid == {1: 3, 7: 11}


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_reputation(tmp_path / "missing.json").reign_by_uid == {}

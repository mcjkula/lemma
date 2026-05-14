"""Public proof corpus writer."""

import json
from pathlib import Path

from lemma.validator.corpus import CorpusEntry, append


def _entry(**overrides: object) -> CorpusEntry:
    base = dict(
        epoch_id=1,
        theorem_id="gen/1",
        theorem_statement="theorem t : True := by sorry",
        proof_script="namespace Submission\n",
        miner_hotkey_ss58="5Fhotkey",
        commit_block=12345,
        mathlib_rev="abc",
        lean_toolchain="leanprover/lean4:v4.30.0",
    )
    base.update(overrides)  # type: ignore[arg-type]
    return CorpusEntry(**base)  # type: ignore[arg-type]


def test_appends_per_epoch_files(tmp_path: Path) -> None:
    append([_entry(epoch_id=10), _entry(epoch_id=10, theorem_id="gen/2")], root=tmp_path)
    files = sorted(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    rows = [json.loads(line) for line in lines]
    assert rows[0]["epoch_id"] == 10


def test_appends_safely_on_reentry(tmp_path: Path) -> None:
    append([_entry(epoch_id=7)], root=tmp_path)
    append([_entry(epoch_id=7, theorem_id="gen/8")], root=tmp_path)
    target = next(tmp_path.glob("*.jsonl"))
    lines = target.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_empty_input_is_noop(tmp_path: Path) -> None:
    append([], root=tmp_path)
    assert list(tmp_path.glob("*.jsonl")) == []

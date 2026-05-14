"""Public proof corpus writer (jsonl per epoch) and S3 publisher."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CorpusEntry:
    epoch_id: int
    theorem_id: str
    theorem_statement: str
    proof_script: str
    miner_hotkey_ss58: str
    commit_block: int
    mathlib_rev: str
    lean_toolchain: str


def default_corpus_dir() -> Path:
    return Path.home() / ".lemma" / "corpus"


def append(entries: list[CorpusEntry], *, root: Path | None = None) -> Path:
    if not entries:
        return (root or default_corpus_dir())
    target_root = root or default_corpus_dir()
    target_root.mkdir(parents=True, exist_ok=True)
    by_epoch: dict[int, list[CorpusEntry]] = {}
    for e in entries:
        by_epoch.setdefault(e.epoch_id, []).append(e)
    for epoch_id, group in by_epoch.items():
        path = target_root / f"{epoch_id:020d}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            for e in group:
                f.write(
                    json.dumps(
                        {
                            "epoch_id": e.epoch_id,
                            "theorem_id": e.theorem_id,
                            "theorem_statement": e.theorem_statement,
                            "proof_script": e.proof_script,
                            "miner_hotkey": e.miner_hotkey_ss58,
                            "commit_block": e.commit_block,
                            "mathlib_rev": e.mathlib_rev,
                            "lean_toolchain": e.lean_toolchain,
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                )
    return target_root


def publish_to_s3(destination: str, *, root: Path | None = None) -> int:
    """Mirror the local corpus directory to ``s3://bucket/prefix`` via ``aws s3 sync``."""
    if not destination.startswith("s3://"):
        raise ValueError(f"destination must be an s3:// URL, got {destination!r}")
    source = root or default_corpus_dir()
    if not source.is_dir():
        return 0
    r = subprocess.run(  # noqa: S603 — operator-supplied destination
        ["aws", "s3", "sync", str(source), destination],
        capture_output=True, text=True, check=False,
    )
    return int(r.returncode)

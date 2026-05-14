"""Per-UID champion-reign state persisted on disk."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReputationStore:
    reign_by_uid: dict[int, int] = field(default_factory=dict)


def _resolve(path: Path | None) -> Path:
    return path or Path.home() / ".lemma" / "validator_reputation.json"


def load_reputation(path: Path | None) -> ReputationStore:
    p = _resolve(path)
    if not p.is_file():
        return ReputationStore()
    data = json.loads(p.read_text(encoding="utf-8"))
    return ReputationStore(
        reign_by_uid={int(k): int(v) for k, v in data.get("reign_by_uid", {}).items()},
    )


def save_reputation(path: Path | None, store: ReputationStore) -> None:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    payload = {"reign_by_uid": {str(k): int(v) for k, v in sorted(store.reign_by_uid.items())}}
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)

"""Per-UID validator scoring state persisted on disk."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ReputationStore:
    rolling_score_by_uid: dict[int, float] = field(default_factory=dict)
    version: int = 4

    def to_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "rolling_score_by_uid": {str(k): v for k, v in sorted(self.rolling_score_by_uid.items())},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ReputationStore:
        ver = int(data.get("version", 3))
        raw = data.get("rolling_score_by_uid") or {}
        rolling: dict[int, float] = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                rolling[int(k)] = _clamp_score(float(v))
        # v2/v3 stored only an EMA map; migrate it to a rolling score.
        if not rolling:
            legacy = data.get("ema_by_uid") or {}
            if isinstance(legacy, dict):
                for k, v in legacy.items():
                    rolling[int(k)] = _clamp_score(float(v))
        return cls(rolling_score_by_uid=rolling, version=max(4, ver))


def default_reputation_path() -> Path:
    return Path.home() / ".lemma" / "validator_reputation.json"


def load_reputation(path: Path | None) -> ReputationStore:
    p = path or default_reputation_path()
    if not p.is_file():
        return ReputationStore()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return ReputationStore()
        return ReputationStore.from_json(data)
    except (OSError, ValueError, json.JSONDecodeError, TypeError, KeyError):
        return ReputationStore()


def save_reputation(path: Path | None, store: ReputationStore) -> None:
    p = path or default_reputation_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(store.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def rolling_effective_alpha(alpha: float, difficulty_weight: float) -> float:
    a = max(0.0, min(1.0, float(alpha)))
    w = max(0.0, float(difficulty_weight))
    if a <= 0.0 or w <= 0.0:
        return 0.0
    eff = 1.0 - ((1.0 - a) ** w)
    return max(0.0, min(1.0, float(eff)))


def apply_rolling_outcomes(
    scores: dict[int, float],
    outcomes: dict[int, bool],
    *,
    alpha: float,
    difficulty_weight: float,
) -> dict[int, float]:
    eff_alpha = rolling_effective_alpha(alpha, difficulty_weight)
    for uid, passed in outcomes.items():
        old = _clamp_score(scores.get(int(uid), 0.0))
        target = 1.0 if passed else 0.0
        scores[int(uid)] = _clamp_score((1.0 - eff_alpha) * old + eff_alpha * target)
    return scores


def rolling_weights(scores: dict[int, float]) -> dict[int, float]:
    raw = {int(uid): _clamp_score(score) for uid, score in scores.items() if _clamp_score(score) > 0.0}
    total = sum(raw.values())
    if total <= 0.0:
        return {}
    return {uid: score / total for uid, score in raw.items()}


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

"""Per-UID validator scoring state persisted on disk."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class ReputationStore:
    rolling_score_by_uid: dict[int, float] = field(default_factory=dict)
    reign_by_uid: dict[int, int] = field(default_factory=dict)


def default_reputation_path() -> Path:
    return Path.home() / ".lemma" / "validator_reputation.json"


def load_reputation(path: Path | None) -> ReputationStore:
    p = path or default_reputation_path()
    if not p.is_file():
        return ReputationStore()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return ReputationStore()
    if not isinstance(data, dict):
        return ReputationStore()
    rolling = {int(k): _clamp_score(float(v)) for k, v in (data.get("rolling_score_by_uid") or {}).items()}
    reign = {int(k): int(v) for k, v in (data.get("reign_by_uid") or {}).items()}
    return ReputationStore(rolling_score_by_uid=rolling, reign_by_uid=reign)


def save_reputation(path: Path | None, store: ReputationStore) -> None:
    p = path or default_reputation_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    payload = {
        "rolling_score_by_uid": {str(k): v for k, v in sorted(store.rolling_score_by_uid.items())},
        "reign_by_uid": {str(k): int(v) for k, v in sorted(store.reign_by_uid.items())},
    }
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def rolling_effective_alpha(alpha: float, difficulty_weight: float) -> float:
    a, w = max(0.0, min(1.0, float(alpha))), max(0.0, float(difficulty_weight))
    if a <= 0.0 or w <= 0.0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - ((1.0 - a) ** w)))


def apply_rolling_outcomes(
    scores: dict[int, float],
    outcomes: dict[int, bool],
    *,
    alpha: float,
    difficulty_weight: float,
) -> dict[int, float]:
    eff = rolling_effective_alpha(alpha, difficulty_weight)
    for uid, passed in outcomes.items():
        old = _clamp_score(scores.get(int(uid), 0.0))
        scores[int(uid)] = _clamp_score((1.0 - eff) * old + eff * (1.0 if passed else 0.0))
    return scores


def rolling_weights(scores: dict[int, float]) -> dict[int, float]:
    raw = {int(uid): _clamp_score(s) for uid, s in scores.items() if _clamp_score(s) > 0.0}
    total = sum(raw.values())
    return {uid: s / total for uid, s in raw.items()} if total > 0.0 else {}

"""Rolling pass/fail scores and validator reputation persistence."""

from pathlib import Path

from lemma.scoring.reputation import (
    ReputationStore,
    apply_rolling_outcomes,
    load_reputation,
    rolling_effective_alpha,
    rolling_weights,
    save_reputation,
)


def test_apply_rolling_outcomes_pass_and_fail() -> None:
    scores = {1: 0.5, 2: 0.5}
    apply_rolling_outcomes(scores, {1: True, 2: False}, alpha=0.1, difficulty_weight=1.0)
    assert abs(scores[1] - 0.55) < 1e-9
    assert abs(scores[2] - 0.45) < 1e-9


def test_difficulty_weight_changes_rolling_impact() -> None:
    easy_alpha = rolling_effective_alpha(0.08, 1.0)
    hard_alpha = rolling_effective_alpha(0.08, 4.0)
    assert hard_alpha > easy_alpha

    easy = {1: 0.0}
    hard = {1: 0.0}
    apply_rolling_outcomes(easy, {1: True}, alpha=0.08, difficulty_weight=1.0)
    apply_rolling_outcomes(hard, {1: True}, alpha=0.08, difficulty_weight=4.0)
    assert hard[1] > easy[1]


def test_rolling_weights_normalize_positive_scores() -> None:
    assert rolling_weights({1: 0.0, 2: 0.25, 3: 0.75}) == {2: 0.25, 3: 0.75}


def test_single_miss_does_not_zero_existing_rolling_score() -> None:
    scores = {1: 0.9}
    apply_rolling_outcomes(scores, {1: False}, alpha=0.1, difficulty_weight=1.0)
    assert 0.0 < scores[1] < 0.9


def test_reputation_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "rep.json"
    save_reputation(p, ReputationStore(rolling_score_by_uid={2: 0.75}))
    loaded = load_reputation(p)
    assert loaded.rolling_score_by_uid == {2: 0.75}


def test_legacy_reputation_state_migrates(tmp_path: Path) -> None:
    p = tmp_path / "rep.json"
    p.write_text('{"version": 2, "ema_by_uid": {"1": 0.4, "2": 1.2}}', encoding="utf-8")
    s = load_reputation(p)
    assert s.rolling_score_by_uid == {1: 0.4, 2: 1.0}

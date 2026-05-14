"""Validator requires Docker for Lean verify."""

import pytest
from lemma.common.config import LemmaSettings
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.hybrid import problem_supply_registry_sha256
from lemma.validator.service import _require_docker_for_validator, validator_startup_issues


def _ready_settings(**updates: object) -> LemmaSettings:
    fields = {
        "lean_use_docker": True,
        "problem_source": "generated",
        "generated_registry_expected_sha256": generated_registry_sha256(),
        **updates,
    }
    return LemmaSettings(_env_file=None, **fields)


def test_validator_requires_docker_by_default() -> None:
    s = LemmaSettings().model_copy(update={"lean_use_docker": False})
    with pytest.raises(SystemExit, match="requires Docker"):
        _require_docker_for_validator(s)


def test_validator_ok_when_docker_on() -> None:
    s = LemmaSettings().model_copy(update={"lean_use_docker": True})
    _require_docker_for_validator(s)


def test_validator_startup_issues_accept_ready_settings() -> None:
    fatal, warn = validator_startup_issues(_ready_settings(), dry_run=False)
    assert fatal == []
    assert warn == []


def test_validator_startup_issues_accept_ready_hybrid_settings() -> None:
    settings = LemmaSettings(
        _env_file=None,
        lean_use_docker=True,
        problem_source="hybrid",
        problem_supply_registry_expected_sha256=problem_supply_registry_sha256(),
    )
    fatal, warn = validator_startup_issues(settings, dry_run=False)
    assert fatal == []
    assert warn == []


def test_validator_startup_issues_match_docker_gate() -> None:
    fatal, _ = validator_startup_issues(_ready_settings(lean_use_docker=False), dry_run=False)
    assert any("requires Docker" in msg for msg in fatal)

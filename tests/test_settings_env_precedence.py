"""LemmaSettings prefers `.env` over process environment (unless LEMMA_PREFER_PROCESS_ENV)."""

from __future__ import annotations

import pytest
from lemma.common.config import LemmaSettings


def test_dotenv_beats_process_env_for_netuid(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("NETUID=11\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NETUID", "99")
    s = LemmaSettings(_env_file=str(env_file))
    assert s.netuid == 11


def test_process_env_beats_dotenv_when_flag(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LEMMA_PREFER_PROCESS_ENV", "1")
    env_file = tmp_path / ".env"
    env_file.write_text("NETUID=11\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NETUID", "99")
    s = LemmaSettings(_env_file=str(env_file))
    assert s.netuid == 99


def test_dotenv_sets_lean_use_docker(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    monkeypatch.delenv("LEMMA_USE_DOCKER", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LEMMA_USE_DOCKER=false\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.lean_use_docker is False


def test_public_ip_discovery_is_opt_in_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AXON_DISCOVER_EXTERNAL_IP", raising=False)
    s = LemmaSettings(_env_file=None)
    assert s.axon_discover_external_ip is False


def test_lean_workspace_cache_has_bounded_default() -> None:
    s = LemmaSettings(_env_file=None)
    assert s.lemma_lean_workspace_cache_max_dirs == 8


def test_lean_workspace_cache_byte_bound_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES=12345\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.lemma_lean_workspace_cache_max_bytes == 12345


def test_explicit_init_kwarg_beats_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NETUID", "99")
    s = LemmaSettings(_env_file=None, netuid=7)
    assert s.netuid == 7


def test_uppercase_alias_is_canonical_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("NETUID=42\nLEMMA_USE_DOCKER=false\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.netuid == 42
    assert s.lean_use_docker is False


def test_validator_wallet_names_returns_pair() -> None:
    s = LemmaSettings(_env_file=None, wallet_cold="c", wallet_hot="h")
    assert s.validator_wallet_names() == ("c", "h")

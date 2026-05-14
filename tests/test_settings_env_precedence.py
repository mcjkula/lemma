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


def test_public_ip_discovery_is_opt_in_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AXON_DISCOVER_EXTERNAL_IP", raising=False)
    s = LemmaSettings(_env_file=None)
    assert s.axon_discover_external_ip is False

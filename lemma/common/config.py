"""Environment-driven settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource


class LemmaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],  # noqa: ARG003
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        if os.environ.get("LEMMA_PREFER_PROCESS_ENV", "").strip().lower() in ("1", "true", "yes"):
            return (init_settings, env_settings, dotenv_settings, file_secret_settings)
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    netuid: int = Field(default=0, ge=0, validation_alias="NETUID")

    problem_seed_quantize_blocks: int = Field(
        default=100, ge=1, le=1_000_000, validation_alias="LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS",
    )
    problem_seed_mode: Literal["quantize", "subnet_epoch"] = Field(
        default="quantize", validation_alias="LEMMA_PROBLEM_SEED_MODE",
    )
    lemma_problem_seed_chain_head_slack_blocks: int = Field(
        default=0, ge=0, le=128, validation_alias="LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS",
    )

    subtensor_network: str = Field(default="finney", validation_alias="SUBTENSOR_NETWORK")
    subtensor_chain_endpoint: str | None = Field(
        default=None, validation_alias="SUBTENSOR_CHAIN_ENDPOINT",
    )
    wallet_cold: str = Field(default="default", validation_alias="BT_WALLET_COLD")
    wallet_hot: str = Field(default="default", validation_alias="BT_WALLET_HOT")
    axon_port: int = Field(default=8091, validation_alias="AXON_PORT")
    axon_external_ip: str | None = Field(default=None, validation_alias="AXON_EXTERNAL_IP")
    axon_discover_external_ip: bool = Field(
        default=False, validation_alias="AXON_DISCOVER_EXTERNAL_IP",
    )

    lean_verify_timeout_s: int = Field(
        default=180, ge=10, le=3600, validation_alias="LEAN_VERIFY_TIMEOUT_S",
    )
    lean_use_docker: bool = Field(default=True, validation_alias="LEMMA_USE_DOCKER")
    lemma_lean_docker_worker: str | None = Field(
        default=None, validation_alias="LEMMA_LEAN_DOCKER_WORKER",
    )
    lemma_lean_verify_max_concurrent: int = Field(
        default=4, ge=1, le=64, validation_alias="LEMMA_LEAN_VERIFY_MAX_CONCURRENT",
    )
    lemma_lean_workspace_cache_enabled: bool = Field(
        default=True, validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_ENABLED",
    )
    lemma_lean_workspace_cache_max_dirs: int = Field(
        default=8, ge=0, le=1_000, validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS",
    )
    lemma_lean_workspace_cache_max_bytes: int = Field(
        default=16 * 1024 * 1024 * 1024, ge=0,
        validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES",
    )
    lemma_lean_workspace_cache_include_submission_hash: bool = Field(
        default=False, validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH",
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    block_time_sec_estimate: float = Field(
        default=12.0, gt=0.0, le=120.0, validation_alias="LEMMA_BLOCK_TIME_SEC_ESTIMATE",
    )
    forward_wait_max_s: float = Field(
        default=240.0, ge=1.0, le=3600.0, validation_alias="LEMMA_FORWARD_WAIT_MAX_S",
    )
    lemma_epoch_problem_count: int = Field(
        default=1, ge=1, le=64, validation_alias="LEMMA_EPOCH_PROBLEM_COUNT",
    )
    lemma_reputation_state_path: Path | None = Field(
        default=None, validation_alias="LEMMA_REPUTATION_STATE_PATH",
    )
    lemma_mathlib_root_path: Path | None = Field(
        default=None, validation_alias="LEMMA_MATHLIB_ROOT_PATH",
    )
    lemma_competition_formal_path: Path | None = Field(
        default=None, validation_alias="LEMMA_COMPETITION_FORMAL_PATH",
    )
    lemma_supply_freshness_path: Path | None = Field(
        default=None, validation_alias="LEMMA_SUPPLY_FRESHNESS_PATH",
    )
    lemma_supply_fallback_generated: bool = Field(
        default=False, validation_alias="LEMMA_SUPPLY_FALLBACK_GENERATED",
    )
    lemma_supply_public_corpus_bloom_path: Path | None = Field(
        default=None, validation_alias="LEMMA_SUPPLY_PUBLIC_CORPUS_BLOOM_PATH",
    )
    lemma_inbound_max_chars: int = Field(
        default=500_000, ge=1024, validation_alias="LEMMA_INBOUND_MAX_CHARS",
    )

    def validator_wallet_names(self) -> tuple[str, str]:
        return (self.wallet_cold, self.wallet_hot)

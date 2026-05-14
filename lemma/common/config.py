"""Environment-driven settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource


def _stripped_or_none(value: str | None) -> str | None:
    s = (value or "").strip()
    return s or None


class LemmaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=False,
    )

    def __init__(self, **data: Any) -> None:
        for name, field in type(self).model_fields.items():
            if name not in data:
                continue
            alias = field.validation_alias
            if isinstance(alias, str):
                data.setdefault(alias, data[name])
                data.pop(name)
                continue
            choices = getattr(alias, "choices", None)
            if choices and isinstance(choices[0], str):
                data.setdefault(choices[0], data[name])
                data.pop(name)
        super().__init__(**data)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        if os.environ.get("LEMMA_PREFER_PROCESS_ENV", "").strip().lower() in ("1", "true", "yes"):
            return (init_settings, env_settings, dotenv_settings, file_secret_settings)
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    netuid: int = Field(default=0, ge=0, validation_alias="NETUID")

    problem_source: Literal["hybrid", "generated"] = Field(
        default="hybrid", validation_alias="LEMMA_PROBLEM_SOURCE",
    )
    lemma_hybrid_generated_weight: int = Field(
        default=60, ge=0, le=10_000, validation_alias="LEMMA_HYBRID_GENERATED_WEIGHT",
    )
    lemma_hybrid_catalog_weight: int = Field(
        default=40, ge=0, le=10_000, validation_alias="LEMMA_HYBRID_CATALOG_WEIGHT",
    )
    problem_seed_quantize_blocks: int = Field(
        default=100, ge=1, le=1_000_000, validation_alias="LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS",
    )
    problem_seed_mode: Literal["quantize", "subnet_epoch"] = Field(
        default="quantize", validation_alias="LEMMA_PROBLEM_SEED_MODE",
    )
    lemma_problem_seed_chain_head_slack_blocks: int = Field(
        default=0, ge=0, le=128, validation_alias="LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS",
    )
    generated_registry_expected_sha256: str | None = Field(
        default=None, validation_alias="LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED",
    )
    problem_supply_registry_expected_sha256: str | None = Field(
        default=None, validation_alias="LEMMA_PROBLEM_SUPPLY_REGISTRY_SHA256_EXPECTED",
    )
    lemma_generated_legacy_plain_rng: bool = Field(
        default=False, validation_alias="LEMMA_GENERATED_LEGACY_PLAIN_RNG",
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
        default=True, validation_alias="AXON_DISCOVER_EXTERNAL_IP",
    )

    lean_sandbox_image: str = Field(
        default="lemma-lean-sandbox:latest", validation_alias="LEMMA_LEAN_SANDBOX_IMAGE",
    )
    lean_verify_timeout_s: int = Field(
        default=180, ge=10, le=3600, validation_alias="LEAN_VERIFY_TIMEOUT_S",
    )
    lean_sandbox_cpu: float = Field(
        default=2.0, gt=0.0, le=64.0, validation_alias="LEAN_SANDBOX_CPU",
    )
    lean_sandbox_mem_mb: int = Field(
        default=4096, ge=512, le=131_072, validation_alias="LEAN_SANDBOX_MEM_MB",
    )
    lean_sandbox_network: str = Field(default="none", validation_alias="LEAN_SANDBOX_NETWORK")
    lean_use_docker: bool = Field(default=False, validation_alias="LEMMA_USE_DOCKER")
    allow_host_lean: bool = Field(default=False, validation_alias="LEMMA_ALLOW_HOST_LEAN")

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", validation_alias="ANTHROPIC_MODEL",
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(
        default="deepseek-ai/DeepSeek-V3.2-TEE", validation_alias="OPENAI_MODEL",
    )
    openai_base_url: str = Field(
        default="https://llm.chutes.ai/v1", validation_alias="OPENAI_BASE_URL",
    )
    prover_provider: str = Field(default="anthropic", validation_alias="PROVER_PROVIDER")
    prover_model: str | None = Field(default=None, validation_alias="PROVER_MODEL")
    prover_max_tokens: int = Field(
        default=32_768, ge=512, le=131_072, validation_alias="LEMMA_PROVER_MAX_TOKENS",
    )
    prover_llm_retry_attempts: int = Field(
        default=4, ge=1, le=32, validation_alias="LEMMA_PROVER_LLM_RETRY_ATTEMPTS",
    )
    prover_temperature: float = Field(
        default=0.2, ge=0.0, le=2.0, validation_alias="PROVER_TEMPERATURE",
    )
    prover_min_proof_script_chars: int = Field(
        default=32, ge=0, le=100_000, validation_alias="LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS",
    )
    prover_openai_base_url: str | None = Field(
        default=None, validation_alias="PROVER_OPENAI_BASE_URL",
    )
    prover_openai_api_key: str | None = Field(
        default=None, validation_alias="PROVER_OPENAI_API_KEY",
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    llm_http_timeout_s: float = Field(
        default=60.0, gt=0.0, le=3600.0, validation_alias="LEMMA_LLM_HTTP_TIMEOUT_S",
    )
    block_time_sec_estimate: float = Field(
        default=12.0, gt=0.0, le=120.0, validation_alias="LEMMA_BLOCK_TIME_SEC_ESTIMATE",
    )
    forward_wait_min_s: float = Field(
        default=5.0, ge=0.0, le=3600.0, validation_alias="LEMMA_FORWARD_WAIT_MIN_S",
    )
    forward_wait_max_s: float = Field(
        default=240.0, ge=1.0, le=3600.0, validation_alias="LEMMA_FORWARD_WAIT_MAX_S",
    )
    miner_reject_past_deadline_block: bool = Field(
        default=True, validation_alias="LEMMA_MINER_REJECT_PAST_DEADLINE_BLOCK",
    )
    timeout_scale_by_split: bool = Field(
        default=False, validation_alias="LEMMA_TIMEOUT_SCALE_BY_SPLIT",
    )
    timeout_split_easy_mult: float = Field(
        default=1.0, gt=0.0, le=10.0, validation_alias="LEMMA_TIMEOUT_SPLIT_EASY_MULT",
    )
    timeout_split_medium_mult: float = Field(
        default=1.0, gt=0.0, le=10.0, validation_alias="LEMMA_TIMEOUT_SPLIT_MEDIUM_MULT",
    )
    timeout_split_hard_mult: float = Field(
        default=1.0, gt=0.0, le=10.0, validation_alias="LEMMA_TIMEOUT_SPLIT_HARD_MULT",
    )
    timeout_split_extreme_mult: float = Field(
        default=1.0, gt=0.0, le=10.0, validation_alias="LEMMA_TIMEOUT_SPLIT_EXTREME_MULT",
    )
    lemma_lean_verify_max_concurrent: int = Field(
        default=4, ge=1, le=64, validation_alias="LEMMA_LEAN_VERIFY_MAX_CONCURRENT",
    )

    lean_verify_workspace_cache_dir: Path | None = Field(
        default=None, validation_alias="LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR",
    )
    lemma_lean_workspace_cache_max_dirs: int = Field(
        default=10, ge=1, le=1_000, validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS",
    )
    lemma_lean_workspace_cache_max_bytes: int = Field(
        default=8 * 1024 * 1024 * 1024,
        ge=0,
        validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES",
    )
    lemma_lean_workspace_cache_include_submission_hash: bool = Field(
        default=False, validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH",
    )
    lemma_lean_proof_metrics_enabled: bool = Field(
        default=False, validation_alias="LEMMA_LEAN_PROOF_METRICS_ENABLED",
    )
    lemma_lean_docker_worker: str | None = Field(
        default=None, validation_alias="LEMMA_LEAN_DOCKER_WORKER",
    )

    set_weights_max_retries: int = Field(
        default=3, ge=1, le=20, validation_alias="SET_WEIGHTS_MAX_RETRIES",
    )
    set_weights_retry_delay_s: float = Field(
        default=2.0, ge=0.1, validation_alias="SET_WEIGHTS_RETRY_DELAY_S",
    )
    empty_epoch_weights_policy: Literal["skip", "uniform"] = Field(
        default="skip", validation_alias="LEMMA_EMPTY_EPOCH_WEIGHTS_POLICY",
    )
    validator_abort_if_not_registered: bool = Field(
        default=True, validation_alias="VALIDATOR_ABORT_IF_NOT_REGISTERED",
    )
    validator_min_free_bytes: int = Field(
        default=2 * 1024 * 1024 * 1024,
        ge=0,
        validation_alias="VALIDATOR_MIN_FREE_BYTES",
    )

    lemma_scoring_rolling_alpha: float = Field(
        default=0.08, gt=0.0, le=1.0, validation_alias="LEMMA_SCORING_ROLLING_ALPHA",
    )
    lemma_scoring_difficulty_easy: float = Field(
        default=1.0, ge=0.0, le=10.0, validation_alias="LEMMA_SCORING_DIFFICULTY_EASY",
    )
    lemma_scoring_difficulty_medium: float = Field(
        default=1.0, ge=0.0, le=10.0, validation_alias="LEMMA_SCORING_DIFFICULTY_MEDIUM",
    )
    lemma_scoring_difficulty_hard: float = Field(
        default=1.0, ge=0.0, le=10.0, validation_alias="LEMMA_SCORING_DIFFICULTY_HARD",
    )
    lemma_scoring_difficulty_extreme: float = Field(
        default=1.0, ge=0.0, le=10.0, validation_alias="LEMMA_SCORING_DIFFICULTY_EXTREME",
    )
    lemma_uid_variant_problems: bool = Field(
        default=False, validation_alias="LEMMA_UID_VARIANT_PROBLEMS",
    )
    lemma_reputation_ema_alpha: float = Field(
        default=0.08, gt=0.0, le=1.0, validation_alias="LEMMA_REPUTATION_EMA_ALPHA",
    )
    lemma_reputation_state_path: Path | None = Field(
        default=None, validation_alias="LEMMA_REPUTATION_STATE_PATH",
    )
    lemma_epoch_problem_count: int = Field(
        default=1, ge=1, le=64, validation_alias="LEMMA_EPOCH_PROBLEM_COUNT",
    )
    lemma_commit_reveal_enabled: bool = Field(
        default=False, validation_alias="LEMMA_COMMIT_REVEAL_ENABLED",
    )
    lemma_supply_pipeline_enabled: bool = Field(
        default=False, validation_alias="LEMMA_SUPPLY_PIPELINE_ENABLED",
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

    miner_min_validator_stake: float = Field(
        default=0.0, ge=0.0, validation_alias="MINER_MIN_VALIDATOR_STAKE",
    )
    miner_metagraph_refresh_s: float = Field(
        default=180.0, ge=10.0, validation_alias="MINER_METAGRAPH_REFRESH_S",
    )
    miner_max_concurrent_forwards: int = Field(
        default=4, ge=1, le=64, validation_alias="MINER_MAX_CONCURRENT_FORWARDS",
    )
    miner_require_validator_permit: bool = Field(
        default=False, validation_alias="MINER_REQUIRE_VALIDATOR_PERMIT",
    )
    miner_priority_by_stake: bool = Field(
        default=False, validation_alias="MINER_PRIORITY_BY_STAKE",
    )
    miner_log_forwards: bool = Field(default=False, validation_alias="MINER_LOG_FORWARDS")
    miner_forward_summary: bool = Field(
        default=False, validation_alias="MINER_FORWARD_SUMMARY",
    )
    miner_forward_timeline: bool = Field(
        default=False, validation_alias="MINER_FORWARD_TIMELINE",
    )
    miner_local_verify: bool = Field(
        default=False, validation_alias="LEMMA_MINER_LOCAL_VERIFY",
    )
    lemma_inbound_max_chars: int = Field(
        default=500_000, ge=1024, validation_alias="LEMMA_INBOUND_MAX_CHARS",
    )

    def prover_openai_base_url_resolved(self) -> str:
        p = (self.prover_openai_base_url or "").strip()
        return p if p else (self.openai_base_url or "").strip()

    def prover_openai_api_key_resolved(self) -> str | None:
        return _stripped_or_none(self.prover_openai_api_key) or _stripped_or_none(self.openai_api_key)

    def validator_wallet_names(self) -> tuple[str, str]:
        return (self.wallet_cold, self.wallet_hot)

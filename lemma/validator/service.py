"""Validator metronome service."""

from __future__ import annotations

import asyncio
import os

import bittensor
from loguru import logger

import lemma.validator.epoch as ep
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.problem_seed import (
    blocks_until_challenge_may_change,
    effective_chain_head_for_problem_seed,
    resolve_problem_seed,
)
from lemma.common.subtensor import get_subtensor

_DOCKER_REQUIRED = "lemma validator requires Docker for Lean verify (LEMMA_USE_DOCKER=true)."


def epoch_sleep_seconds(blocks_until_epoch: int, block_time_sec_estimate: float) -> float:
    bu = int(blocks_until_epoch)
    if bu <= 1:
        return 0.0
    if bu <= 3:
        return 1.0
    return min(12.0, max(1.0, float(bu) * float(block_time_sec_estimate) * 0.25))


def validator_retry_sleep_seconds(exc: BaseException, block_time_sec_estimate: float) -> float:
    msg = str(exc).lower()
    if "429" in msg or "rate limit" in msg or "too many requests" in msg:
        return min(300.0, max(30.0, float(block_time_sec_estimate) * 5.0))
    return 2.0


def validator_problem_window(settings: LemmaSettings, subtensor: bittensor.Subtensor, chain_head_block: int) -> tuple[int, int, str]:
    seed_head = effective_chain_head_for_problem_seed(
        int(chain_head_block), int(settings.lemma_problem_seed_chain_head_slack_blocks or 0),
    )
    seed, tag = resolve_problem_seed(
        chain_head_block=seed_head, netuid=settings.netuid, mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks, subtensor=subtensor,
    )
    blocks, edge = blocks_until_challenge_may_change(
        chain_head_block=seed_head, netuid=settings.netuid, mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks, seed_tag=tag, subtensor=subtensor,
    )
    return int(seed), int(blocks), edge


def validator_startup_issues(settings: LemmaSettings) -> list[str]:
    fatal: list[str] = []
    if not settings.lean_use_docker:
        fatal.append(_DOCKER_REQUIRED)
    if settings.lemma_transport != "http":
        fatal.append(f"LEMMA_TRANSPORT={settings.lemma_transport!r} unsupported — set LEMMA_TRANSPORT=http.")
    if settings.lemma_scoring_mode != "pareto":
        fatal.append(f"LEMMA_SCORING_MODE={settings.lemma_scoring_mode!r} unsupported — set LEMMA_SCORING_MODE=pareto.")
    return fatal


class ValidatorService:
    def __init__(self, settings: LemmaSettings | None = None, dry_run: bool | None = None) -> None:
        self.settings = settings or LemmaSettings()
        self.dry_run = dry_run if dry_run is not None else os.environ.get("LEMMA_DRY_RUN") == "1"

    async def run_forever(self) -> None:
        setup_logging(self.settings.log_level)
        logger.info("Validator running — press Ctrl+C to stop and return to your shell.")
        s = self.settings
        fatal = await asyncio.to_thread(validator_startup_issues, s)
        if fatal:
            raise SystemExit(fatal[0])
        subtensor = get_subtensor(s)
        last_seed: int | None = None
        while True:
            try:
                head = int(subtensor.get_current_block())
                seed, blocks, edge = validator_problem_window(s, subtensor, head)
                if last_seed != seed:
                    await ep.run_epoch(s, dry_run=self.dry_run)
                    last_seed = seed
                    await asyncio.sleep(2)
                    continue
                wait_s = epoch_sleep_seconds(blocks, s.block_time_sec_estimate)
                logger.debug("Waiting {:.0f}s (~{} blocks to {})", wait_s, blocks, edge)
                await asyncio.sleep(wait_s)
            except Exception as e:  # noqa: BLE001
                wait_s = validator_retry_sleep_seconds(e, s.block_time_sec_estimate)
                logger.exception("validator loop retry in {:.0f}s: {}", wait_s, e)
                await asyncio.sleep(wait_s)

    def run_blocking(self) -> None:
        import click

        from lemma.cli.style import finish_cli_output, stylize

        click.echo(stylize("Validator running — press Ctrl+C to stop and return to your shell.",
                           fg="cyan", bold=True), err=True)
        try:
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            click.echo("")
            click.echo(stylize("Validator stopped (Ctrl+C).", fg="yellow", bold=True), err=True)
        finally:
            finish_cli_output()

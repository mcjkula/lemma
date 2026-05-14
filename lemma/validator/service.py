"""Validator metronome service."""

from __future__ import annotations

import asyncio

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


def epoch_sleep_seconds(blocks_until_epoch: int, block_time_sec_estimate: float) -> float:
    if blocks_until_epoch <= 1:
        return 0.0
    if blocks_until_epoch <= 3:
        return 1.0
    return min(12.0, max(1.0, blocks_until_epoch * block_time_sec_estimate * 0.25))


def validator_problem_window(
    settings: LemmaSettings, subtensor: bittensor.Subtensor, chain_head_block: int,
) -> tuple[int, int, str]:
    seed_head = effective_chain_head_for_problem_seed(
        chain_head_block, settings.lemma_problem_seed_chain_head_slack_blocks,
    )
    seed, tag = resolve_problem_seed(
        chain_head_block=seed_head, netuid=settings.netuid, mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks, subtensor=subtensor,
    )
    blocks, edge = blocks_until_challenge_may_change(
        chain_head_block=seed_head, netuid=settings.netuid, mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks, seed_tag=tag, subtensor=subtensor,
    )
    return seed, blocks, edge


class ValidatorService:
    def __init__(self, settings: LemmaSettings, *, dry_run: bool) -> None:
        self.settings = settings
        self.dry_run = dry_run

    async def run_forever(self) -> None:
        setup_logging(self.settings.log_level)
        logger.info("Validator running — press Ctrl+C to stop.")
        s = self.settings
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
                logger.exception("validator loop retry in 2s: {}", e)
                await asyncio.sleep(2)

    def run_blocking(self) -> None:
        import click

        from lemma.cli.style import finish_cli_output, stylize

        click.echo(stylize("Validator running — press Ctrl+C to stop.", fg="cyan", bold=True), err=True)
        try:
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            click.echo(stylize("\nValidator stopped (Ctrl+C).", fg="yellow", bold=True), err=True)
        finally:
            finish_cli_output()

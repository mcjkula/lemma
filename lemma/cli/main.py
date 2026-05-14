"""Lemma CLI: doctor, miner, validator, weights."""

from __future__ import annotations

import click

from lemma import __version__
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="lemma")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("doctor")
def doctor_cmd() -> None:
    """Check local environment and chain RPC."""
    from lemma.cli.doctor import run_doctor

    raise SystemExit(run_doctor())


@main.group("miner", invoke_without_command=True)
@click.pass_context
def miner_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@miner_group.command("start")
def miner_start_cmd() -> None:
    """Listen on AXON_PORT for validator forwards."""
    from lemma.miner.service import MinerService

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    MinerService(settings).run()


@main.group("validator", invoke_without_command=True)
@click.pass_context
def validator_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@validator_group.command("start")
def validator_start_cmd() -> None:
    """Run scoring rounds until Ctrl+C."""
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    ValidatorService(settings, dry_run=False).run_blocking()


@validator_group.command("dry-run")
def validator_dry_run_cmd() -> None:
    """Run scoring rounds without writing on-chain weights."""
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    ValidatorService(settings, dry_run=True).run_blocking()


@main.command("weights")
def weights_cmd() -> None:
    """Print chain head and netuid (debug)."""
    from lemma.common.subtensor import get_subtensor

    settings = LemmaSettings()
    try:
        head = int(get_subtensor(settings).get_current_block())
    except Exception as e:  # noqa: BLE001
        click.echo(f"chain RPC failed: {e}", err=True)
        raise SystemExit(2) from e
    click.echo(f"chain_head={head}")
    click.echo(f"netuid={settings.netuid}")


if __name__ == "__main__":
    main(prog_name="lemma")

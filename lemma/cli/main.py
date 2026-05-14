"""Lemma CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from lemma import __version__
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import get_problem_source, resolve_problem


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="lemma")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("doctor")
def doctor_cmd() -> None:
    """Check local environment, config, and chain RPC."""
    from lemma.cli.doctor import run_doctor

    raise SystemExit(run_doctor())


@main.command("meta")
def meta_cmd() -> None:
    """Print canonical problem-supply registry hashes."""
    import json

    from lemma.problems.generated import generated_registry_canonical_dict, generated_registry_sha256
    from lemma.problems.hybrid import problem_supply_registry_canonical_dict, problem_supply_registry_sha256

    s = LemmaSettings()
    reg_sha = generated_registry_sha256()
    supply_sha = problem_supply_registry_sha256(
        generated_weight=s.lemma_hybrid_generated_weight,
        catalog_weight=s.lemma_hybrid_catalog_weight,
    )
    reg = generated_registry_canonical_dict()
    supply = problem_supply_registry_canonical_dict(
        generated_weight=s.lemma_hybrid_generated_weight,
        catalog_weight=s.lemma_hybrid_catalog_weight,
    )
    click.echo(f"lemma_version={__version__}")
    click.echo(f"problem_source={s.problem_source}")
    click.echo(f"problem_supply_registry_sha256={supply_sha}")
    click.echo("problem_supply_registry_json=" + json.dumps(supply, sort_keys=True))
    click.echo(f"generated_registry_sha256={reg_sha}")
    click.echo("generated_registry_json=" + json.dumps(reg, sort_keys=True))


@main.command("setup")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path), default=None)
def setup_cmd(env_path: Path | None) -> None:
    """Bootstrap a .env file from current environment defaults."""
    from lemma.cli.env_file import merge_dotenv

    path = env_path or Path(".env")
    s = LemmaSettings()
    merge_dotenv(
        path,
        {
            "NETUID": str(s.netuid),
            "SUBTENSOR_NETWORK": s.subtensor_network or "finney",
            "BT_WALLET_COLD": s.wallet_cold or "default",
            "BT_WALLET_HOT": s.wallet_hot or "default",
            "LEMMA_USE_DOCKER": "1" if s.lean_use_docker else "0",
            "LEMMA_PROBLEM_SOURCE": s.problem_source or "hybrid",
        },
    )
    click.echo(f"wrote {path}")


@main.group("problems", invoke_without_command=True)
@click.pass_context
def problems_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@problems_group.command("list")
def problems_list_cmd() -> None:
    """List enumerable catalog problems (generated source has none)."""
    settings = LemmaSettings()
    rows = get_problem_source(settings).all_problems()
    if not rows:
        click.echo("No enumerable rows (generated source uses gen/<seed> ids).")
        return
    for p in rows:
        click.echo(f"{p.id}\t{p.split}\t{p.theorem_name}")


@problems_group.command("show")
@click.argument("problem_id")
def problems_show_cmd(problem_id: str) -> None:
    """Print Challenge.lean source for one problem."""
    settings = LemmaSettings()
    p = resolve_problem(settings, problem_id)
    click.echo(p.challenge_source)


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


@main.command("verify")
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
    help="Path to a Submission.lean file.",
)
def verify_cmd(problem_id: str, submission_path: Path) -> None:
    """Verify a Submission.lean file against a catalog problem."""
    from lemma.lean.verify_runner import run_lean_verify

    settings = LemmaSettings()
    src = submission_path.read_text(encoding="utf-8")
    p = resolve_problem(settings, problem_id)
    vr = run_lean_verify(
        settings,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=p,
        proof_script=src,
    )
    click.echo(vr.model_dump_json(indent=2))
    sys.exit(0 if vr.passed else 1)


@main.command("weights")
def weights_cmd() -> None:
    """Print last on-chain weights this validator emitted (debug)."""
    settings = LemmaSettings()
    from lemma.common.subtensor import get_subtensor

    try:
        sub = get_subtensor(settings)
        head = int(sub.get_current_block())
    except Exception as e:  # noqa: BLE001
        click.echo(f"chain RPC failed: {e}", err=True)
        raise SystemExit(2) from e
    click.echo(f"chain_head={head}")
    click.echo(f"netuid={settings.netuid}")


def _run() -> None:
    """Entry point — keeps imports lazy."""
    main(prog_name="lemma")


if __name__ == "__main__":
    _run()

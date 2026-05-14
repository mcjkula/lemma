"""Doctor: styled environment, config, and chain RPC check."""

from __future__ import annotations

from pathlib import Path

import click

from lemma.cli.style import finish_cli_output, stylize
from lemma.common.config import LemmaSettings


def _chain_head(settings: LemmaSettings) -> tuple[int | None, Exception | None]:
    try:
        from lemma.common.subtensor import get_subtensor

        return int(get_subtensor(settings).get_current_block()), None
    except Exception as exc:  # noqa: BLE001
        return None, exc


def run_doctor() -> int:
    ok = True
    click.echo(stylize("\nlemma doctor", fg="cyan", bold=True))
    click.echo(stylize("-" * 42, dim=True))

    click.echo(stylize("\n1  Environment", fg="cyan", bold=True))
    if (Path.cwd() / ".venv").is_dir():
        click.echo(stylize("   OK", fg="green") + "    .venv present")
    else:
        click.echo(stylize("   MISS", fg="red") + "  .venv - run `uv sync --extra btcli`", err=True)
        ok = False

    try:
        settings = LemmaSettings()
    except Exception as exc:  # noqa: BLE001
        click.echo(stylize("CONFIG ERROR: ", fg="red") + str(exc), err=True)
        finish_cli_output()
        return 1

    click.echo(stylize("\n2  Configuration (.env)", fg="cyan", bold=True))
    click.echo(stylize("   OK", fg="green") + f"    NETUID={settings.netuid}  lean_use_docker={settings.lean_use_docker}")
    click.echo(stylize("   .", dim=True) + f"    wallet={settings.wallet_cold}/{settings.wallet_hot}")

    click.echo(stylize("\n3  Lean sandbox", fg="cyan", bold=True))
    worker = (settings.lemma_lean_docker_worker or "").strip()
    if worker:
        click.echo(stylize("   OK", fg="green") + f"    LEMMA_LEAN_DOCKER_WORKER={worker!r}")
    else:
        click.echo(stylize("   WARN", fg="yellow") + "  LEMMA_LEAN_DOCKER_WORKER unset; validator cannot verify.", err=True)
        ok = False

    click.echo(stylize("\n4  Chain RPC", fg="cyan", bold=True))
    chain_head, chain_error = _chain_head(settings)
    if chain_head is not None:
        click.echo(stylize("   OK", fg="green") + f"    head_block={chain_head}")
    else:
        click.echo(stylize("   SKIP", fg="yellow") + f"  (offline OK): {chain_error}")

    summary = "OK" if ok else "WARN - see lines above before running validator."
    click.echo(stylize(f"\nSummary: {summary}", fg="green" if ok else "yellow"), err=not ok)
    finish_cli_output()
    return 0 if ok else 1

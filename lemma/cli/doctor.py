"""Doctor: styled environment, config, and chain RPC check."""

from __future__ import annotations

from pathlib import Path

import click

from lemma.cli.style import finish_cli_output, stylize
from lemma.common.config import LemmaSettings


def _chain_snapshot(settings: LemmaSettings) -> tuple[int | None, Exception | None]:
    try:
        from lemma.common.subtensor import get_subtensor

        head = int(get_subtensor(settings).get_current_block())
        return head, None
    except Exception as exc:  # noqa: BLE001
        return None, exc


def run_doctor() -> int:
    ok = True
    root = Path.cwd()
    click.echo(stylize("\nlemma doctor", fg="cyan", bold=True))
    click.echo(stylize("-" * 42, dim=True))

    click.echo(stylize("\n1  Environment", fg="cyan", bold=True))
    if (root / ".venv").is_dir():
        click.echo(stylize("   OK", fg="green") + "    .venv present (core Lemma uv env)")
    else:
        click.echo(
            stylize("   MISS", fg="red")
            + "  .venv - run from the core Lemma repo after `uv sync --extra btcli`",
            err=True,
        )
        ok = False

    try:
        settings = LemmaSettings()
    except Exception as exc:  # noqa: BLE001
        click.echo(stylize("CONFIG ERROR: ", fg="red") + str(exc), err=True)
        finish_cli_output()
        return 1

    click.echo(stylize("\n2  Configuration (.env)", fg="cyan", bold=True))
    click.echo(
        stylize("   OK", fg="green")
        + f"    NETUID={settings.netuid}  lean_use_docker={settings.lean_use_docker}",
    )
    click.echo(
        stylize("   .", dim=True)
        + f"    wallet={settings.wallet_cold}/{settings.wallet_hot}",
    )
    click.echo(
        stylize(
            "   (Keys above follow active config - `.env` wins over shell unless LEMMA_PREFER_PROCESS_ENV=1.)",
            dim=True,
        ),
    )

    click.echo(stylize("\n3  Lean sandbox", fg="cyan", bold=True))
    worker = (settings.lemma_lean_docker_worker or "").strip()
    if worker:
        click.echo(stylize("   OK", fg="green") + f"    LEMMA_LEAN_DOCKER_WORKER={worker!r}")
    else:
        click.echo(
            stylize("   WARN", fg="yellow")
            + "  LEMMA_LEAN_DOCKER_WORKER is unset; validator cannot verify proofs.",
            err=True,
        )
        ok = False

    click.echo(stylize("\n4  Chain RPC", fg="cyan", bold=True))
    chain_head, chain_error = _chain_snapshot(settings)
    if chain_head is not None:
        click.echo(stylize("   OK", fg="green") + f"    head_block={chain_head}")
    else:
        click.echo(stylize("   SKIP", fg="yellow") + f"  (offline OK): {chain_error}")

    click.echo(
        stylize(
            "\n5  Next commands\n"
            "     lemma validator dry-run   - validate scoring loop without writing weights\n"
            "     lemma validator start     - run scoring rounds and set_weights\n"
            "     lemma miner start         - serve /lemma/commit and /lemma/reveal\n"
            "     lemma weights             - print chain head + netuid (debug)\n",
            dim=True,
        ),
        nl=False,
    )

    if ok:
        click.echo(stylize("\nSummary: OK", fg="green"))
    else:
        click.echo(
            stylize("\nSummary: WARN - see lines above before running validator.", fg="yellow"),
            err=True,
        )
    finish_cli_output()
    return 0 if ok else 1

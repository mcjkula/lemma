"""Minimal environment + chain RPC check."""

from __future__ import annotations

import click

from lemma.common.config import LemmaSettings


def run_doctor() -> int:
    try:
        settings = LemmaSettings()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"CONFIG ERROR: {exc}", err=True)
        return 1

    click.echo(f"netuid={settings.netuid}")
    click.echo(f"lean_use_docker={settings.lean_use_docker}")
    click.echo(f"wallet={settings.wallet_cold}/{settings.wallet_hot}")

    try:
        from lemma.common.subtensor import get_subtensor

        head = int(get_subtensor(settings).get_current_block())
        click.echo(f"chain_head={head}")
    except Exception as exc:  # noqa: BLE001
        click.echo(f"chain_rpc_error={exc}", err=True)
        return 2
    return 0

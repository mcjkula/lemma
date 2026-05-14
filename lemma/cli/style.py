"""Terminal styling and end-of-command stream flushing."""

from __future__ import annotations

import os
import sys
from typing import Any

import click


def colors_enabled() -> bool:
    # no-color.org: NO_COLOR disables ANSI regardless of value.
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def stylize(text: str, **kwargs: Any) -> str:
    return click.style(text, **kwargs) if colors_enabled() else text


def _poke_controlling_tty() -> None:
    # Cursor / VS Code can replace sys.stdout so isatty() lies; /dev/tty is the real terminal.
    if os.name != "posix":
        return
    try:
        with open("/dev/tty", "w", encoding="utf-8", errors="replace") as tty:
            if "NO_COLOR" not in os.environ:
                tty.write("\r\033[0m\033[39m\033[49m\033[?25h")
            tty.write("\n\n")
            tty.flush()
    except OSError:
        pass


def finish_cli_output() -> None:
    """Newline + reset + flush so the shell prompt redraws after mixed stdout/stderr."""
    no_color = "NO_COLOR" in os.environ
    for stream in (sys.stderr, sys.stdout):
        try:
            if not no_color and stream.isatty():
                stream.write("\r\033[0m\033[39m\033[49m\033[?25h\n")
            else:
                stream.write("\n")
            stream.flush()
        except (BrokenPipeError, OSError):
            pass
    click.echo("")
    _poke_controlling_tty()

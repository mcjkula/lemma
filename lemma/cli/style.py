"""Terminal styling: color when stdout is a TTY and NO_COLOR is unset."""

from __future__ import annotations

import os
import sys
from contextlib import suppress
from typing import Any

import click


def colors_enabled() -> bool:
    # https://no-color.org/ — if NO_COLOR is set (any value), disable ANSI.
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def stylize(text: str, **kwargs: Any) -> str:
    if not colors_enabled():
        return text
    return click.style(text, **kwargs)


def _poke_controlling_tty() -> None:
    """Cursor/VS Code redirect sys.stdout so isatty() lies; /dev/tty is the real terminal."""
    if os.name != "posix":
        return
    with suppress(OSError), open("/dev/tty", "w", encoding="utf-8", errors="replace") as tty:
        if "NO_COLOR" not in os.environ:
            tty.write("\r\033[0m\033[39m\033[49m\033[?25h")
        tty.write("\n\n")
        tty.flush()


def finish_cli_output() -> None:
    """End-of-command newline + reset so the shell prompt redraws after mixed stdout/stderr."""
    no_color = "NO_COLOR" in os.environ
    # Stderr first: zsh/bash under Cursor/VS Code attach the prompt to stderr-backed styling.
    for stream in (sys.stderr, sys.stdout):
        with suppress(BrokenPipeError, OSError):
            if not no_color and stream.isatty():
                stream.write("\r\033[0m\033[39m\033[49m\033[?25h\n")
            else:
                stream.write("\n")
            stream.flush()
    with suppress(BrokenPipeError, OSError):
        if sys.stderr.isatty():
            sys.stderr.write("\n")
            sys.stderr.flush()
    click.echo("")
    _poke_controlling_tty()

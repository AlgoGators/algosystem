"""Compatibility import for the CLI entry point."""

from __future__ import annotations

from algosystem.interfaces.cli.main import cli

__all__ = ["cli"]


if __name__ == "__main__":
    cli()

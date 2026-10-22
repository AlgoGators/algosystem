"""Fuzz the public metric-key and legacy-alias input boundary."""

from __future__ import annotations

import sys

from algosystem.shared.metric_key import LEGACY_ALIASES, MetricKey


def test_one_input(data: bytes) -> None:
    """Resolve arbitrary metric text and exercise the resulting key."""
    text = data[:128].decode("utf-8", errors="replace")
    try:
        key = MetricKey(text)
    except ValueError:
        key = LEGACY_ALIASES.get(text)
        if key is None:
            return

    assert key.label()
    assert isinstance(key.is_benchmark_relative(), bool)


if __name__ == "__main__":
    import atheris

    # PyInstaller uses a custom import loader, so instrument target functions.
    atheris.instrument_func(MetricKey.label)
    atheris.instrument_func(MetricKey.is_benchmark_relative)
    atheris.instrument_func(test_one_input)

    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()

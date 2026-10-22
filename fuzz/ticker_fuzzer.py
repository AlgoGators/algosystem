"""Fuzz the public ticker and benchmark alias validation boundary."""

from __future__ import annotations

import sys

from algosystem.marketdata.domain.benchmark import BenchmarkCatalog, Ticker
from algosystem.shared.errors import ConfigurationError, UnknownBenchmarkError


def test_one_input(data: bytes) -> None:
    """Accept only documented input errors for arbitrary ticker and alias text."""
    text = data[:256].decode("utf-8", errors="replace")

    try:
        ticker = Ticker(text)
    except ConfigurationError:
        pass
    else:
        assert ticker.value == text.strip()

    try:
        benchmark = BenchmarkCatalog.standard().lookup(text)
    except UnknownBenchmarkError:
        pass
    else:
        assert benchmark.alias == text.strip()


if __name__ == "__main__":
    import atheris

    # Instrument only the target functions; PyInstaller uses a custom import loader.
    atheris.instrument_func(Ticker.__post_init__)
    atheris.instrument_func(BenchmarkCatalog.lookup)
    atheris.instrument_func(BenchmarkCatalog._unknown_alias)
    atheris.instrument_func(test_one_input)

    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()

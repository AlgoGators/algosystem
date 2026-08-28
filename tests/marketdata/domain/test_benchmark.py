import pytest

from algosystem.marketdata.domain.benchmark import STANDARD_CATALOG, Ticker
from algosystem.shared.errors import ConfigurationError, UnknownBenchmarkError


def test_catalog_exposes_alias_lookup_and_info_from_single_declaration():
    aliases = STANDARD_CATALOG.aliases()
    info = STANDARD_CATALOG.info_frame()

    assert "sp500" in aliases
    assert STANDARD_CATALOG.lookup("sp500").ticker.value == "^GSPC"
    assert set(info["Alias"]) == set(aliases)
    assert set(info.columns) == {"Alias", "Category", "Ticker/Symbol", "Description"}


def test_unknown_benchmark_lists_near_matches():
    with pytest.raises(UnknownBenchmarkError) as exc_info:
        STANDARD_CATALOG.lookup("sp50")

    message = str(exc_info.value)
    assert "sp50" in message
    assert "sp500" in message


def test_ticker_rejects_empty_whitespace_and_unsupported_characters():
    with pytest.raises(ConfigurationError):
        Ticker("")
    with pytest.raises(ConfigurationError):
        Ticker("SP 500")
    with pytest.raises(ConfigurationError):
        Ticker("SPY!")

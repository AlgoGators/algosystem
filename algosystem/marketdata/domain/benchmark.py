"""Benchmark catalog value objects."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd

from algosystem.shared.errors import ConfigurationError, UnknownBenchmarkError

DEFAULT_BENCHMARK = "sp500"
_TICKER_RE = re.compile(r"^[A-Za-z0-9.^=_-]+$")


@dataclass(frozen=True)
class Ticker:
    """Validated market-data ticker symbol."""

    value: str

    def __post_init__(self) -> None:
        ticker = str(self.value).strip()
        if not ticker:
            raise ConfigurationError("ticker must be a non-empty string")
        if any(char.isspace() for char in ticker):
            raise ConfigurationError("ticker must not contain whitespace")
        if _TICKER_RE.fullmatch(ticker) is None:
            raise ConfigurationError(f"ticker contains unsupported characters: {ticker}")
        object.__setattr__(self, "value", ticker)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Benchmark:
    """Benchmark catalog entry."""

    alias: str
    ticker: Ticker
    description: str
    category: str

    def __post_init__(self) -> None:
        alias = str(self.alias).strip()
        description = str(self.description).strip()
        category = str(self.category).strip()
        if not alias:
            raise ConfigurationError("benchmark alias must be non-empty")
        if not description:
            raise ConfigurationError("benchmark description must be non-empty")
        if not category:
            raise ConfigurationError("benchmark category must be non-empty")
        object.__setattr__(self, "alias", alias)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "category", category)


@dataclass(frozen=True)
class BenchmarkCatalog:
    """Single source of truth for available benchmark aliases and categories."""

    benchmarks: tuple[Benchmark, ...]

    def __post_init__(self) -> None:
        aliases = [benchmark.alias for benchmark in self.benchmarks]
        duplicates = sorted({alias for alias in aliases if aliases.count(alias) > 1})
        if duplicates:
            raise ConfigurationError(f"duplicate benchmark aliases: {', '.join(duplicates)}")
        if DEFAULT_BENCHMARK not in aliases:
            raise ConfigurationError(f"default benchmark is not in catalog: {DEFAULT_BENCHMARK}")

    @classmethod
    def standard(cls) -> "BenchmarkCatalog":
        """Return the built-in benchmark catalog."""
        return cls(_STANDARD_BENCHMARKS)

    def aliases(self) -> list[str]:
        """Return aliases sorted for display."""
        return sorted(benchmark.alias for benchmark in self.benchmarks)

    def lookup(self, alias: str) -> Benchmark:
        """Return a benchmark by alias."""
        normalized = str(alias).strip()
        mapping = self.alias_lookup()
        try:
            return mapping[normalized]
        except KeyError as exc:
            raise self._unknown_alias(normalized) from exc

    def alias_lookup(self) -> dict[str, Benchmark]:
        """Return alias to Benchmark mapping."""
        return {benchmark.alias: benchmark for benchmark in self.benchmarks}

    def ticker_lookup(self) -> dict[str, str]:
        """Return alias to ticker mapping."""
        return {benchmark.alias: benchmark.ticker.value for benchmark in self.benchmarks}

    def info_frame(self) -> pd.DataFrame:
        """Return display information for all benchmarks."""
        rows = [
            {
                "Alias": benchmark.alias,
                "Category": benchmark.category,
                "Ticker/Symbol": benchmark.ticker.value,
                "Description": benchmark.description,
            }
            for benchmark in self._in_category_order()
        ]
        return pd.DataFrame(rows)

    def _in_category_order(self) -> Sequence[Benchmark]:
        category_order = []
        for benchmark in self.benchmarks:
            if benchmark.category not in category_order:
                category_order.append(benchmark.category)
        ordered = []
        for category in category_order:
            ordered.extend(
                sorted(
                    (benchmark for benchmark in self.benchmarks if benchmark.category == category),
                    key=lambda benchmark: benchmark.alias,
                )
            )
        return ordered

    def _unknown_alias(self, alias: str) -> UnknownBenchmarkError:
        aliases = self.aliases()
        matches = difflib.get_close_matches(alias, aliases, n=5)
        if matches:
            message = f"unknown benchmark alias {alias!r}; near matches: {', '.join(matches)}"
        else:
            message = (
                f"unknown benchmark alias {alias!r}; available aliases: " f"{', '.join(aliases)}"
            )
        return UnknownBenchmarkError(message)


def _benchmark(alias: str, ticker: str, description: str, category: str) -> Benchmark:
    return Benchmark(alias=alias, ticker=Ticker(ticker), description=description, category=category)


def _benchmarks(entries: Iterable[tuple[str, str, str, str]]) -> tuple[Benchmark, ...]:
    return tuple(
        _benchmark(alias, ticker, description, category)
        for alias, ticker, description, category in entries
    )


_STANDARD_BENCHMARKS = _benchmarks(
    (
        (
            "sp500",
            "^GSPC",
            "S&P 500 Index - 500 of the largest US companies",
            "Stock indices",
        ),
        (
            "nasdaq",
            "^IXIC",
            "NASDAQ Composite Index - US tech-heavy stock market index",
            "Stock indices",
        ),
        (
            "djia",
            "^DJI",
            "Dow Jones Industrial Average - 30 prominent US companies",
            "Stock indices",
        ),
        (
            "russell2000",
            "^RUT",
            "Russell 2000 Index - 2000 small-cap US companies",
            "Stock indices",
        ),
        (
            "vix",
            "^VIX",
            "CBOE Volatility Index - Market expectation of 30-day volatility",
            "Stock indices",
        ),
        ("10y_treasury", "^TNX", "10-Year US Treasury Yield", "Treasury yields"),
        ("5y_treasury", "^FVX", "5-Year US Treasury Yield", "Treasury yields"),
        ("30y_treasury", "^TYX", "30-Year US Treasury Yield", "Treasury yields"),
        ("13w_treasury", "^IRX", "13-Week US Treasury Yield", "Treasury yields"),
        (
            "treasury_bonds",
            "TLT",
            "iShares 20+ Year Treasury Bond ETF (TLT)",
            "ETFs",
        ),
        (
            "corporate_bonds",
            "LQD",
            "iShares iBoxx $ Investment Grade Corporate Bond ETF (LQD)",
            "ETFs",
        ),
        (
            "high_yield_bonds",
            "HYG",
            "iShares iBoxx $ High Yield Corporate Bond ETF (HYG)",
            "ETFs",
        ),
        ("gold", "GLD", "SPDR Gold Shares (GLD)", "ETFs"),
        (
            "commodities",
            "DBC",
            "Invesco DB Commodity Index Tracking Fund (DBC)",
            "ETFs",
        ),
        ("real_estate", "VNQ", "Vanguard Real Estate ETF (VNQ)", "ETFs"),
        (
            "europe",
            "^STOXX50E",
            "EURO STOXX 50 - 50 of the largest Eurozone companies",
            "International",
        ),
        (
            "uk",
            "^FTSE",
            "FTSE 100 Index - 100 companies listed on the London Stock Exchange",
            "International",
        ),
        (
            "japan",
            "^N225",
            "Nikkei 225 - Japan leading stock market index",
            "International",
        ),
        ("china", "000001.SS", "Shanghai Composite Index", "International"),
        (
            "emerging_markets",
            "EEM",
            "iShares MSCI Emerging Markets ETF (EEM)",
            "International",
        ),
        (
            "trend_following",
            "DBMF",
            "iMGP DBi Managed Futures Strategy ETF (DBMF)",
            "Alternative strategies",
        ),
        (
            "hedge_fund",
            "HFRX",
            "HFRX Global Hedge Fund Index approximation",
            "Alternative strategies",
        ),
        ("risk_parity", "RPAR", "RPAR Risk Parity ETF", "Alternative strategies"),
        (
            "momentum",
            "MTUM",
            "iShares MSCI USA Momentum Factor ETF (MTUM)",
            "Alternative strategies",
        ),
        (
            "value",
            "VLUE",
            "iShares MSCI USA Value Factor ETF (VLUE)",
            "Alternative strategies",
        ),
        (
            "low_vol",
            "USMV",
            "iShares MSCI USA Min Vol Factor ETF (USMV)",
            "Alternative strategies",
        ),
        ("technology", "XLK", "Technology Select Sector SPDR Fund (XLK)", "Sectors"),
        ("healthcare", "XLV", "Health Care Select Sector SPDR Fund (XLV)", "Sectors"),
        ("financials", "XLF", "Financial Select Sector SPDR Fund (XLF)", "Sectors"),
        ("energy", "XLE", "Energy Select Sector SPDR Fund (XLE)", "Sectors"),
        ("utilities", "XLU", "Utilities Select Sector SPDR Fund (XLU)", "Sectors"),
    )
)


STANDARD_CATALOG = BenchmarkCatalog.standard()

__all__ = [
    "DEFAULT_BENCHMARK",
    "STANDARD_CATALOG",
    "Benchmark",
    "BenchmarkCatalog",
    "Ticker",
]

"""Application-layer request and response DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

import pandas as pd

from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.shared.values import DateRange, Money, Percent, RunId

PriceInput = Union[pd.DataFrame, pd.Series]


@dataclass(frozen=True)
class RunBacktestRequest:
    """Request to run a backtest from raw price/equity inputs."""

    data: PriceInput
    benchmark: Optional[PriceInput] = None
    start: Optional[object] = None
    end: Optional[object] = None
    initial_capital: Optional[object] = None
    price_column: Optional[str] = None


@dataclass(frozen=True)
class RunBacktestResponse:
    """Result of running a backtest, mapped to caller-friendly values."""

    run_id: Optional[RunId]
    metrics: dict[str, float]
    equity: pd.Series
    benchmark: Optional[pd.Series]
    date_range: DateRange
    initial_capital: Money
    final_capital: Money
    total_return: Percent
    summary: dict[str, object]


@dataclass(frozen=True)
class ArchiveRunRequest:
    """Request to persist a completed backtest result."""

    result: BacktestResult
    name: Optional[str] = None
    description: str = ""
    hyperparameters: Optional[Mapping[str, object]] = None
    overwrite: bool = False


@dataclass(frozen=True)
class ArchiveRunResponse:
    """Response returned after a run has been archived."""

    run_id: RunId


@dataclass(frozen=True)
class LoadRunRequest:
    """Request to load a persisted run."""

    run_id: Union[RunId, str]


@dataclass(frozen=True)
class LoadRunResponse:
    """Response containing a rehydrated backtest result."""

    result: BacktestResult


@dataclass(frozen=True)
class CompareRunsRequest:
    """Request to compare persisted runs."""

    run_ids: Sequence[Union[RunId, str]]


@dataclass(frozen=True)
class CompareRunsResponse:
    """Response containing summaries and aligned equity curves."""

    summaries: list[dict[str, object]]
    equity_curves: pd.DataFrame


@dataclass(frozen=True)
class GenerateTearsheetRequest:
    """Request to render a quantstats tearsheet for a result."""

    result: BacktestResult
    output: Union[Path, str]
    title: str
    mode: str = "html"
    rf: float = 0.0
    periods_per_year: int = 252


@dataclass(frozen=True)
class GenerateTearsheetResponse:
    """Response returned after rendering a tearsheet."""

    output: Path

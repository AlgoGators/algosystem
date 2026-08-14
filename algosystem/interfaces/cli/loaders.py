"""CLI input loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd

from algosystem.shared.errors import InvalidPriceSeriesError

PathInput = Union[str, Path]
_DATE_COLUMN_NAMES = {"date", "datetime", "timestamp", "time"}


def load_prices(path: PathInput) -> pd.DataFrame:
    """Load a CSV file and return a DataFrame indexed by dates."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise InvalidPriceSeriesError(f"input file not found: {csv_path}")
    frame = pd.read_csv(csv_path)
    if frame.empty:
        raise InvalidPriceSeriesError(f"input file is empty: {csv_path}")
    return _with_datetime_index(frame, csv_path)


def load_benchmark_input(
    value: Optional[str],
    start: object = None,
    end: object = None,
) -> Optional[pd.Series]:
    """Load a benchmark from a local CSV path or benchmark alias."""
    if value is None or str(value).strip() == "":
        return None

    candidate = Path(value)
    if candidate.exists():
        frame = load_prices(candidate)
        return _single_series(frame, source=candidate)

    from algosystem.marketdata.benchmark import fetch_benchmark_data

    return fetch_benchmark_data(value, start_date=start, end_date=end)


def _with_datetime_index(frame: pd.DataFrame, source: Path) -> pd.DataFrame:
    for column in _candidate_date_columns(frame):
        parsed = pd.to_datetime(frame[column], errors="coerce")
        if parsed.notna().all():
            indexed = frame.drop(columns=[column]).copy()
            indexed.index = pd.DatetimeIndex(parsed)
            indexed = indexed.sort_index()
            indexed.index.name = column
            return indexed
    raise InvalidPriceSeriesError(f"could not detect a date column in: {source}")


def _candidate_date_columns(frame: pd.DataFrame) -> list[str]:
    named = [
        column
        for column in frame.columns
        if str(column).strip().lower() in _DATE_COLUMN_NAMES
        or str(column).lower().startswith("unnamed")
    ]
    return named + [column for column in frame.columns if column not in named]


def _single_series(frame: pd.DataFrame, source: Path) -> pd.Series:
    numeric = frame.select_dtypes(include="number")
    if numeric.empty:
        raise InvalidPriceSeriesError(f"benchmark file has no numeric price column: {source}")
    series = numeric.iloc[:, 0].copy()
    series.index = frame.index
    series.name = numeric.columns[0]
    return series


__all__ = ["load_benchmark_input", "load_prices"]

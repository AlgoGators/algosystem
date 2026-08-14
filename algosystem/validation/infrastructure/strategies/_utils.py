"""Shared utility functions for strategy backtests."""

from __future__ import annotations

import numpy as np


def sharpe(returns: np.ndarray, annualize: float = 252.0) -> float:
    """Return annualized Sharpe for a daily return array."""
    if len(returns) < 2:
        return 0.0
    mean = np.mean(returns)
    std = np.std(returns, ddof=1)
    if std < 1e-12:
        return 0.0
    return float((mean / std) * np.sqrt(annualize))

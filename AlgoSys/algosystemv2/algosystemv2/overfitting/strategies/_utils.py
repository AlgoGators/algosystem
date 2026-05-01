"""Shared utility functions for strategy backtests."""

from __future__ import annotations

import numpy as np


def sharpe(returns: np.ndarray, annualize: float = 252.0) -> float:
    """Annualized Sharpe from a daily returns array."""
    if len(returns) < 2:
        return 0.0
    m = np.mean(returns)
    s = np.std(returns, ddof=1)
    if s < 1e-12:
        return 0.0
    return (m / s) * np.sqrt(annualize)

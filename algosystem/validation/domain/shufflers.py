"""
Return-series shuffling strategies for permutation tests.

Each shuffler takes a 1-D numpy array of returns and an RNG,
and returns a shuffled copy that destroys any real signal while
preserving certain statistical properties.

Three methods that trade off between preserving temporal structure
and destroying exploitable signal:

- complete_shuffle: IID shuffle — destroys all autocorrelation
- block_shuffle: stationary block bootstrap — preserves local structure
- cyclic_shuffle: circular shift — preserves all autocorrelation
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Callable, Mapping

import numpy as np


def _coerce_rng(rng: np.random.Generator | None) -> np.random.Generator:
    return rng if rng is not None else np.random.default_rng()


def complete_shuffle(
    returns: np.ndarray,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Fisher-Yates shuffle (iid assumption).

    Destroys ALL temporal structure (autocorrelation, volatility clustering).
    Preserves the exact marginal distribution.

    Best for: strategies where you believe returns are approximately iid,
    or as a conservative test (hardest to beat).
    """
    shuffled = returns.copy()
    _coerce_rng(rng).shuffle(shuffled)
    return shuffled


def block_shuffle(
    returns: np.ndarray,
    rng: np.random.Generator | None = None,
    block_size: int | None = None,
) -> np.ndarray:
    """
    Stationary block bootstrap with wrapping.

    Draws random starting positions and copies contiguous blocks,
    wrapping around the end. Block size defaults to sqrt(n).

    Preserves: local autocorrelation and volatility clustering within blocks.
    Destroys: long-range dependencies and any real signal that spans blocks.

    Best for: strategies on financial time series where short-term
    autocorrelation (momentum, mean-reversion) is a feature of the
    market microstructure, not of your strategy.
    """
    n = len(returns)
    generator = _coerce_rng(rng)
    if block_size is None:
        block_size = max(2, int(np.sqrt(n)))

    result = np.empty(n, dtype=returns.dtype)
    pos = 0
    while pos < n:
        start = generator.integers(0, n)
        length = min(block_size, n - pos)
        indices = np.arange(start, start + length) % n
        result[pos : pos + length] = returns[indices]
        pos += length
    return result


def cyclic_shuffle(
    returns: np.ndarray,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Cyclic (circular) permutation.

    Shifts the entire series by a random offset, wrapping around.
    Preserves ALL autocorrelation structure exactly.
    Only destroys the alignment between returns and calendar time.

    Best for: testing whether the strategy's edge comes from the
    specific timing of trades rather than from the return dynamics.
    This is the most conservative shuffler — hardest to reject H0.
    """
    n = len(returns)
    offset = _coerce_rng(rng).integers(1, n)
    return np.roll(returns, offset)


SHUFFLE_METHODS: Mapping[str, Callable[..., np.ndarray]] = MappingProxyType(
    {
        "complete": complete_shuffle,
        "cyclic": cyclic_shuffle,
        "block": block_shuffle,
    }
)

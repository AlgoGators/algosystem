"""
Synthetic return series generators for testing overfitting detection.

Each generator produces a specific market regime structure:
- noise: pure IID — no exploitable structure
- trending: regime-switching with momentum
- mean_reverting: AR(1) process
- volatile_regimes: alternating high/low volatility
"""

from __future__ import annotations

import numpy as np


def generate_noise(n: int = 3000, seed: int = 42) -> np.ndarray:
    """Pure IID noise — no exploitable structure."""
    return np.random.default_rng(seed).normal(0.00005, 0.01, size=n)


def generate_trending(n: int = 3000, seed: int = 42) -> np.ndarray:
    """Regime-switching trending data (momentum-exploitable)."""
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    regime = 1.0
    for i in range(n):
        if rng.random() < 0.005:
            regime *= -1
        returns[i] = regime * 0.0015 + rng.normal(0, 0.01)
    return returns


def generate_mean_reverting(n: int = 3000, seed: int = 42) -> np.ndarray:
    """AR(1) mean-reverting returns (mean-reversion exploitable)."""
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    returns[0] = rng.normal(0, 0.01)
    for i in range(1, n):
        returns[i] = -0.15 * returns[i - 1] + rng.normal(0.0002, 0.01)
    return returns


def generate_volatile_regimes(n: int = 3000, seed: int = 42) -> np.ndarray:
    """Alternating high/low vol regimes (vol-strategy exploitable)."""
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    high_vol = False
    for i in range(n):
        if rng.random() < 0.003:
            high_vol = not high_vol
        vol = 0.025 if high_vol else 0.008
        returns[i] = rng.normal(0.0003, vol)
    return returns

"""Tests for shuffle method correctness."""

import numpy as np
import pytest
from numpy.fft import fft

from algosystem.validation.domain import block_shuffle, complete_shuffle, cyclic_shuffle
from tests.validation.conftest import backtest_noise


class TestCompleteShuffle:
    def test_preserves_length(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        shuffled = complete_shuffle(returns, rng)
        assert len(shuffled) == len(returns)

    def test_preserves_mean(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        shuffled = complete_shuffle(returns, rng)
        assert abs(np.mean(shuffled) - np.mean(returns)) < 1e-10

    def test_preserves_sorted_values(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        shuffled = complete_shuffle(returns, rng)
        assert np.allclose(np.sort(shuffled), np.sort(returns))

    def test_changes_order(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        shuffled = complete_shuffle(returns, rng)
        assert not np.array_equal(shuffled, returns)


class TestCyclicShuffle:
    def test_preserves_length(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        cycled = cyclic_shuffle(returns, rng)
        assert len(cycled) == len(returns)

    def test_preserves_sorted_values(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        cycled = cyclic_shuffle(returns, rng)
        assert np.allclose(np.sort(cycled), np.sort(returns))

    def test_preserves_power_spectrum(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        rng2 = np.random.default_rng(42)
        cycled = cyclic_shuffle(returns, rng2)
        orig_spectrum = np.abs(fft(returns)) ** 2
        cycled_spectrum = np.abs(fft(cycled)) ** 2
        assert np.allclose(orig_spectrum, cycled_spectrum, atol=1e-8)


class TestBlockShuffle:
    def test_preserves_length(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        blocked = block_shuffle(returns, rng, block_size=20)
        assert len(blocked) == len(returns)

    def test_changes_order(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=1000)
        blocked = block_shuffle(returns, rng, block_size=20)
        assert not np.array_equal(blocked, returns)


class TestShuffleMethodsInDetector:
    @pytest.mark.parametrize("method", ["complete", "cyclic", "block"])
    def test_method_completes(self, method):
        from algosystem.validation import OverfitDetector

        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.01, size=200)
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid={"lookback": [5, 10], "threshold": [0.0]},
            n_reps=20,
            shuffle_method=method,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.n_reps == 20

"""
Tests for statistical power:
- Real signal produces low p-values
- No signal produces high p-values
- Deflated Sharpe ratio properties
"""

import numpy as np
import pytest

from algosystem.validation import OverfitDetector
from tests.validation.conftest import backtest_noise


class TestPowerRealSignal:
    @pytest.fixture
    def signal_returns(self):
        rng = np.random.default_rng(42)
        n = 3000
        returns = np.empty(n)
        regime = 1.0
        for i in range(n):
            if rng.random() < 0.005:
                regime *= -1
            returns[i] = regime * 0.002 + rng.normal(0, 0.01)
        return returns

    def test_low_pvalue(self, signal_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=signal_returns,
            param_grid=small_grid,
            n_reps=200,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.unbiased_pvalue < 0.20

    def test_high_deflated_sharpe(self, signal_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=signal_returns,
            param_grid=small_grid,
            n_reps=200,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.deflated_sharpe > 0.5

    def test_low_prob_overfit(self, signal_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=signal_returns,
            param_grid=small_grid,
            n_reps=200,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.prob_overfit < 0.20


class TestNoSignal:
    def test_high_pvalue_on_noise(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0, 0.01, size=2000)
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid={"lookback": [5, 10, 20, 40, 60], "threshold": [0.0, 0.0005, 0.001, 0.002]},
            n_reps=300,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.unbiased_pvalue > 0.10
        assert res.prob_overfit > 0.10


class TestDeflatedSharpe:
    def test_noise_deflated_low(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0, 0.01, size=2000)
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid={"lookback": [5, 10, 20, 40, 60], "threshold": [0.0, 0.0005, 0.001, 0.002]},
            n_reps=300,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.deflated_sharpe < 1.0

    def test_signal_beats_noise(self):
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 0.01, size=2000)
        signal = np.empty(3000)
        regime = 1.0
        for i in range(3000):
            if rng.random() < 0.005:
                regime *= -1
            signal[i] = regime * 0.002 + rng.normal(0, 0.01)

        grid = {"lookback": [5, 10, 20], "threshold": [0.0, 0.001]}
        res_noise = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise,
            param_grid=grid,
            n_reps=300,
            n_workers=1,
            seed=42,
        ).run()
        res_signal = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=signal,
            param_grid=grid,
            n_reps=300,
            n_workers=1,
            seed=42,
        ).run()
        assert res_signal.deflated_sharpe > res_noise.deflated_sharpe

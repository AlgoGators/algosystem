"""Tests for validation pass runners."""

import numpy as np
import pytest

from algosystem.shared.errors import ValidationError
from algosystem.validation import OverfitDetector
from algosystem.validation.application.detect_overfitting import DetectOverfitting
from algosystem.validation.domain.strategy import ParameterGrid, StrategySpec
from algosystem.validation.infrastructure.multiprocessing_runner import MultiprocessingPassRunner
from algosystem.validation.infrastructure.sequential_runner import SequentialPassRunner
from tests.validation.conftest import backtest_noise


def test_same_seed_is_byte_identical_across_runs_and_runners():
    returns = np.random.default_rng(42).normal(0.0, 0.01, size=120)
    strategy = StrategySpec(
        name="noise",
        backtest_fn_path="tests.validation.conftest.backtest_noise",
        parameter_grid=ParameterGrid({"lookback": [5, 10], "threshold": [0.0, 0.001]}),
    )

    seq_runner = SequentialPassRunner(evaluator=backtest_noise)
    mp_runner = MultiprocessingPassRunner(evaluator=backtest_noise, worker_count=2)

    seq_1 = DetectOverfitting(seq_runner).execute(strategy, returns, n_reps=8, seed=7)
    seq_2 = DetectOverfitting(seq_runner).execute(strategy, returns, n_reps=8, seed=7)
    mp = DetectOverfitting(mp_runner).execute(strategy, returns, n_reps=8, seed=7)

    assert np.array_equal(seq_1.original_sharpes, seq_2.original_sharpes)
    assert np.array_equal(seq_1.null_best_sharpes, seq_2.null_best_sharpes)
    assert np.array_equal(seq_1.solo_pvalues, seq_2.solo_pvalues)
    assert np.array_equal(seq_1.original_sharpes, mp.original_sharpes)
    assert np.array_equal(seq_1.null_best_sharpes, mp.null_best_sharpes)
    assert seq_1.unbiased_pvalue == mp.unbiased_pvalue


def test_multiprocessing_runner_reports_unpicklable_backtest_fn():
    returns = np.random.default_rng(42).normal(0.0, 0.01, size=80)

    with pytest.raises(ValidationError, match="module-level function, not a lambda or closure"):
        OverfitDetector(
            backtest_fn=lambda params, ret: 0.0,
            returns=returns,
            param_grid={"lookback": [5], "threshold": [0.0]},
            n_reps=2,
            n_workers=2,
            seed=42,
        ).run()


def test_multiprocessing_runner_accepts_cost_wrapped_shipped_strategy():
    from algosystem.validation.domain import RETAIL_EQUITY
    from algosystem.validation.infrastructure.strategies import make_cost_aware, momentum_backtest

    returns = np.random.default_rng(42).normal(0.0, 0.01, size=100)
    wrapped = make_cost_aware(momentum_backtest, RETAIL_EQUITY, strategy_name="momentum")

    result = OverfitDetector(
        backtest_fn=wrapped,
        returns=returns,
        param_grid={"lookback": [5, 10], "threshold": [0.0]},
        n_reps=2,
        n_workers=2,
        seed=42,
    ).run()

    assert result.n_reps == 2
    assert np.all(np.isfinite(result.original_sharpes))

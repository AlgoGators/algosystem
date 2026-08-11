"""
Tests for the parameter-sensitivity surface:
- cost_sensitivity_pbo across transaction-cost assumptions
- Sobol first-order indices are deterministic and metric-key backed
- the sensitivity path reached through the public facade
"""

import numpy as np
import pytest

from algosystem.validation import OverfitDetector
from algosystem.validation.domain import cost_sensitivity_pbo
from algosystem.validation.domain.validation_metric import ValidationMetricKey
from tests.validation.conftest import backtest_noise

SOBOL = ValidationMetricKey.SOBOL_FIRST.value
PBOS = ValidationMetricKey.PBOS.value
BREAKEVEN = ValidationMetricKey.BREAKEVEN_COST_BPS.value


def _returns_matrix(n_periods=240, n_configs=12, seed=7):
    """Per-period gross returns for several configurations."""
    rng = np.random.default_rng(seed)
    return rng.normal(0.0004, 0.01, size=(n_periods, n_configs))


class TestCostSensitivityPBO:
    def test_expected_keys(self):
        out = cost_sensitivity_pbo(_returns_matrix(), n_splits=6, seed=42)
        assert set(out) == {"cost_levels", PBOS, BREAKEVEN}

    def test_default_cost_ladder(self):
        out = cost_sensitivity_pbo(_returns_matrix(), n_splits=6, seed=42)
        assert out["cost_levels"] == [0, 1, 2, 3, 5, 7, 10]
        assert len(out[PBOS]) == len(out["cost_levels"])

    def test_pbos_are_probabilities(self):
        out = cost_sensitivity_pbo(_returns_matrix(), n_splits=6, seed=42)
        assert all(0.0 <= p <= 1.0 for p in out[PBOS])

    def test_custom_cost_range_is_respected(self):
        levels = [0, 4, 8]
        out = cost_sensitivity_pbo(_returns_matrix(), cost_bps_range=levels, n_splits=6, seed=42)
        assert out["cost_levels"] == levels
        assert len(out[PBOS]) == 3

    def test_deterministic_for_a_given_seed(self):
        matrix = _returns_matrix()
        a = cost_sensitivity_pbo(matrix, n_splits=6, seed=42)
        b = cost_sensitivity_pbo(matrix, n_splits=6, seed=42)
        assert a[PBOS] == b[PBOS]
        assert a[BREAKEVEN] == b[BREAKEVEN]

    def test_breakeven_is_zero_when_already_overfit_at_no_cost(self):
        """Pure noise has no real edge, so PBO starts high and breakeven is 0."""
        rng = np.random.default_rng(3)
        matrix = rng.normal(0.0, 0.01, size=(240, 12))
        out = cost_sensitivity_pbo(matrix, n_splits=6, seed=42)
        if out[PBOS][0] >= 0.5:
            assert out[BREAKEVEN] == 0.0

    def test_breakeven_within_tested_range_or_infinite(self):
        out = cost_sensitivity_pbo(_returns_matrix(), n_splits=6, seed=42)
        be = out[BREAKEVEN]
        assert be == float("inf") or 0.0 <= be <= max(out["cost_levels"])


class TestSobolIndices:
    @pytest.fixture(scope="class")
    def surface(self):
        rng = np.random.default_rng(11)
        returns = rng.normal(0.0003, 0.01, size=600)
        grid = {"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.0005, 0.001]}
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid=grid,
            n_reps=30,
            n_workers=1,
            seed=99,
        )
        return det.run().surface_analysis()

    def test_every_grid_parameter_is_analysed(self, surface):
        assert set(surface["per_param_sensitivity"]) == {"lookback", "threshold"}

    def test_indices_are_bounded(self, surface):
        for vals in surface["per_param_sensitivity"].values():
            assert 0.0 <= vals[SOBOL] <= 1.0

    def test_first_order_indices_do_not_exceed_unity(self, surface):
        """First-order indices sum to <= 1; the remainder is interaction effect."""
        total = sum(v[SOBOL] for v in surface["per_param_sensitivity"].values())
        assert total <= 1.0 + 1e-9

    def test_marginal_range_is_non_negative(self, surface):
        for vals in surface["per_param_sensitivity"].values():
            assert vals["marginal_range"] >= 0.0

    def test_keys_come_from_the_metric_enum(self, surface):
        """Rule V3: validation metric names originate in ValidationMetricKey."""
        for vals in surface["per_param_sensitivity"].values():
            assert SOBOL in vals

    def test_deterministic_across_runs(self):
        rng = np.random.default_rng(11)
        returns = rng.normal(0.0003, 0.01, size=600)
        grid = {"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.0005, 0.001]}

        def run():
            det = OverfitDetector(
                backtest_fn=backtest_noise,
                returns=returns,
                param_grid=grid,
                n_reps=30,
                n_workers=1,
                seed=99,
            )
            return det.run().surface_analysis()["per_param_sensitivity"]

        first, second = run(), run()
        for name in first:
            assert first[name][SOBOL] == second[name][SOBOL]


class TestSurfaceSummaryRendering:
    def test_summary_reports_sensitivity_without_printing(self, capsys):
        """Rule V2: the domain returns lines; it never writes to stdout."""
        rng = np.random.default_rng(5)
        returns = rng.normal(0.0003, 0.01, size=500)
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid={"lookback": [5, 10, 20], "threshold": [0.0, 0.001]},
            n_reps=25,
            n_workers=1,
            seed=7,
        )
        lines = det.run().surface_summary()

        assert isinstance(lines, list)
        assert any("Sobol" in line for line in lines)
        assert capsys.readouterr().out == ""


class TestSensitivityThroughFacade:
    def test_shipped_strategy_exposes_sensitivity(self):
        from algosystem import AlgoSystem

        rng = np.random.default_rng(21)
        returns = rng.normal(0.0002, 0.01, size=600)
        results = AlgoSystem().detect_overfitting(
            strategy="momentum", returns=returns, n_reps=25, seed=13
        )
        per_param = results.surface_analysis()["per_param_sensitivity"]

        assert per_param
        assert all(0.0 <= v[SOBOL] <= 1.0 for v in per_param.values())

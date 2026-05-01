"""Tests for report/plot methods — ensure they don't crash."""

import io
import os
import sys

import numpy as np
import pytest

from algosystemv2.overfitting import OverfitDetector
from algosystemv2.overfitting.visualization import (
    plot_null_distribution,
    plot_parameter_sensitivity,
    plot_surface_2d,
)

from .conftest import backtest_noise


@pytest.fixture
def results():
    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=300)
    det = OverfitDetector(
        backtest_fn=backtest_noise, returns=returns,
        param_grid={'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]},
        n_reps=20, n_workers=1, seed=42,
    )
    return det.run()


class TestReport:
    def test_report_runs(self, results):
        old = sys.stdout
        sys.stdout = io.StringIO()
        results.report()
        output = sys.stdout.getvalue()
        sys.stdout = old
        assert len(output) > 100

    def test_surface_report_runs(self, results):
        old = sys.stdout
        sys.stdout = io.StringIO()
        results.surface_report()
        output = sys.stdout.getvalue()
        sys.stdout = old
        assert len(output) > 50


class TestPlots:
    def test_null_distribution(self, results, tmp_path):
        import matplotlib
        matplotlib.use('Agg')
        path = str(tmp_path / "null.png")
        fig = plot_null_distribution(results, save_path=path)
        assert fig is not None
        assert os.path.exists(path)

    def test_parameter_sensitivity(self, results, tmp_path):
        import matplotlib
        matplotlib.use('Agg')
        path = str(tmp_path / "sens.png")
        fig = plot_parameter_sensitivity(results, save_path=path)
        assert fig is not None
        assert os.path.exists(path)

    def test_surface_2d(self, results, tmp_path):
        import matplotlib
        matplotlib.use('Agg')
        path = str(tmp_path / "2d.png")
        fig = plot_surface_2d(results, 'lookback', 'threshold', save_path=path)
        assert fig is not None
        assert os.path.exists(path)

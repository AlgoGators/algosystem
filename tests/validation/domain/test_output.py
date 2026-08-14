"""Tests for report/plot methods — ensure they don't crash."""

import numpy as np
import pytest

from tests.validation.conftest import backtest_noise


@pytest.fixture
def results():
    from algosystem.validation import OverfitDetector

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=300)
    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={"lookback": [5, 10, 20], "threshold": [0.0, 0.001]},
        n_reps=20,
        n_workers=1,
        seed=42,
    )
    return det.run()


class TestReport:
    def test_report_runs(self, results):
        lines = results.summary()
        assert len("\n".join(lines)) > 100

    def test_surface_report_runs(self, results):
        lines = results.surface_summary()
        assert len("\n".join(lines)) > 50

    def test_html_report_writes_file_without_opening_browser(self, results, tmp_path, monkeypatch):
        calls = []
        monkeypatch.setattr("webbrowser.open", lambda url: calls.append(url))
        from algosystem.validation.infrastructure.html_report import generate_overfit_dashboard

        output = generate_overfit_dashboard(results, output_path=tmp_path / "report.html")

        assert output.exists()
        assert "cdn.plot.ly" in output.read_text(encoding="utf-8")
        assert calls == []


class TestPlots:
    def test_null_distribution(self, results, tmp_path):
        import matplotlib

        from algosystem.validation.infrastructure.matplotlib_charts import plot_null_distribution

        matplotlib.use("Agg")
        path = tmp_path / "null.png"
        fig = plot_null_distribution(results, save_path=path)
        assert fig is not None
        assert path.exists()

    def test_parameter_sensitivity(self, results, tmp_path):
        import matplotlib

        from algosystem.validation.infrastructure.matplotlib_charts import (
            plot_parameter_sensitivity,
        )

        matplotlib.use("Agg")
        path = tmp_path / "sens.png"
        fig = plot_parameter_sensitivity(results, save_path=path)
        assert fig is not None
        assert path.exists()

    def test_surface_2d(self, results, tmp_path):
        import matplotlib

        from algosystem.validation.infrastructure.matplotlib_charts import plot_surface_2d

        matplotlib.use("Agg")
        path = tmp_path / "2d.png"
        fig = plot_surface_2d(results, "lookback", "threshold", save_path=path)
        assert fig is not None
        assert path.exists()

    def test_full_render_restores_backend_and_closes_figures(self, results, tmp_path):
        import matplotlib
        import matplotlib.pyplot as plt

        from algosystem.validation.domain.statistics.cscv import PBOResults
        from algosystem.validation.domain.statistics.diagnostics import AutocorrelationDiagnostic
        from algosystem.validation.domain.statistics.walkforward import WalkForwardResults
        from algosystem.validation.infrastructure.matplotlib_charts import (
            plot_autocorrelation,
            plot_null_distribution,
            plot_overfit_dashboard,
            plot_parameter_sensitivity,
            plot_pbo_distribution,
            plot_pvalue_comparison,
            plot_surface_2d,
            plot_walkforward_degradation,
        )

        original_backend = matplotlib.get_backend()
        plt.close("all")
        pbo = PBOResults(
            pbo=0.25,
            logits=np.array([-1.0, 0.5, 1.0]),
            n_combinations=3,
            n_splits=4,
            n_configs=3,
            is_best_indices=np.array([0, 1, 2]),
            oos_ranks=np.array([1, 2, 3]),
            oos_sharpes_of_best=np.array([0.4, 0.2, -0.1]),
            is_sharpes_of_best=np.array([0.8, 0.7, 0.6]),
            logit_mean=0.1,
            logit_std=0.2,
        )
        wf = WalkForwardResults(
            n_folds=3,
            purge_gap=0,
            is_sharpes=np.array([1.0, 0.8, 0.6]),
            oos_sharpes=np.array([0.7, 0.5, 0.2]),
            best_params_per_fold=[{"lookback": 5}, {"lookback": 10}, {"lookback": 20}],
            degradation_ratios=np.array([0.7, 0.625, 0.333]),
            wfe=0.58,
            mean_is_sharpe=0.8,
            mean_oos_sharpe=0.4667,
            frac_oos_positive=1.0,
            frac_oos_profitable=0.67,
        )
        diagnostic = AutocorrelationDiagnostic(
            acf_1=0.1,
            acf_values=np.array([0.1, 0.05, -0.02]),
            ljung_box_stat=1.2,
            ljung_box_pvalue=0.55,
            has_autocorrelation=False,
            recommended_shuffle="complete",
            warning_message="",
        )

        plot_null_distribution(results, save_path=tmp_path / "null.png")
        plot_parameter_sensitivity(results, save_path=tmp_path / "sens.png")
        plot_surface_2d(results, "lookback", "threshold", save_path=tmp_path / "surf.png")
        plot_overfit_dashboard(
            results,
            pbo_results=pbo,
            wf_results=wf,
            ac_diagnostic=diagnostic,
            n_obs=100,
            save_path=tmp_path / "dash.png",
        )
        plot_pbo_distribution(pbo, save_path=tmp_path / "pbo.png")
        plot_walkforward_degradation(wf, save_path=tmp_path / "wf.png")
        plot_autocorrelation(diagnostic, 100, save_path=tmp_path / "acf.png")
        plot_pvalue_comparison(results, save_path=tmp_path / "pvals.png")

        assert matplotlib.get_backend() == original_backend
        assert plt.get_fignums() == []

"""Canonical validation metric keys used by AlgoSystem."""

from __future__ import annotations

from enum import Enum


class ValidationMetricKey(str, Enum):
    """Single source of truth for validation metric names."""

    # Permutation and p-value metrics
    UNBIASED_PVALUE = "unbiased_pvalue"
    UNBIASED_PVALUES = "unbiased_pvalues"
    SOLO_PVALUE = "solo_pvalue"
    SOLO_PVALUES = "solo_pvalues"
    STEPWISE_PVALUE = "stepwise_pvalue"
    STEPWISE_PVALUES = "stepwise_pvalues"

    # Probability of backtest overfitting
    PBO = "pbo"
    PBOS = "pbos"
    PBO_LOGIT = "logits"
    PBO_LOGIT_MEAN = "logit_mean"
    PBO_LOGIT_STD = "logit_std"
    BREAKEVEN_COST_BPS = "breakeven_cost_bps"

    # Sharpe and multiple-testing metrics
    PSR = "psr"
    DSR = "dsr"
    BEST_DSR = "best_dsr"
    DEFLATED_SHARPE = "deflated_sharpe"
    SHARPE = "sharpe"
    ORIGINAL_SHARPES = "original_sharpes"
    BEST_SHARPE = "best_sharpe"
    SR_HAT = "sr_hat"
    SR0 = "sr0"
    SR0_STAR = "sr0_star"
    IS_SHARPES = "is_sharpes"
    OOS_SHARPES = "oos_sharpes"
    IS_SHARPES_OF_BEST = "is_sharpes_of_best"
    OOS_SHARPES_OF_BEST = "oos_sharpes_of_best"
    DEGRADATION_RATIOS = "degradation_ratios"
    VAR_SR = "var_sr"
    NULL_BEST_SHARPES = "null_best_sharpes"
    NULL_DISTRIBUTION_MEAN = "null_distribution_mean"
    NULL_DISTRIBUTION_STD = "null_distribution_std"
    TEST_STATISTIC = "test_statistic"
    MIN_TRL = "min_trl"

    # Walk-forward metrics
    WFE = "wfe"
    MEAN_IS_SHARPE = "mean_is_sharpe"
    MEAN_OOS_SHARPE = "mean_oos_sharpe"
    FRAC_OOS_POSITIVE = "frac_oos_positive"
    FRAC_OOS_PROFITABLE = "frac_oos_profitable"

    # Return-distribution diagnostics
    MEAN = "mean"
    STD = "std"
    SKEWNESS = "skewness"
    KURTOSIS = "kurtosis"
    ACF1 = "acf1"
    ACF_VALUES = "acf_values"
    LJUNG_BOX_STAT = "ljung_box_stat"
    LJUNG_BOX_PVALUE = "ljung_box_pvalue"
    N_EFFECTIVE = "n_effective"

    # Bootstrap and Monte Carlo robustness metrics
    SHARPE_CI_POINT = "point_estimate"
    SHARPE_CI_LOWER = "ci_lower"
    SHARPE_CI_UPPER = "ci_upper"
    ACTUAL_TERMINAL_PNL = "actual_terminal_pnl"
    ACTUAL_MAX_DRAWDOWN = "actual_max_drawdown"
    TERMINAL_PNL_MEAN = "terminal_pnl_mean"
    TERMINAL_PNL_5TH = "terminal_pnl_5th"
    TERMINAL_PNL_95TH = "terminal_pnl_95th"
    TERMINAL_PNL_PERCENTILE = "terminal_pnl_percentile"
    MAX_DRAWDOWN_MEAN = "max_drawdown_mean"
    MAX_DRAWDOWN_5TH = "max_drawdown_5th"
    MAX_DRAWDOWN_95TH = "max_drawdown_95th"
    MAX_DRAWDOWN_PERCENTILE = "max_drawdown_percentile"

    # Benchmark-relative robustness metrics
    ALPHA_DAILY = "alpha_daily"
    ALPHA_ANNUAL = "alpha_annual"
    BETA = "beta"
    R_SQUARED = "r_squared"
    TRACKING_ERROR = "tracking_error"
    INFORMATION_RATIO = "information_ratio"

    # Kelly and trade-edge metrics
    KELLY_FRACTION = "kelly_fraction"
    HALF_KELLY = "half_kelly"
    WIN_RATE = "win_rate"
    AVG_WIN = "avg_win"
    AVG_LOSS = "avg_loss"
    PAYOFF_RATIO = "payoff_ratio"
    EDGE = "edge"
    RISK_OF_RUIN_FULL_KELLY = "risk_of_ruin_full_kelly"
    RISK_OF_RUIN_HALF_KELLY = "risk_of_ruin_half_kelly"

    # Regime and surface metrics
    REGIME_SHARPES = "regime_sharpes"
    REGIME_FRAC = "regime_frac"
    OVERALL_SHARPE = "overall_sharpe"
    WORST_REGIME_SHARPE = "worst_regime_sharpe"
    ROBUSTNESS_RATIO = "robustness_ratio"
    FRAC_POSITIVE = "frac_positive"
    FRAC_ABOVE_HALF = "frac_above_half"
    PLATEAU_SCORE = "plateau_score"
    CV_NEIGHBORS = "cv_neighbors"
    PEAK_TO_NEIGHBOR = "peak_to_neighbor"
    SOBOL_FIRST = "sobol_first"
    MARGINAL_RANGE = "marginal_range"
    CONFIDENCE = "confidence"

    def label(self) -> str:
        """Return a human-readable display label."""
        special_words = {
            "acf": "ACF",
            "acf1": "ACF1",
            "bps": "Bps",
            "ci": "CI",
            "cv": "CV",
            "dsr": "DSR",
            "is": "IS",
            "kelly": "Kelly",
            "ljung": "Ljung",
            "oos": "OOS",
            "pbo": "PBO",
            "pnl": "PnL",
            "prob": "Probability",
            "psr": "PSR",
            "sr0": "SR0",
            "sr0_star": "SR0*",
            "std": "Std",
            "trl": "TRL",
            "var": "Variance",
            "wfe": "WFE",
        }
        return " ".join(
            special_words.get(part, part.capitalize()) for part in self.value.split("_")
        )

    def is_probability_metric(self) -> bool:
        """Return whether this metric is a probability or fraction."""
        return self in {
            ValidationMetricKey.UNBIASED_PVALUE,
            ValidationMetricKey.UNBIASED_PVALUES,
            ValidationMetricKey.SOLO_PVALUE,
            ValidationMetricKey.SOLO_PVALUES,
            ValidationMetricKey.STEPWISE_PVALUE,
            ValidationMetricKey.STEPWISE_PVALUES,
            ValidationMetricKey.PBO,
            ValidationMetricKey.PBOS,
            ValidationMetricKey.PSR,
            ValidationMetricKey.DSR,
            ValidationMetricKey.BEST_DSR,
            ValidationMetricKey.FRAC_OOS_POSITIVE,
            ValidationMetricKey.FRAC_OOS_PROFITABLE,
            ValidationMetricKey.FRAC_POSITIVE,
            ValidationMetricKey.FRAC_ABOVE_HALF,
            ValidationMetricKey.PLATEAU_SCORE,
            ValidationMetricKey.TERMINAL_PNL_PERCENTILE,
            ValidationMetricKey.MAX_DRAWDOWN_PERCENTILE,
            ValidationMetricKey.WIN_RATE,
            ValidationMetricKey.REGIME_FRAC,
            ValidationMetricKey.CONFIDENCE,
        }


LEGACY_ALIASES: dict[str, ValidationMetricKey] = {
    "acf_1": ValidationMetricKey.ACF1,
    "min_track_record": ValidationMetricKey.MIN_TRL,
    "prob_overfit": ValidationMetricKey.PBO,
}

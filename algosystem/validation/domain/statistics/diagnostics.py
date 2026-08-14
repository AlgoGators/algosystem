"""
Pre-test diagnostics for permutation-based overfitting detection.
Detects conditions that can invalidate the permutation test.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AutocorrelationDiagnostic:
    """Results of autocorrelation check on a returns series."""

    acf_1: float  # First-order autocorrelation
    acf_values: np.ndarray  # ACF at lags 1..max_lag
    ljung_box_stat: float  # Ljung-Box Q statistic
    ljung_box_pvalue: float  # Ljung-Box p-value
    has_autocorrelation: bool  # True if significant at given level
    recommended_shuffle: str  # 'complete', 'cyclic', or 'block'
    warning_message: str  # Human-readable warning (empty if clean)


def check_autocorrelation(
    returns: np.ndarray,
    max_lag: int = 10,
    significance: float = 0.05,
) -> AutocorrelationDiagnostic:
    """
    Check returns series for autocorrelation that would invalidate
    a complete-shuffle permutation test.

    Uses Ljung-Box test and individual ACF values.
    """
    # Compute ACF at each lag
    n = len(returns)
    mean = np.mean(returns)
    demeaned = returns - mean
    var = np.sum(demeaned**2) / n

    acf_values = np.empty(max_lag)
    for lag in range(1, max_lag + 1):
        if lag >= n:
            acf_values[lag - 1] = 0.0
        else:
            acf_values[lag - 1] = np.sum(demeaned[: n - lag] * demeaned[lag:]) / (n * var)

    acf_1 = acf_values[0]

    # Ljung-Box Q statistic: Q = n*(n+2) * sum(acf_k^2 / (n-k))
    q_stat = 0.0
    for k in range(1, max_lag + 1):
        if k < n:
            q_stat += acf_values[k - 1] ** 2 / (n - k)
    q_stat *= n * (n + 2)

    # Q ~ chi-squared with max_lag degrees of freedom
    # Compute p-value using chi-squared survival function
    # Use scipy if available, else approximate
    try:
        from scipy.stats import chi2

        lb_pvalue = chi2.sf(q_stat, df=max_lag)
    except ImportError:
        # Rough approximation: for large df, chi2 ~ Normal(df, 2*df)
        z = (q_stat - max_lag) / np.sqrt(2 * max_lag)
        lb_pvalue = 0.5 * (1 - np.tanh(z * 0.7))  # crude approx

    has_ac = lb_pvalue < significance

    # Also check if any individual ACF exceeds 2/sqrt(n) (95% band)
    acf_threshold = 2.0 / np.sqrt(n)
    significant_lags = np.where(np.abs(acf_values) > acf_threshold)[0] + 1

    # Recommendation logic
    if not has_ac and len(significant_lags) == 0:
        recommended = "complete"
        warning = ""
    elif has_ac and abs(acf_1) > 0.1:
        recommended = "block"
        warning = (
            f"WARNING: Significant autocorrelation detected "
            f"(Ljung-Box p={lb_pvalue:.4f}, ACF(1)={acf_1:.4f}). "
            f"Complete shuffle will produce anti-conservative p-values. "
            f"Using 'block' shuffle is recommended. "
            f"Significant ACF at lags: {significant_lags.tolist()}"
        )
    else:
        recommended = "cyclic"
        warning = (
            f"WARNING: Mild autocorrelation detected "
            f"(Ljung-Box p={lb_pvalue:.4f}, ACF(1)={acf_1:.4f}). "
            f"Consider using 'cyclic' or 'block' shuffle instead of 'complete'. "
            f"Significant ACF at lags: {significant_lags.tolist()}"
        )

    return AutocorrelationDiagnostic(
        acf_1=float(acf_1),
        acf_values=acf_values,
        ljung_box_stat=float(q_stat),
        ljung_box_pvalue=float(lb_pvalue),
        has_autocorrelation=has_ac,
        recommended_shuffle=recommended,
        warning_message=warning,
    )

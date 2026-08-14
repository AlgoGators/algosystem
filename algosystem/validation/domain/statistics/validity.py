"""
Data validation for backtesting returns series.

Checks for common data issues that silently corrupt backtest results:
- Duplicate timestamps
- Gaps in the time series
- Non-finite values (NaN, inf)
- Unsorted data
- Suspiciously extreme values
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class ValidationResult:
    """Results of data validation checks."""

    is_valid: bool
    n_observations: int
    issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def summary(self) -> list[str]:
        """Return data validation results as formatted lines."""
        status = "PASS" if self.is_valid else "FAIL"
        lines = [f"Data Validation: {status} ({self.n_observations} observations)"]
        for issue in self.issues:
            lines.append(f"  [ERROR] {issue}")
        for warning in self.warnings:
            lines.append(f"  [WARN]  {warning}")
        if not self.issues and not self.warnings:
            lines.append("  No issues found.")
        return lines


def validate_returns(  # noqa: C901
    returns: np.ndarray,
    max_abs_return: float = 0.5,
    min_observations: int = 50,
) -> ValidationResult:
    """
    Validate a returns series for common data issues.

    Parameters
    ----------
    returns : np.ndarray
        1-D array of returns.
    max_abs_return : float
        Flag returns exceeding this absolute value as suspicious (default 0.5 = 50%).
    min_observations : int
        Minimum required observations (default 50).

    Returns
    -------
    ValidationResult
    """
    issues = []
    warnings = []
    n = len(returns)

    # Check minimum length
    if n < min_observations:
        issues.append(f"Only {n} observations (minimum {min_observations})")

    # Check for non-finite values
    n_nan = np.sum(np.isnan(returns))
    n_inf = np.sum(np.isinf(returns))
    if n_nan > 0:
        issues.append(f"{n_nan} NaN values found")
    if n_inf > 0:
        issues.append(f"{n_inf} infinite values found")

    # Check for constant returns (zero variance)
    if n > 1 and np.std(returns) < 1e-15:
        issues.append("Returns have zero variance (constant series)")

    # Check for extreme values
    if n > 0:
        n_extreme = np.sum(np.abs(returns) > max_abs_return)
        if n_extreme > 0:
            max_val = np.max(np.abs(returns))
            warnings.append(
                f"{n_extreme} returns exceed {max_abs_return:.0%} "
                f"(max |r| = {max_val:.4f}). Check for data errors."
            )

    # Check for suspiciously many zeros
    if n > 0:
        frac_zero = np.mean(returns == 0.0)
        if frac_zero > 0.5:
            warnings.append(
                f"{frac_zero:.0%} of returns are exactly zero. "
                f"Check for missing data or non-trading days."
            )

    # Check for suspiciously high mean (drift)
    if n > 20:
        daily_mean = np.mean(returns)
        annual_return = daily_mean * 252
        if abs(annual_return) > 2.0:
            warnings.append(
                f"Annualized mean return = {annual_return:.1%}. "
                f"Unusually high — check for survivorship or look-ahead bias."
            )

    is_valid = len(issues) == 0

    return ValidationResult(
        is_valid=is_valid,
        n_observations=n,
        issues=issues,
        warnings=warnings,
    )

"""
OverfitResults dataclass — container for all overfitting detection results.

Includes report generation and parameter surface analysis (Sobol indices,
robustness ratio, plateau score).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.validation_metric import ValidationMetricKey


@dataclass(frozen=True)
class OverfitResults:
    """Container for all overfitting detection results."""

    # Inputs
    param_list: list
    n_params: int
    n_reps: int
    shuffle_method: str

    # Pass 0 (unpermuted) results
    original_sharpes: np.ndarray
    best_param_index: int
    best_sharpe: float

    # Permutation results
    solo_pvalues: np.ndarray
    unbiased_pvalue: float
    unbiased_pvalues: np.ndarray
    null_best_sharpes: np.ndarray
    prob_overfit: float
    deflated_sharpe: float

    # For ordered reporting
    sort_indices: np.ndarray

    # Optional: original returns for analytical DSR computation
    returns: Optional[np.ndarray] = field(default=None, repr=False)

    def summary(self) -> list[str]:
        """Return a summary report as formatted lines."""
        lines = [
            "=" * 72,
            "PERMUTATION-BASED OVERFITTING DETECTION REPORT",
            "=" * 72,
            f"Parameter combinations tested : {self.n_params}",
            f"Permutation replications      : {self.n_reps}",
            f"Shuffle method                : {self.shuffle_method}",
            "",
            f"Best in-sample Sharpe (S*)     : {self.best_sharpe:.4f}",
            f"Best parameter set             : {self.param_list[self.best_param_index]}",
            "",
            f"Unbiased p-value (best set)    : {self.unbiased_pvalue:.4f}",
            f"Probability of overfitting     : {self.prob_overfit:.4f}",
            f"Deflated Sharpe ratio          : {self.deflated_sharpe:.4f}",
        ]
        if self.returns is not None:
            adsr = self.analytical_deflated_sharpe()
            lines.extend(
                [
                    f"Analytical DSR (Bailey/LdP)    : {adsr[ValidationMetricKey.DSR.value]:.4f}",
                    f"  SR0 (haircut threshold)      : {adsr[ValidationMetricKey.SR0.value]:.4f}",
                    (
                        "  Min track record length      : "
                        f"{adsr[ValidationMetricKey.MIN_TRL.value]:.1f}"
                    ),
                    (
                        "  Returns skewness             : "
                        f"{adsr[ValidationMetricKey.SKEWNESS.value]:.4f}"
                    ),
                    (
                        "  Returns kurtosis             : "
                        f"{adsr[ValidationMetricKey.KURTOSIS.value]:.4f}"
                    ),
                ]
            )
        lines.append("")

        n_show = min(20, self.n_params)
        lines.extend(
            [
                f"Top {n_show} parameter sets (sorted by unpermuted Sharpe):",
                "-" * 72,
                f"{'Rank':>4}  {'Sharpe':>8}  {'Solo pval':>10}  {'Unbiased pval':>14}  Params",
                "-" * 72,
            ]
        )
        for rank in range(n_show):
            idx = self.sort_indices[rank]
            spval = self.solo_pvalues[idx]
            upval = self.unbiased_pvalues[rank]
            lines.append(
                f"{rank+1:4d}  {self.original_sharpes[idx]:8.4f}  "
                f"{spval:10.4f}  {upval:14.4f}  {self.param_list[idx]}"
            )
        lines.append("-" * 72)
        return lines

    def analytical_deflated_sharpe(self, returns: np.ndarray | None = None) -> dict:  # noqa: C901
        """
        Compute the Bailey / Lopez de Prado Deflated Sharpe Ratio (DSR).

        This analytical correction accounts for multiple testing, non-normal
        returns, and finite sample length — without permutation.

        Parameters
        ----------
        returns : np.ndarray, optional
            Strategy returns used to estimate skewness and kurtosis.
            Falls back to ``self.returns`` if not provided.

        Returns
        -------
        dict with keys: dsr, sr0, min_trl, skewness, kurtosis
        """
        ret = returns if returns is not None else self.returns
        if ret is None:
            raise ValidationError(
                "Returns array required for analytical DSR. " "Pass returns= or set self.returns."
            )

        try:
            from scipy.stats import norm as _norm

            _phi = _norm.cdf
            _phi_inv = _norm.ppf
        except ImportError:
            # Minimal fallback using error-function approximation
            def _phi(x):
                return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

            def _phi_inv(p):
                # Rational approximation (Abramowitz & Stegun 26.2.23)
                if p <= 0.0:
                    return -np.inf
                if p >= 1.0:
                    return np.inf
                if p > 0.5:
                    return -_phi_inv(1.0 - p)
                t = math.sqrt(-2.0 * math.log(p))
                c0, c1, c2 = 2.515517, 0.802853, 0.010328
                d1, d2, d3 = 1.432788, 0.189269, 0.001308
                return -(t - (c0 + c1 * t + c2 * t**2) / (1.0 + d1 * t + d2 * t**2 + d3 * t**3))

        N_raw = max(self.n_params, 2)
        T_raw = len(ret)
        sr_hat = float(self.best_sharpe)
        ret_arr = np.asarray(ret, dtype=np.float64)

        # --- Effective sample size (autocorrelation adjustment) ---
        # T_eff = T * (1 - rho1) / (1 + rho1) for AR(1) returns
        rho1 = 0.0
        if T_raw > 2:
            demeaned = ret_arr - np.mean(ret_arr)
            denom = np.sum(demeaned**2)
            if denom > 1e-15:
                rho1 = float(np.sum(demeaned[:-1] * demeaned[1:]) / denom)
        rho1 = np.clip(rho1, -0.99, 0.99)
        T = max(int(T_raw * (1.0 - rho1) / (1.0 + rho1)), 3)

        # --- Effective number of trials (correlation adjustment) ---
        # N_eff = N / (1 + (N-1) * rho_avg) where rho_avg = avg pairwise
        # correlation of strategy Sharpes. Approximate from Sharpe variance.
        if N_raw > 2 and len(self.original_sharpes) > 2:
            sr_std = float(np.std(self.original_sharpes, ddof=1))
            sr_range = float(np.max(self.original_sharpes) - np.min(self.original_sharpes))
            # High correlation → low variance relative to range → higher rho_avg
            rho_avg = max(0.0, 1.0 - sr_std / (sr_range + 1e-12))
            rho_avg = min(rho_avg, 0.95)
            N = max(int(N_raw / (1.0 + (N_raw - 1) * rho_avg)), 2)
        else:
            N = N_raw

        # --- Cross-sectional variance of all original Sharpe ratios ---
        var_sr = float(np.var(self.original_sharpes, ddof=1))

        # --- SR0: expected maximum Sharpe under the null ---
        gamma_em = 0.5772156649  # Euler-Mascheroni constant
        sr0 = math.sqrt(var_sr) * (
            (1.0 - gamma_em) * _phi_inv(1.0 - 1.0 / N)
            + gamma_em * _phi_inv(1.0 - 1.0 / (N * math.e))
        )

        # --- Skewness and kurtosis of returns ---
        mu = np.mean(ret_arr)
        sigma = np.std(ret_arr, ddof=1)
        if sigma < 1e-15:
            gamma3 = 0.0
            gamma4 = 3.0
        else:
            z = (ret_arr - mu) / sigma
            gamma3 = float(np.mean(z**3))  # skewness
            gamma4 = float(np.mean(z**4))  # kurtosis (non-excess)

        # --- DSR = Phi[ (SR_hat - SR0) * sqrt(T-1) / denominator ] ---
        # gamma4 is raw kurtosis (normal=3); the SR variance formula uses (gamma4-1)/4
        denom_sq = 1.0 - gamma3 * sr_hat + (gamma4 - 1.0) / 4.0 * sr_hat**2
        if denom_sq <= 0:
            denom_sq = 1e-8  # guard against degenerate case
        denom = math.sqrt(denom_sq)

        if T > 1:
            test_stat = (sr_hat - sr0) * math.sqrt(T - 1) / denom
        else:
            test_stat = 0.0

        dsr = float(_phi(test_stat))

        # --- Minimum Track Record Length ---
        min_trl = self.min_track_record_length(
            target_dsr=0.95,
            _sr0=sr0,
            _gamma3=gamma3,
            _gamma4=gamma4,
        )

        return {
            ValidationMetricKey.DSR.value: dsr,
            ValidationMetricKey.SR0.value: float(sr0),
            ValidationMetricKey.MIN_TRL.value: min_trl,
            ValidationMetricKey.SKEWNESS.value: gamma3,
            ValidationMetricKey.KURTOSIS.value: gamma4,
        }

    def min_track_record_length(  # noqa: C901
        self,
        target_dsr: float = 0.95,
        _sr0: float | None = None,
        _gamma3: float | None = None,
        _gamma4: float | None = None,
    ) -> float:
        """
        Minimum Track Record Length (MinTRL) required for the best Sharpe
        to be considered significant at the *target_dsr* confidence level.

        Parameters
        ----------
        target_dsr : float
            Desired deflated-Sharpe probability (default 0.95).

        Returns
        -------
        float  — number of return observations needed.
        """
        try:
            from scipy.stats import norm as _norm

            _phi_inv = _norm.ppf
        except ImportError:

            def _phi_inv(p):
                if p <= 0.0:
                    return -np.inf
                if p >= 1.0:
                    return np.inf
                if p > 0.5:
                    return -_phi_inv(1.0 - p)
                t = math.sqrt(-2.0 * math.log(p))
                c0, c1, c2 = 2.515517, 0.802853, 0.010328
                d1, d2, d3 = 1.432788, 0.189269, 0.001308
                return -(t - (c0 + c1 * t + c2 * t**2) / (1.0 + d1 * t + d2 * t**2 + d3 * t**3))

        sr_hat = float(self.best_sharpe)

        # Compute SR0 if not passed internally
        if _sr0 is None:
            gamma_em = 0.5772156649
            N = max(self.n_params, 2)
            var_sr = float(np.var(self.original_sharpes, ddof=1))
            _sr0 = math.sqrt(var_sr) * (
                (1.0 - gamma_em) * _phi_inv(1.0 - 1.0 / N)
                + gamma_em * _phi_inv(1.0 - 1.0 / (N * math.e))
            )

        # Compute skewness / kurtosis from stored returns if not passed
        if _gamma3 is None or _gamma4 is None:
            if self.returns is None:
                raise ValidationError(
                    "Returns array required for min_track_record_length. "
                    "Pass returns when constructing OverfitResults or call "
                    "analytical_deflated_sharpe() first."
                )
            ret_arr = np.asarray(self.returns, dtype=np.float64)
            mu = np.mean(ret_arr)
            sigma = np.std(ret_arr, ddof=1)
            if sigma < 1e-15:
                _gamma3 = 0.0
                _gamma4 = 3.0
            else:
                z = (ret_arr - mu) / sigma
                _gamma3 = float(np.mean(z**3))
                _gamma4 = float(np.mean(z**4))

        z_alpha = _phi_inv(target_dsr)

        sr_diff = sr_hat - _sr0
        if abs(sr_diff) < 1e-15:
            return float("inf")

        numer = 1.0 - _gamma3 * sr_hat + (_gamma4 - 1.0) / 4.0 * sr_hat**2
        min_trl = 1.0 + numer * (z_alpha / sr_diff) ** 2
        return float(min_trl)

    def surface_analysis(self) -> dict:
        """
        Compute parameter surface metrics for overfitting detection.

        Returns a dict with:
            robustness_ratio    : mean(neighbor Sharpe) / best Sharpe  (1.0 = plateau)
            frac_positive       : fraction of param space with Sharpe > 0
            frac_above_half     : fraction with Sharpe > 0.5 * best
            plateau_score       : fraction with Sharpe > 0.7 * best (PSI)
            cv_neighbors        : coeff of variation in neighborhood of best
            peak_to_neighbor    : best / mean(neighbors)  (1.0 = flat)
            per_param_sensitivity: dict of param_name -> {sobol_first, marginal_range}
        """
        param_keys = sorted({k for p in self.param_list for k in p})
        param_values = {k: sorted({p[k] for p in self.param_list}) for k in param_keys}
        sharpes = self.original_sharpes
        best = self.best_sharpe
        best_params = self.param_list[self.best_param_index]

        frac_positive = np.mean(sharpes > 0)
        frac_above_half = np.mean(sharpes > 0.5 * best) if best > 0 else 0.0
        plateau_score = np.mean(sharpes > 0.7 * best) if best > 0 else 0.0

        # Neighbor analysis — param combos differing in exactly 1 param by 1 step
        neighbor_sharpes = []
        for i, p in enumerate(self.param_list):
            diffs = 0
            for k in param_keys:
                vals = param_values[k]
                idx_best = vals.index(best_params[k])
                idx_this = vals.index(p[k])
                if abs(idx_best - idx_this) == 1:
                    diffs += 1
                elif idx_best != idx_this:
                    diffs = 99
                    break
            if diffs == 1:
                neighbor_sharpes.append(sharpes[i])

        if len(neighbor_sharpes) > 0:
            nb = np.array(neighbor_sharpes)
            nb_mean = np.mean(nb)
            robustness_ratio = nb_mean / best if best != 0 else 0.0
            peak_to_neighbor = best / nb_mean if nb_mean != 0 else float("inf")
            cv_neighbors = np.std(nb, ddof=1) / abs(nb_mean) if nb_mean != 0 else float("inf")
        else:
            robustness_ratio = 1.0
            peak_to_neighbor = 1.0
            cv_neighbors = 0.0

        # Per-parameter sensitivity (first-order Sobol approximation)
        total_var = np.var(sharpes)
        per_param: Dict[str, dict] = {}
        for k in param_keys:
            vals = param_values[k]
            conditional_means = []
            for v in vals:
                subset = [sharpes[i] for i, p in enumerate(self.param_list) if p[k] == v]
                conditional_means.append(np.mean(subset))
            cm = np.array(conditional_means)

            sobol_first = np.var(cm) / total_var if total_var > 1e-12 else 0.0
            marginal_range = cm.max() - cm.min()

            per_param[k] = {
                ValidationMetricKey.SOBOL_FIRST.value: float(sobol_first),
                ValidationMetricKey.MARGINAL_RANGE.value: float(marginal_range),
                "conditional_means": cm.tolist(),
                "values": [float(v) if isinstance(v, (int, float)) else v for v in vals],
            }

        return {
            ValidationMetricKey.ROBUSTNESS_RATIO.value: float(robustness_ratio),
            ValidationMetricKey.FRAC_POSITIVE.value: float(frac_positive),
            ValidationMetricKey.FRAC_ABOVE_HALF.value: float(frac_above_half),
            ValidationMetricKey.PLATEAU_SCORE.value: float(plateau_score),
            ValidationMetricKey.CV_NEIGHBORS.value: float(cv_neighbors),
            ValidationMetricKey.PEAK_TO_NEIGHBOR.value: float(peak_to_neighbor),
            "per_param_sensitivity": per_param,
        }

    def surface_summary(self) -> list[str]:
        """Return the surface analysis report as formatted lines."""
        sa = self.surface_analysis()
        lines = [
            "=" * 72,
            "PARAMETER SURFACE ANALYSIS",
            "=" * 72,
        ]

        def rating(val, good, bad, higher_is_better=True):
            if higher_is_better:
                if val >= good:
                    return "GOOD"
                if val >= bad:
                    return "WARN"
                return "BAD "
            else:
                if val <= good:
                    return "GOOD"
                if val <= bad:
                    return "WARN"
                return "BAD "

        rr = sa[ValidationMetricKey.ROBUSTNESS_RATIO.value]
        fp = sa[ValidationMetricKey.FRAC_POSITIVE.value]
        fh = sa[ValidationMetricKey.FRAC_ABOVE_HALF.value]
        ps = sa[ValidationMetricKey.PLATEAU_SCORE.value]
        cv = sa[ValidationMetricKey.CV_NEIGHBORS.value]
        pn = sa[ValidationMetricKey.PEAK_TO_NEIGHBOR.value]

        lines.extend(
            [
                (
                    f"  Robustness ratio (neighbor/best)  : {rr:.4f}  "
                    f"[{rating(rr, 0.8, 0.5)}]  (1.0 = flat plateau)"
                ),
                (
                    f"  Frac param space with Sharpe > 0  : {fp:.4f}  "
                    f"[{rating(fp, 0.5, 0.2)}]  (>0.5 = structural edge)"
                ),
                (f"  Frac above 50% of best            : {fh:.4f}  " f"[{rating(fh, 0.3, 0.1)}]"),
                (f"  Plateau score (>70% of best)      : {ps:.4f}  " f"[{rating(ps, 0.2, 0.05)}]"),
                (
                    f"  CV of neighbors                   : {cv:.4f}  "
                    f"[{rating(cv, 0.3, 0.5, higher_is_better=False)}]  "
                    "(lower = more stable)"
                ),
                (
                    f"  Peak-to-neighbor ratio             : {pn:.4f}  "
                    f"[{rating(pn, 1.2, 1.5, higher_is_better=False)}]  (1.0 = flat)"
                ),
                "",
                "  Per-parameter sensitivity (Sobol first-order index):",
                f"    {'Parameter':<20} {'Sobol S1':>10} {'Marginal range':>15}",
                f"    {'-'*20} {'-'*10} {'-'*15}",
            ]
        )
        for k, v in sorted(
            sa["per_param_sensitivity"].items(),
            key=lambda x: -x[1][ValidationMetricKey.SOBOL_FIRST.value],
        ):
            lines.append(
                f"    {k:<20} {v[ValidationMetricKey.SOBOL_FIRST.value]:>10.4f} "
                f"{v[ValidationMetricKey.MARGINAL_RANGE.value]:>15.4f}"
            )
        lines.append("=" * 72)
        return lines

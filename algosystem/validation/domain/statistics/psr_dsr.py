"""
Probabilistic Sharpe Ratio (PSR) and Deflated Sharpe Ratio (DSR).

Implements the gold-standard math from:
- Bailey & Lopez de Prado (2012): "The Sharpe Ratio Efficient Frontier"
- Bailey & Lopez de Prado (2014): "The Deflated Sharpe Ratio"
- jsharpe library conventions for multi-trial correction

Key concepts:
    PSR: Given an observed Sharpe ratio, what is the probability that the
         TRUE Sharpe exceeds a benchmark SR0? Accounts for non-normal returns
         (skewness, kurtosis) and finite sample size.

    DSR: PSR but with SR0 set to the expected maximum Sharpe under the null
         (i.e., what you'd expect the best of N random strategies to achieve).
         This is the core p-hacking correction.

    Trial Tracker: VARRD-inspired system that logs every test and auto-raises
         the significance threshold the more you test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from algosystem.validation.domain.validation_metric import ValidationMetricKey

# ---------------------------------------------------------------------------
# Normal CDF / inverse CDF (with scipy fallback)
# ---------------------------------------------------------------------------


def _phi(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _phi_inv(p: float) -> float:
    """Standard normal inverse CDF (rational approximation)."""
    if p <= 0.0:
        return -float("inf")
    if p >= 1.0:
        return float("inf")
    if p > 0.5:
        return -_phi_inv(1.0 - p)
    t = math.sqrt(-2.0 * math.log(p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    return -(t - (c0 + c1 * t + c2 * t**2) / (1.0 + d1 * t + d2 * t**2 + d3 * t**3))


# Try scipy for better precision
try:
    from scipy.stats import norm as _norm

    _phi = _norm.cdf
    _phi_inv = _norm.ppf
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Return statistics helper
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReturnStats:
    """Descriptive statistics of a returns series relevant to PSR/DSR."""

    n_obs: int
    mean: float
    std: float
    sharpe: float  # annualized
    skewness: float  # gamma3
    kurtosis: float  # gamma4 (non-excess, so normal = 3.0)
    acf1: float  # first-order autocorrelation
    n_effective: int  # autocorrelation-adjusted sample size


def compute_return_stats(
    returns: np.ndarray,
    annualize: float = 252.0,
) -> ReturnStats:
    """Compute all statistics needed for PSR/DSR from a returns array."""
    ret = np.asarray(returns, dtype=np.float64)
    n = len(ret)
    mu = float(np.mean(ret))
    sigma = float(np.std(ret, ddof=1))

    if sigma < 1e-15:
        return ReturnStats(
            n_obs=n,
            mean=mu,
            std=sigma,
            sharpe=0.0,
            skewness=0.0,
            kurtosis=3.0,
            acf1=0.0,
            n_effective=n,
        )

    sharpe = (mu / sigma) * math.sqrt(annualize)
    z = (ret - mu) / sigma
    gamma3 = float(np.mean(z**3))
    gamma4 = float(np.mean(z**4))

    # First-order autocorrelation
    demeaned = ret - mu
    denom = np.sum(demeaned**2)
    acf1 = float(np.sum(demeaned[:-1] * demeaned[1:]) / denom) if denom > 1e-15 and n > 2 else 0.0
    acf1 = np.clip(acf1, -0.99, 0.99)

    # Effective sample size (Lo 2002 autocorrelation adjustment)
    # Cap at n to avoid inflated sample size for mean-reverting series
    n_eff = max(3, min(n, int(n * (1.0 - acf1) / (1.0 + acf1))))

    return ReturnStats(
        n_obs=n,
        mean=mu,
        std=sigma,
        sharpe=sharpe,
        skewness=gamma3,
        kurtosis=gamma4,
        acf1=acf1,
        n_effective=n_eff,
    )


# ---------------------------------------------------------------------------
# Probabilistic Sharpe Ratio (PSR)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PSRResult:
    """Result of Probabilistic Sharpe Ratio test."""

    psr: float  # P(SR_true > SR0) given observed data
    sr_hat: float  # observed annualized Sharpe
    sr0: float  # benchmark Sharpe (null hypothesis)
    test_statistic: float  # z-score
    n_obs: int
    n_effective: int
    skewness: float
    kurtosis: float
    is_significant: bool  # PSR > threshold (default 0.95)
    threshold: float

    def summary(self) -> list[str]:
        """Return the PSR report as formatted lines."""
        status = "SIGNIFICANT" if self.is_significant else "NOT SIGNIFICANT"
        return [
            f"Probabilistic Sharpe Ratio [{status}]",
            f"  PSR             : {self.psr:.4f} (threshold: {self.threshold:.2f})",
            f"  Observed SR     : {self.sr_hat:.4f}",
            f"  Benchmark SR0   : {self.sr0:.4f}",
            f"  Test statistic  : {self.test_statistic:.4f}",
            f"  Observations    : {self.n_obs} (effective: {self.n_effective})",
            f"  Skewness        : {self.skewness:.4f}",
            f"  Kurtosis        : {self.kurtosis:.4f}",
        ]


def probabilistic_sharpe_ratio(
    returns: np.ndarray,
    sr0: float = 0.0,
    annualize: float = 252.0,
    threshold: float = 0.95,
) -> PSRResult:
    """
    Compute PSR: the probability that the true Sharpe exceeds sr0.

    This is the non-normal-corrected version from Bailey & LdP (2012).
    Unlike a simple t-test on Sharpe, this accounts for skewness and
    kurtosis of returns, which matter enormously for real strategies.

    Parameters
    ----------
    returns : np.ndarray
        Strategy returns (daily).
    sr0 : float
        Benchmark Sharpe ratio to test against (default 0 = "is SR > 0?").
    annualize : float
        Annualization factor.
    threshold : float
        PSR threshold for significance (default 0.95).

    Returns
    -------
    PSRResult
    """
    stats = compute_return_stats(returns, annualize)
    sr_hat = stats.sharpe
    T = stats.n_effective
    gamma3 = stats.skewness
    gamma4 = stats.kurtosis

    # PSR = Phi[ (sr_hat - sr0) * sqrt(T-1) / sqrt(1 - gamma3*sr_hat + (gamma4-1)/4 * sr_hat^2) ]
    denom_sq = 1.0 - gamma3 * sr_hat + (gamma4 - 1.0) / 4.0 * sr_hat**2
    if denom_sq <= 0:
        denom_sq = 1e-8
    denom = math.sqrt(denom_sq)

    if T > 1:
        z = (sr_hat - sr0) * math.sqrt(T - 1) / denom
    else:
        z = 0.0

    psr = float(_phi(z))

    return PSRResult(
        psr=psr,
        sr_hat=sr_hat,
        sr0=sr0,
        test_statistic=z,
        n_obs=stats.n_obs,
        n_effective=T,
        skewness=gamma3,
        kurtosis=gamma4,
        is_significant=psr >= threshold,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio (DSR)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DSRResult:
    """Result of Deflated Sharpe Ratio test."""

    dsr: float  # P(SR_true > SR0*) where SR0* = E[max SR under null]
    sr_hat: float  # observed best Sharpe
    sr0_star: float  # expected max Sharpe under null (the "haircut")
    n_trials: int  # number of strategies/param combos tested
    n_trials_effective: int  # correlation-adjusted trial count
    test_statistic: float
    n_obs: int
    n_effective: int
    skewness: float
    kurtosis: float
    min_track_record: float  # MinTRL for DSR > 0.95
    is_significant: bool
    threshold: float
    var_sr: float  # cross-sectional variance of Sharpe ratios

    def summary(self) -> list[str]:
        """Return the DSR report as formatted lines."""
        status = "SIGNIFICANT" if self.is_significant else "LIKELY P-HACKED"
        return [
            f"Deflated Sharpe Ratio [{status}]",
            f"  DSR             : {self.dsr:.4f} (threshold: {self.threshold:.2f})",
            f"  Best observed SR: {self.sr_hat:.4f}",
            f"  SR0* (haircut)  : {self.sr0_star:.4f}",
            f"  Trials tested   : {self.n_trials} (effective: {self.n_trials_effective})",
            f"  Min track record: {self.min_track_record:.0f} observations",
            f"  Test statistic  : {self.test_statistic:.4f}",
            f"  Skewness        : {self.skewness:.4f}",
            f"  Kurtosis        : {self.kurtosis:.4f}",
        ]


def deflated_sharpe_ratio(
    returns: np.ndarray,
    n_trials: int,
    all_sharpes: np.ndarray | None = None,
    annualize: float = 252.0,
    threshold: float = 0.95,
    sr_hat: float | None = None,
) -> DSRResult:
    """
    Compute DSR: the probability that the best observed Sharpe exceeds
    what you'd expect the best of N random strategies to achieve.

    This is the core p-hacking test. If you tested 100 parameter combos
    and the best has SR=1.5, DSR tells you whether that 1.5 is significant
    AFTER accounting for the 100 trials.

    Parameters
    ----------
    returns : np.ndarray
        Returns of the best strategy (or the underlying return series).
    n_trials : int
        Total number of strategies / parameter combinations tested.
    all_sharpes : np.ndarray, optional
        Sharpe ratios of ALL tested strategies. Used to estimate
        cross-sectional variance and inter-strategy correlation.
        If None, assumes independent trials with variance estimated
        from returns.
    annualize : float
        Annualization factor.
    threshold : float
        DSR threshold for significance (default 0.95).
    sr_hat : float, optional
        Override the observed Sharpe (e.g., if returns are the underlying
        data, not the strategy returns).

    Returns
    -------
    DSRResult
    """
    stats = compute_return_stats(returns, annualize)
    if sr_hat is None:
        sr_hat = stats.sharpe
    T = stats.n_effective
    gamma3 = stats.skewness
    gamma4 = stats.kurtosis

    N_raw = max(n_trials, 2)

    # --- Effective number of trials (correlation adjustment) ---
    if all_sharpes is not None and len(all_sharpes) > 2:
        sr_std = float(np.std(all_sharpes, ddof=1))
        sr_range = float(np.max(all_sharpes) - np.min(all_sharpes))
        rho_avg = max(0.0, 1.0 - sr_std / (sr_range + 1e-12))
        rho_avg = min(rho_avg, 0.95)
        N_eff = max(int(N_raw / (1.0 + (N_raw - 1) * rho_avg)), 2)
        var_sr = float(np.var(all_sharpes, ddof=1))
    else:
        N_eff = N_raw
        # Estimate variance from the Sharpe standard error
        var_sr = (1.0 + 0.5 * sr_hat**2) / max(T, 1) if T > 0 else 1.0

    # --- SR0*: Expected maximum Sharpe under the null ---
    # Uses the Euler-Mascheroni approximation for E[max] of N iid normals
    gamma_em = 0.5772156649
    sr0_star = math.sqrt(var_sr) * (
        (1.0 - gamma_em) * _phi_inv(1.0 - 1.0 / N_eff)
        + gamma_em * _phi_inv(1.0 - 1.0 / (N_eff * math.e))
    )

    # --- DSR = Phi[ (sr_hat - sr0*) * sqrt(T-1) / denominator ] ---
    # Uses raw kurtosis gamma4 (normal=3.0); the SR variance formula is
    # Var(SR) ~ (1/T) * [1 - gamma3*SR + (gamma4-1)/4 * SR^2]
    denom_sq = 1.0 - gamma3 * sr_hat + (gamma4 - 1.0) / 4.0 * sr_hat**2
    if denom_sq <= 0:
        denom_sq = 1e-8
    denom = math.sqrt(denom_sq)

    if T > 1:
        z = (sr_hat - sr0_star) * math.sqrt(T - 1) / denom
    else:
        z = 0.0

    dsr = float(_phi(z))

    # --- MinTRL ---
    sr_diff = sr_hat - sr0_star
    if abs(sr_diff) > 1e-15:
        z_alpha = _phi_inv(threshold)
        numer = 1.0 - gamma3 * sr0_star + (gamma4 - 1.0) / 4.0 * sr0_star**2
        min_trl = 1.0 + numer * (z_alpha / sr_diff) ** 2
    else:
        min_trl = float("inf")

    return DSRResult(
        dsr=dsr,
        sr_hat=sr_hat,
        sr0_star=sr0_star,
        n_trials=N_raw,
        n_trials_effective=N_eff,
        test_statistic=z,
        n_obs=stats.n_obs,
        n_effective=T,
        skewness=gamma3,
        kurtosis=gamma4,
        min_track_record=float(min_trl),
        is_significant=dsr >= threshold,
        threshold=threshold,
        var_sr=var_sr,
    )


# ---------------------------------------------------------------------------
# Multi-strategy DSR batch (jsharpe-style)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchDSRResult:
    """Results from testing multiple strategies with proper multi-trial correction."""

    n_strategies: int
    n_significant: int
    results: list[DSRResult]
    best_strategy_idx: int
    best_dsr: float
    summary_table: list[dict]

    def summary(self) -> list[str]:
        """Return the batch DSR report as formatted lines."""
        lines = [
            "=" * 72,
            f"BATCH DEFLATED SHARPE RATIO ({self.n_strategies} strategies)",
            "=" * 72,
            f"Significant (DSR > 0.95): {self.n_significant}/{self.n_strategies}",
            f"Best DSR: {self.best_dsr:.4f} (strategy #{self.best_strategy_idx})",
            "",
            f"{'#':>3}  {'SR_hat':>8}  {'SR0*':>8}  {'DSR':>8}  {'Sig?':>5}  {'MinTRL':>8}",
            "-" * 52,
        ]
        for i, r in enumerate(self.results):
            sig = "YES" if r.is_significant else "no"
            mtrl = f"{r.min_track_record:.0f}" if r.min_track_record < 1e6 else "inf"
            marker = " <-- best" if i == self.best_strategy_idx else ""
            lines.append(
                f"{i:3d}  {r.sr_hat:8.4f}  {r.sr0_star:8.4f}  "
                f"{r.dsr:8.4f}  {sig:>5}  {mtrl:>8}{marker}"
            )
        lines.append("-" * 52)
        return lines


def batch_deflated_sharpe(
    returns_list: list[np.ndarray],
    annualize: float = 252.0,
    threshold: float = 0.95,
) -> BatchDSRResult:
    """
    Compute DSR for multiple strategies tested on the same data.

    Each strategy is penalized for the TOTAL number of strategies tested.
    This is the jsharpe-style workflow: test N strategies, see which survive
    the multiple-testing haircut.

    Parameters
    ----------
    returns_list : list of np.ndarray
        Returns for each strategy.
    annualize : float
        Annualization factor.
    threshold : float
        DSR significance threshold.

    Returns
    -------
    BatchDSRResult
    """
    n = len(returns_list)
    all_sharpes = np.array([compute_return_stats(r, annualize).sharpe for r in returns_list])

    results = []
    for i, ret in enumerate(returns_list):
        dsr = deflated_sharpe_ratio(
            returns=ret,
            n_trials=n,
            all_sharpes=all_sharpes,
            annualize=annualize,
            threshold=threshold,
            sr_hat=all_sharpes[i],
        )
        results.append(dsr)

    best_idx = int(np.argmax([r.dsr for r in results]))
    n_sig = sum(1 for r in results if r.is_significant)

    return BatchDSRResult(
        n_strategies=n,
        n_significant=n_sig,
        results=results,
        best_strategy_idx=best_idx,
        best_dsr=results[best_idx].dsr,
        summary_table=[
            {
                "strategy": i,
                ValidationMetricKey.SHARPE.value: r.sr_hat,
                ValidationMetricKey.DSR.value: r.dsr,
                "significant": r.is_significant,
            }
            for i, r in enumerate(results)
        ],
    )


# ---------------------------------------------------------------------------
# Trial Tracker (VARRD-inspired)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrialRecord:
    """Record of a single strategy test."""

    trial_id: int
    sharpe: float
    params: dict
    strategy_name: str
    timestamp: float  # time.time() when recorded
    psr: float  # PSR at time of recording
    dsr: float  # DSR at time of recording (updated as trials accumulate)
    significant_at_time: bool


class TrialTracker:
    """
    VARRD-inspired trial tracker.

    Logs every strategy test and automatically raises the significance
    threshold as more tests are run. Makes it nearly impossible to p-hack
    without the system flagging it.

    Usage:
        tracker = TrialTracker()
        for params in param_grid:
            sharpe = backtest(params, returns)
            record = tracker.record_trial(returns, sharpe, params, 'momentum')
            line = f"DSR after {tracker.n_trials} trials: {record.dsr:.4f}"
    """

    def __init__(self, annualize: float = 252.0, base_threshold: float = 0.95):
        self.annualize = annualize
        self.base_threshold = base_threshold
        self.trials: list[TrialRecord] = []
        self._trial_counter = 0
        self._return_stats: dict[int, ReturnStats] = {}  # trial_id -> stats

    @property
    def n_trials(self) -> int:
        return len(self.trials)

    @property
    def all_sharpes(self) -> np.ndarray:
        return np.array([t.sharpe for t in self.trials]) if self.trials else np.array([0.0])

    def record_trial(
        self,
        returns: np.ndarray,
        sharpe: float,
        params: dict,
        strategy_name: str = "",
    ) -> TrialRecord:
        """
        Record a new trial and compute its DSR against all prior trials.

        The more trials you've run, the higher SR0* becomes, making it
        harder for any single trial to be "significant."
        """
        import time

        self._trial_counter += 1

        # PSR against zero (does this strategy beat nothing?)
        stats = compute_return_stats(returns, self.annualize)
        psr_result = probabilistic_sharpe_ratio(
            returns,
            sr0=0.0,
            annualize=self.annualize,
        )

        # DSR against all trials so far (including this one)
        # Temporarily add this sharpe to compute the collective DSR
        temp_sharpes = np.append(self.all_sharpes, sharpe) if self.trials else np.array([sharpe])

        dsr_result = deflated_sharpe_ratio(
            returns=returns,
            n_trials=self._trial_counter,
            all_sharpes=temp_sharpes,
            annualize=self.annualize,
            threshold=self.base_threshold,
            sr_hat=sharpe,
        )

        record = TrialRecord(
            trial_id=self._trial_counter,
            sharpe=sharpe,
            params=params,
            strategy_name=strategy_name,
            timestamp=time.time(),
            psr=psr_result.psr,
            dsr=dsr_result.dsr,
            significant_at_time=dsr_result.is_significant,
        )
        self.trials.append(record)
        self._return_stats[self._trial_counter] = stats
        return record

    def current_sr0_star(self) -> float:
        """Current expected-max-Sharpe threshold given all trials so far."""
        if self.n_trials < 2:
            return 0.0
        gamma_em = 0.5772156649
        var_sr = float(np.var(self.all_sharpes, ddof=1))
        N = self.n_trials
        return math.sqrt(var_sr) * (
            (1.0 - gamma_em) * _phi_inv(1.0 - 1.0 / N)
            + gamma_em * _phi_inv(1.0 - 1.0 / (N * math.e))
        )

    def survivors(self, threshold: float | None = None) -> list[TrialRecord]:
        """Return trials that are still significant after all accumulated tests."""
        th = threshold or self.base_threshold
        if self.n_trials < 2:
            return list(self.trials)

        # Use stored return stats for each trial so that skewness,
        # kurtosis, and effective sample size are from real data
        survivors = []
        for trial in self.trials:
            stats = self._return_stats.get(trial.trial_id)
            if stats is None:
                continue

            # Rebuild the DSR z-score using the trial's actual stats
            sr_hat = trial.sharpe
            T = stats.n_effective
            gamma3 = stats.skewness
            gamma4 = stats.kurtosis

            # SR0* from the full set of accumulated trials
            sr0_star = self.current_sr0_star()

            denom_sq = 1.0 - gamma3 * sr_hat + (gamma4 - 1.0) / 4.0 * sr_hat**2
            if denom_sq <= 0:
                denom_sq = 1e-8
            denom = math.sqrt(denom_sq)

            if T > 1:
                z = (sr_hat - sr0_star) * math.sqrt(T - 1) / denom
            else:
                z = 0.0

            dsr = float(_phi(z))
            if dsr >= th:
                survivors.append(trial)
        return survivors

    def summary(self) -> list[str]:
        """Return current trial tracker status as formatted lines."""
        lines = [
            "=" * 72,
            f"TRIAL TRACKER ({self.n_trials} trials recorded)",
            "=" * 72,
        ]
        if self.n_trials == 0:
            lines.append("  No trials recorded yet.")
            return lines

        sr0 = self.current_sr0_star()
        n_surv = len(self.survivors())
        best = max(self.trials, key=lambda t: t.sharpe)

        lines.extend(
            [
                f"  Current SR0* threshold : {sr0:.4f}",
                f"  Best observed Sharpe   : {best.sharpe:.4f} (trial #{best.trial_id})",
                f"  Survivors (DSR > {self.base_threshold}): {n_surv}/{self.n_trials}",
                "",
                f"  {'Trial':>5}  {'SR':>8}  {'PSR':>6}  {'DSR':>6}  {'Sig?':>5}  Strategy",
                f"  {'-'*5}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*5}  {'-'*15}",
            ]
        )
        for t in sorted(self.trials, key=lambda t: -t.sharpe)[:20]:
            sig = "YES" if t.significant_at_time else "no"
            lines.append(
                f"  {t.trial_id:5d}  {t.sharpe:8.4f}  {t.psr:6.3f}  "
                f"{t.dsr:6.3f}  {sig:>5}  {t.strategy_name}"
            )
        lines.append("=" * 72)
        return lines

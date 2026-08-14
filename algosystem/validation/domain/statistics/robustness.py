"""
Robustness checks that bridge the gap between "did the overfitting test pass?"
and "should I actually trade this?"

Five tools, each answering a different trust question:

1. bootstrap_sharpe_ci     -- "How precise is my Sharpe estimate?"
2. monte_carlo_trades      -- "Was my drawdown lucky or typical?"
3. alpha_beta_decomposition -- "Is this just levered beta or real alpha?"
4. kelly_criterion         -- "Is the edge large enough to bet on?"
5. regime_conditional      -- "Does this only work in calm markets?"
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# -----------------------------------------------------------------------
# 1. Bootstrap Confidence Interval on Sharpe Ratio
# -----------------------------------------------------------------------


@dataclass(frozen=True)
class SharpeCI:
    """Bootstrap confidence interval for the Sharpe ratio."""

    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence: float
    n_bootstrap: int
    ci_includes_zero: bool

    def summary(self) -> list[str]:
        """Return the Sharpe confidence interval report as formatted lines."""
        status = "FAIL -- CI includes zero" if self.ci_includes_zero else "PASS"
        return [
            f"Sharpe Ratio: {self.point_estimate:.4f}",
            f"  {self.confidence:.0%} CI: [{self.ci_lower:.4f}, {self.ci_upper:.4f}]",
            f"  Includes zero: {self.ci_includes_zero} [{status}]",
            f"  Bootstrap samples: {self.n_bootstrap}",
        ]


def bootstrap_sharpe_ci(
    returns: np.ndarray,
    n_bootstrap: int = 5000,
    confidence: float = 0.95,
    annualize: float = 252.0,
    seed: int = 42,
) -> SharpeCI:
    """
    Bootstrap confidence interval for the annualized Sharpe ratio.

    If the CI includes zero, the claimed Sharpe is not statistically
    distinguishable from a zero-skill strategy.

    Parameters
    ----------
    returns : np.ndarray
        Strategy returns (daily).
    n_bootstrap : int
        Number of bootstrap resamples.
    confidence : float
        Confidence level (default 0.95 = 95% CI).
    annualize : float
        Annualization factor (252 for daily).
    seed : int
        Random seed.
    """
    rng = np.random.default_rng(seed)
    n = len(returns)

    def _sharpe(r):
        if len(r) < 2:
            return 0.0
        m, s = np.mean(r), np.std(r, ddof=1)
        return (m / s) * np.sqrt(annualize) if s > 1e-12 else 0.0

    point = _sharpe(returns)

    boot_sharpes = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        boot_sharpes[i] = _sharpe(returns[idx])

    alpha = (1 - confidence) / 2
    ci_lower = float(np.percentile(boot_sharpes, 100 * alpha))
    ci_upper = float(np.percentile(boot_sharpes, 100 * (1 - alpha)))

    return SharpeCI(
        point_estimate=float(point),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        confidence=confidence,
        n_bootstrap=n_bootstrap,
        ci_includes_zero=ci_lower <= 0 <= ci_upper,
    )


# -----------------------------------------------------------------------
# 2. Monte Carlo Trade Resampling
# -----------------------------------------------------------------------


@dataclass(frozen=True)
class MonteCarloResults:
    """Results from trade-sequence Monte Carlo simulation."""

    n_simulations: int
    n_trades: int

    # Actual realized values
    actual_terminal_pnl: float
    actual_max_drawdown: float

    # Distribution from reshuffled trade sequences
    terminal_pnl_mean: float
    terminal_pnl_5th: float
    terminal_pnl_95th: float
    max_drawdown_mean: float
    max_drawdown_5th: float
    max_drawdown_95th: float

    # Percentile rank of actual in the MC distribution
    terminal_pnl_percentile: float  # where actual falls in MC dist
    max_drawdown_percentile: float

    def summary(self) -> list[str]:
        """Return the Monte Carlo trade resampling report as formatted lines."""
        lines = [
            "Monte Carlo Trade Resampling",
            f"  Trades: {self.n_trades}, Simulations: {self.n_simulations}",
            f"  Terminal PnL:  actual={self.actual_terminal_pnl:.4f}",
            f"    MC 5-95%:    [{self.terminal_pnl_5th:.4f}, {self.terminal_pnl_95th:.4f}]",
            f"    Percentile:  {self.terminal_pnl_percentile:.1f}th",
            f"  Max Drawdown:  actual={self.actual_max_drawdown:.4f}",
            f"    MC 5-95%:    [{self.max_drawdown_5th:.4f}, {self.max_drawdown_95th:.4f}]",
            f"    Percentile:  {self.max_drawdown_percentile:.1f}th",
        ]
        if self.actual_max_drawdown < self.max_drawdown_5th:
            lines.append("  WARNING: Actual drawdown was unusually mild -- may have been lucky")
        if self.actual_max_drawdown > self.max_drawdown_95th:
            lines.append("  WARNING: Actual drawdown was unusually severe")
        return lines


def monte_carlo_trades(
    trade_pnls: np.ndarray | list,
    n_simulations: int = 2000,
    seed: int = 42,
) -> MonteCarloResults:
    """
    Reshuffle the sequence of realized trade PnLs to build a distribution
    of possible equity curves from the same set of trades.

    Answers: "Given these trades, how lucky/unlucky was my specific ordering?"

    Parameters
    ----------
    trade_pnls : array-like
        Per-trade net PnL values (from compute_trade_log).
    n_simulations : int
        Number of reshuffled sequences to generate.
    seed : int
        Random seed.
    """
    pnls = np.asarray(trade_pnls, dtype=np.float64)
    n_trades = len(pnls)
    if n_trades < 3:
        return MonteCarloResults(
            n_simulations=0,
            n_trades=n_trades,
            actual_terminal_pnl=float(np.sum(pnls)),
            actual_max_drawdown=0.0,
            terminal_pnl_mean=0,
            terminal_pnl_5th=0,
            terminal_pnl_95th=0,
            max_drawdown_mean=0,
            max_drawdown_5th=0,
            max_drawdown_95th=0,
            terminal_pnl_percentile=50,
            max_drawdown_percentile=50,
        )

    rng = np.random.default_rng(seed)

    def _max_dd(equity):
        peak = np.maximum.accumulate(equity)
        dd = peak - equity
        return float(np.max(dd)) if len(dd) > 0 else 0.0

    # Actual path
    actual_equity = np.cumsum(pnls)
    actual_terminal = float(actual_equity[-1])
    actual_dd = _max_dd(actual_equity)

    # MC simulations
    mc_terminals = np.empty(n_simulations)
    mc_drawdowns = np.empty(n_simulations)

    for i in range(n_simulations):
        shuffled = pnls.copy()
        rng.shuffle(shuffled)
        equity = np.cumsum(shuffled)
        mc_terminals[i] = equity[-1]
        mc_drawdowns[i] = _max_dd(equity)

    return MonteCarloResults(
        n_simulations=n_simulations,
        n_trades=n_trades,
        actual_terminal_pnl=actual_terminal,
        actual_max_drawdown=actual_dd,
        terminal_pnl_mean=float(np.mean(mc_terminals)),
        terminal_pnl_5th=float(np.percentile(mc_terminals, 5)),
        terminal_pnl_95th=float(np.percentile(mc_terminals, 95)),
        max_drawdown_mean=float(np.mean(mc_drawdowns)),
        max_drawdown_5th=float(np.percentile(mc_drawdowns, 5)),
        max_drawdown_95th=float(np.percentile(mc_drawdowns, 95)),
        terminal_pnl_percentile=float(np.mean(mc_terminals <= actual_terminal) * 100),
        max_drawdown_percentile=float(np.mean(mc_drawdowns <= actual_dd) * 100),
    )


# -----------------------------------------------------------------------
# 3. Alpha/Beta Decomposition
# -----------------------------------------------------------------------


@dataclass(frozen=True)
class AlphaBetaResult:
    """OLS decomposition of strategy returns vs benchmark."""

    alpha_daily: float  # daily alpha (intercept)
    alpha_annual: float  # annualized alpha
    beta: float  # market exposure
    r_squared: float  # fraction of variance explained by benchmark
    tracking_error: float  # annualized std of residuals
    information_ratio: float  # alpha / tracking_error
    is_just_beta: bool  # True if alpha is not significant

    def summary(self) -> list[str]:
        """Return the alpha/beta decomposition report as formatted lines."""
        verdict = "JUST BETA" if self.is_just_beta else "HAS ALPHA"
        lines = [
            f"Alpha/Beta Decomposition [{verdict}]",
            f"  Alpha (annual): {self.alpha_annual:.4f} ({self.alpha_annual*100:.2f}%)",
            f"  Beta:           {self.beta:.4f}",
            f"  R-squared:      {self.r_squared:.4f}",
            f"  Info Ratio:     {self.information_ratio:.4f}",
            f"  Tracking Error: {self.tracking_error:.4f}",
        ]
        if self.is_just_beta:
            lines.append("  WARNING: Strategy returns are mostly explained by market exposure")
        return lines


def alpha_beta_decomposition(
    strategy_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    annualize: float = 252.0,
) -> AlphaBetaResult:
    """
    OLS regression: strategy = alpha + beta * benchmark + epsilon.

    Answers: "Is this just levered SPY or does it have real alpha?"

    Parameters
    ----------
    strategy_returns : np.ndarray
        Daily strategy returns.
    benchmark_returns : np.ndarray
        Daily benchmark returns (same length).
    annualize : float
        Annualization factor.
    """
    n = min(len(strategy_returns), len(benchmark_returns))
    y = strategy_returns[:n]
    x = benchmark_returns[:n]

    # OLS: y = alpha + beta * x
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    cov_xy = np.mean((x - x_mean) * (y - y_mean))
    var_x = np.var(x, ddof=0)

    beta = cov_xy / var_x if var_x > 1e-15 else 0.0
    alpha = y_mean - beta * x_mean

    # Residuals
    residuals = y - (alpha + beta * x)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-15 else 0.0

    tracking_error = float(np.std(residuals, ddof=1) * np.sqrt(annualize))
    alpha_annual = float(alpha * annualize)
    info_ratio = alpha_annual / tracking_error if tracking_error > 1e-12 else 0.0

    # Alpha significance: t-stat > 2 (roughly 95% CI)
    # Correct OLS intercept SE: sigma_hat * sqrt(1/n + x_mean^2 / sum_sq_x)
    if n > 2:
        sigma_hat = np.sqrt(ss_res / (n - 2))
        sum_sq_x = np.sum((x - x_mean) ** 2)
        if sum_sq_x > 1e-15:
            se_alpha = sigma_hat * np.sqrt(1.0 / n + x_mean**2 / sum_sq_x)
        else:
            se_alpha = float("inf")
    else:
        se_alpha = float("inf")
    t_stat = abs(alpha) / se_alpha if se_alpha > 1e-15 else 0.0
    is_just_beta = t_stat < 2.0

    return AlphaBetaResult(
        alpha_daily=float(alpha),
        alpha_annual=alpha_annual,
        beta=float(beta),
        r_squared=float(r_squared),
        tracking_error=tracking_error,
        information_ratio=float(info_ratio),
        is_just_beta=is_just_beta,
    )


# -----------------------------------------------------------------------
# 4. Kelly Criterion / Risk of Ruin
# -----------------------------------------------------------------------


@dataclass(frozen=True)
class KellyResult:
    """Kelly criterion and risk of ruin estimates."""

    win_rate: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float  # avg_win / avg_loss
    kelly_fraction: float  # optimal bet fraction
    half_kelly: float  # practical bet fraction
    edge: float  # expected return per dollar risked
    risk_of_ruin_full_kelly: float
    risk_of_ruin_half_kelly: float
    has_edge: bool  # True if Kelly > 0

    def summary(self) -> list[str]:
        """Return the Kelly criterion report as formatted lines."""
        verdict = "HAS EDGE" if self.has_edge else "NO EDGE"
        lines = [
            f"Kelly Criterion [{verdict}]",
            f"  Win rate:       {self.win_rate:.1%}",
            f"  Avg win:        {self.avg_win:.6f}",
            f"  Avg loss:       {self.avg_loss:.6f}",
            f"  Payoff ratio:   {self.payoff_ratio:.2f}",
            f"  Kelly fraction: {self.kelly_fraction:.4f} ({self.kelly_fraction*100:.1f}%)",
            f"  Half-Kelly:     {self.half_kelly:.4f} ({self.half_kelly*100:.1f}%)",
            f"  Edge (EV/$):    {self.edge:.6f}",
        ]
        if not self.has_edge:
            lines.append("  WARNING: Kelly fraction <= 0: no edge to exploit")
        else:
            lines.extend(
                [
                    f"  Risk of ruin (full Kelly):  {self.risk_of_ruin_full_kelly:.4f}",
                    f"  Risk of ruin (half Kelly):  {self.risk_of_ruin_half_kelly:.4f}",
                ]
            )
        return lines


def kelly_criterion(
    trade_pnls: np.ndarray | list,
    ruin_threshold: float = 0.5,
) -> KellyResult:
    """
    Compute the Kelly fraction and risk of ruin from realized trade PnLs.

    Answers: "Is the edge large enough to bet on, and at what size?"

    Parameters
    ----------
    trade_pnls : array-like
        Per-trade net PnL values.
    ruin_threshold : float
        Fraction of capital loss that constitutes "ruin" (default 0.5 = 50%).
    """
    pnls = np.asarray(trade_pnls, dtype=np.float64)
    if len(pnls) < 5:
        return KellyResult(
            win_rate=0,
            avg_win=0,
            avg_loss=0,
            payoff_ratio=0,
            kelly_fraction=0,
            half_kelly=0,
            edge=0,
            risk_of_ruin_full_kelly=1,
            risk_of_ruin_half_kelly=1,
            has_edge=False,
        )

    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]

    win_rate = len(wins) / len(pnls) if len(pnls) > 0 else 0.0
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(np.mean(np.abs(losses))) if len(losses) > 0 else 1e-12

    payoff_ratio = avg_win / avg_loss if avg_loss > 1e-12 else 0.0

    # Kelly: f* = (p * b - q) / b  where p=win_rate, q=1-p, b=payoff_ratio
    q = 1.0 - win_rate
    if payoff_ratio > 1e-12:
        kelly = (win_rate * payoff_ratio - q) / payoff_ratio
    else:
        kelly = 0.0

    kelly = max(kelly, 0.0)  # never negative (don't bet against yourself)
    half_kelly = kelly / 2.0

    # Edge: expected value per dollar risked
    edge = win_rate * avg_win - q * avg_loss

    # Risk of ruin (simplified): P(ruin) ~= ((1-edge)/(1+edge))^(capital/avg_risk)
    # Using the classic formula: P(ruin) = (q/p)^(n) where n = capital units
    if win_rate > 0 and win_rate < 1 and kelly > 0:
        # Number of "bets" worth of capital at the given fraction
        n_full = 1.0 / kelly if kelly > 0.01 else 100
        n_half = 1.0 / half_kelly if half_kelly > 0.01 else 100
        ratio = q / win_rate if win_rate > 1e-12 else 1.0
        ror_full = min(ratio**n_full, 1.0) if ratio < 1 else 1.0
        ror_half = min(ratio**n_half, 1.0) if ratio < 1 else 1.0
    else:
        ror_full = 1.0
        ror_half = 1.0

    return KellyResult(
        win_rate=float(win_rate),
        avg_win=float(avg_win),
        avg_loss=float(avg_loss),
        payoff_ratio=float(payoff_ratio),
        kelly_fraction=float(kelly),
        half_kelly=float(half_kelly),
        edge=float(edge),
        risk_of_ruin_full_kelly=float(ror_full),
        risk_of_ruin_half_kelly=float(ror_half),
        has_edge=kelly > 0,
    )


# -----------------------------------------------------------------------
# 5. Regime-Conditional Performance
# -----------------------------------------------------------------------


@dataclass(frozen=True)
class RegimeResult:
    """Performance breakdown by volatility regime."""

    regime_names: list
    regime_sharpes: list
    regime_counts: list  # number of observations per regime
    regime_frac: list  # fraction of total time in each regime
    overall_sharpe: float
    worst_regime_sharpe: float
    worst_regime_name: str
    works_in_all_regimes: bool  # True if Sharpe > 0 in all regimes

    def summary(self) -> list[str]:
        """Return the regime-conditional performance report as formatted lines."""
        verdict = "ALL REGIMES" if self.works_in_all_regimes else "REGIME-DEPENDENT"
        lines = [
            f"Regime-Conditional Performance [{verdict}]",
            f"  Overall Sharpe: {self.overall_sharpe:.4f}",
            f"  {'Regime':<15} {'Sharpe':>8} {'Frac':>8} {'Days':>6}",
            f"  {'-'*15} {'-'*8} {'-'*8} {'-'*6}",
        ]
        for i, name in enumerate(self.regime_names):
            lines.append(
                f"  {name:<15} {self.regime_sharpes[i]:8.4f} "
                f"{self.regime_frac[i]:7.1%} {self.regime_counts[i]:6d}"
            )
        if not self.works_in_all_regimes:
            lines.append(
                f"  WARNING: Worst regime: {self.worst_regime_name} "
                f"(Sharpe={self.worst_regime_sharpe:.4f})"
            )
        return lines


def regime_conditional_performance(  # noqa: C901
    strategy_returns: np.ndarray,
    market_returns: np.ndarray | None = None,
    n_regimes: int = 3,
    vol_window: int = 21,
    annualize: float = 252.0,
) -> RegimeResult:
    """
    Split performance by volatility regime and report Sharpe per regime.

    Answers: "Does this strategy only work in calm markets?"

    Regimes are defined by rolling volatility percentiles of the strategy
    returns (or market returns if provided):
        Low vol (bottom tercile), Medium vol, High vol (top tercile)

    Parameters
    ----------
    strategy_returns : np.ndarray
        Daily strategy returns.
    market_returns : np.ndarray or None
        Market returns for regime classification. If None, uses strategy returns.
    n_regimes : int
        Number of vol regimes (default 3: low/med/high).
    vol_window : int
        Rolling window for volatility estimation (default 21 days).
    annualize : float
        Annualization factor.
    """
    ref = market_returns if market_returns is not None else strategy_returns
    n = len(strategy_returns)

    # Compute rolling volatility
    if n <= vol_window:
        # Not enough data for regimes
        return RegimeResult(
            regime_names=["all"],
            regime_sharpes=[0.0],
            regime_counts=[n],
            regime_frac=[1.0],
            overall_sharpe=0.0,
            worst_regime_sharpe=0.0,
            worst_regime_name="all",
            works_in_all_regimes=False,
        )

    rolling_vol = np.empty(n)
    rolling_vol[:vol_window] = np.nan
    for i in range(vol_window, n):
        rolling_vol[i] = np.std(ref[i - vol_window : i], ddof=1)

    # Assign regimes based on percentiles (skip NaN warmup)
    valid = ~np.isnan(rolling_vol)
    valid_vol = rolling_vol[valid]
    thresholds = np.percentile(valid_vol, np.linspace(0, 100, n_regimes + 1)[1:-1])

    regime_labels = np.full(n, -1, dtype=int)
    for i in range(n):
        if np.isnan(rolling_vol[i]):
            continue
        label = 0
        for t in thresholds:
            if rolling_vol[i] > t:
                label += 1
        regime_labels[i] = label

    regime_names = (
        ["low_vol", "med_vol", "high_vol"]
        if n_regimes == 3
        else [f"regime_{i}" for i in range(n_regimes)]
    )

    def _sharpe(r):
        if len(r) < 5:
            return 0.0
        m, s = np.mean(r), np.std(r, ddof=1)
        return (m / s) * np.sqrt(annualize) if s > 1e-12 else 0.0

    overall = _sharpe(strategy_returns[valid])
    regime_sharpes = []
    regime_counts = []
    regime_frac = []
    n_valid = np.sum(valid)

    for r in range(n_regimes):
        mask = regime_labels == r
        count = int(np.sum(mask))
        regime_counts.append(count)
        regime_frac.append(count / n_valid if n_valid > 0 else 0.0)
        if count >= 5:
            regime_sharpes.append(float(_sharpe(strategy_returns[mask])))
        else:
            regime_sharpes.append(0.0)

    worst_idx = int(np.argmin(regime_sharpes))
    works_all = all(s > 0 for s in regime_sharpes)

    return RegimeResult(
        regime_names=regime_names,
        regime_sharpes=regime_sharpes,
        regime_counts=regime_counts,
        regime_frac=regime_frac,
        overall_sharpe=float(overall),
        worst_regime_sharpe=float(regime_sharpes[worst_idx]),
        worst_regime_name=regime_names[worst_idx],
        works_in_all_regimes=works_all,
    )

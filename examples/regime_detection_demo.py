"""
Demo: regime detection catches what the headline Sharpe ratio hides.

Two strategies are calibrated to the SAME overall Sharpe.
One earns its return evenly across all market conditions. The other earns
everything in calm markets and gives it back when volatility arrives.

The headline number cannot tell them apart. Regime analysis can.
"""

import numpy as np
import pandas as pd

from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.shared.errors import ValidationError
from algosystem.validation.application.analyze_regimes import AnalyzeRegimes

N = 750
BREAK = N // 2
rng = np.random.default_rng(20260918)

# A market that is calm for the first half and stormy for the second.
market = np.concatenate(
    [rng.normal(0.0004, 0.004, BREAK), rng.normal(-0.0002, 0.025, N - BREAK)]
)

# Strategy A: a steady edge, indifferent to the market's state.
robust = rng.normal(0.00075, 0.009, N)

# Strategy B: a big edge while calm, bleeding once volatility arrives.
_fragile = np.concatenate(
    [rng.normal(0.0026, 0.009, BREAK), rng.normal(-0.0011, 0.009, N - BREAK)]
)


def curve(returns):
    levels = np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + returns)])
    index = pd.date_range("2023-01-02", periods=len(levels), freq="B")
    return EquityCurve.from_series(pd.Series(levels, index=index))


def sharpe(returns):
    return float(np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(252))


def matched_to(target, returns):
    """Shift a return series so its overall Sharpe equals `target` exactly.

    A constant shift leaves the standard deviation untouched, so this changes
    only the headline number -- the regime *structure* is preserved.
    """
    sd = np.std(returns, ddof=1)
    return returns + (target * sd / np.sqrt(252) - np.mean(returns))


# Calibrate B to the SAME overall Sharpe as A, so only regime analysis separates them.
fragile = matched_to(sharpe(robust), _fragile)


market_curve = curve(market)
analyzer = AnalyzeRegimes()

print("=" * 66)
print("HEADLINE NUMBERS -- these are what a tearsheet shows you")
print("=" * 66)
print(f"  Strategy A (robust)  annualized Sharpe : {sharpe(robust):.2f}")
print(f"  Strategy B (fragile) annualized Sharpe : {sharpe(fragile):.2f}")
print("\n  Same number. A tearsheet cannot separate these. Now split by regime.\n")

for name, returns in [("A (robust)", robust), ("B (fragile)", fragile)]:
    result = analyzer.execute(curve(returns), market_returns=market_curve)
    print("=" * 66)
    print(f"STRATEGY {name}")
    print("=" * 66)
    print("\n".join("  " + line for line in result.summary()))
    verdict = "SAFE" if result.works_in_all_regimes else "DO NOT TRADE AS SIZED"
    print(f"\n  works_in_all_regimes = {result.works_in_all_regimes}  ->  {verdict}\n")

print("=" * 66)
print("GUARDRAILS")
print("=" * 66)

# Too little data to classify -- refuses rather than printing zeros.
try:
    analyzer.execute(np.full(15, 0.001))
except ValidationError as exc:
    print(f"  short series      -> ValidationError: {exc}")

# Benchmark from a different period -- refuses rather than misaligning.
stale = EquityCurve.from_series(
    pd.Series(
        np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + market)]),
        index=pd.date_range("2010-01-04", periods=N + 1, freq="B"),
    )
)
try:
    analyzer.execute(curve(fragile), market_returns=stale)
except ValidationError as exc:
    print(f"  mismatched dates  -> ValidationError: {exc}")

print("\n  Both would otherwise have produced confident, meaningless output.")

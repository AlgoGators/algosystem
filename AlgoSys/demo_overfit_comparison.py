"""
Side-by-side comparison: an overfit strategy vs a strategy with real edge.
Generates plots for both so you can see what each looks like.
"""

import numpy as np
from overfit_detector import OverfitDetector


# -----------------------------------------------------------------------
# Shared backtest: simple momentum / trend-follow
# Long when rolling mean of returns > threshold, flat otherwise.
# -----------------------------------------------------------------------

def momentum_backtest(params, returns):
    lookback = params['lookback']
    threshold = params['threshold']
    n = len(returns)
    if n <= lookback:
        return 0.0

    cumsum = np.cumsum(returns)
    rolling_mean = np.empty(n)
    rolling_mean[:lookback] = 0.0
    rolling_mean[lookback:] = (cumsum[lookback:] - cumsum[:n - lookback]) / lookback

    signal = (rolling_mean > threshold).astype(float)
    strat_returns = signal * returns
    strat_returns = strat_returns[lookback:]
    if len(strat_returns) == 0:
        return 0.0
    mean_r = np.mean(strat_returns)
    std_r = np.std(strat_returns, ddof=1)
    if std_r < 1e-12:
        return 0.0
    return (mean_r / std_r) * np.sqrt(252)


def generate_noise_returns(n=5000, seed=100):
    """Pure IID noise — no exploitable momentum structure at all."""
    rng = np.random.default_rng(seed)
    return rng.normal(0.00005, 0.012, size=n)


def generate_trending_returns(n=5000, seed=100):
    """
    Returns with a planted trend-following / regime signal.
    Long bull/bear regimes (~200 days each) with strong drift.
    A momentum strategy should exploit this; shuffling destroys it.
    """
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    regime = 1.0  # +1 = bull, -1 = bear
    for i in range(n):
        # Regime flips infrequently (avg length ~200 days)
        if rng.random() < 0.005:
            regime *= -1
        # Strong regime-dependent drift
        returns[i] = regime * 0.0015 + rng.normal(0.0, 0.01)
    return returns


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')

    param_grid = {
        'lookback': [3, 5, 8, 10, 15, 20, 30, 40, 60, 80, 100, 120],
        'threshold': [-0.002, -0.001, -0.0005, 0.0, 0.0002, 0.0005,
                      0.001, 0.0015, 0.002, 0.003],
    }

    n_reps = 500

    # --- OVERFIT: momentum strategy on pure noise ---
    print("\n" + "=" * 72)
    print("SCENARIO 1: OVERFIT (momentum on pure noise)")
    print("=" * 72)
    noise_returns = generate_noise_returns()

    det_overfit = OverfitDetector(
        backtest_fn=momentum_backtest,
        returns=noise_returns,
        param_grid=param_grid,
        n_reps=n_reps,
        shuffle_method='complete',
        n_workers=1,
        seed=42,
    )
    res_overfit = det_overfit.run()
    print()
    res_overfit.report()
    res_overfit.plot_null_distribution(save_path='demo_overfit_null.png')
    res_overfit.plot_parameter_sensitivity(save_path='demo_overfit_sensitivity.png')

    # --- REAL EDGE: momentum strategy on trending data ---
    print("\n" + "=" * 72)
    print("SCENARIO 2: REAL EDGE (momentum on regime-trending data)")
    print("=" * 72)
    trending_returns = generate_trending_returns()

    det_real = OverfitDetector(
        backtest_fn=momentum_backtest,
        returns=trending_returns,
        param_grid=param_grid,
        n_reps=n_reps,
        shuffle_method='complete',
        n_workers=1,
        seed=42,
    )
    res_real = det_real.run()
    print()
    res_real.report()
    res_real.plot_null_distribution(save_path='demo_real_null.png')
    res_real.plot_parameter_sensitivity(save_path='demo_real_sensitivity.png')

    print("\n\nSaved plots:")
    print("  demo_overfit_null.png         — null distribution (overfit)")
    print("  demo_overfit_sensitivity.png  — parameter sensitivity (overfit)")
    print("  demo_real_null.png            — null distribution (real edge)")
    print("  demo_real_sensitivity.png     — parameter sensitivity (real edge)")

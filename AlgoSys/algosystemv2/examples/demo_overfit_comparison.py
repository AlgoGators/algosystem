"""
Side-by-side comparison: an overfit strategy vs a strategy with real edge.
Generates plots for both so you can see what each looks like.
"""

import numpy as np

from algosystemv2.overfitting import OverfitDetector, plot_null_distribution, plot_parameter_sensitivity
from algosystemv2.overfitting.strategies.momentum import momentum_backtest
from algosystemv2.overfitting.data_generators import generate_noise, generate_trending


def generate_noise_returns(n=5000, seed=100):
    """Pure IID noise — no exploitable momentum structure at all."""
    return np.random.default_rng(seed).normal(0.00005, 0.012, size=n)


def generate_trending_returns(n=5000, seed=100):
    """Returns with a planted trend-following / regime signal."""
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    regime = 1.0
    for i in range(n):
        if rng.random() < 0.005:
            regime *= -1
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
    plot_null_distribution(res_overfit, save_path='demo_overfit_null.png')
    plot_parameter_sensitivity(res_overfit, save_path='demo_overfit_sensitivity.png')

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
    plot_null_distribution(res_real, save_path='demo_real_null.png')
    plot_parameter_sensitivity(res_real, save_path='demo_real_sensitivity.png')

    print("\n\nSaved plots:")
    print("  demo_overfit_null.png         — null distribution (overfit)")
    print("  demo_overfit_sensitivity.png  — parameter sensitivity (overfit)")
    print("  demo_real_null.png            — null distribution (real edge)")
    print("  demo_real_sensitivity.png     — parameter sensitivity (real edge)")

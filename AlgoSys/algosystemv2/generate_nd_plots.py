"""
Generate N-dimensional overfitting visualizations.

Creates:
1. 3D volume scatter for a 3-signal strategy (dual momentum)
2. 3D slider surface for the same strategy
3. Parallel coordinates for a 4-signal strategy (vol regime)
4. Pairwise 3D grid for 4 signals
5. Side-by-side: overfit (noise) vs real (trending) in 3D
"""
import numpy as np
from algosystemv2.overfitting import (
    OverfitDetector,
    plot_volume_3d,
    plot_surface_3d_interactive,
    plot_parallel_coordinates,
    plot_pairwise_3d_grid,
    plot_parameter_space,
)
from algosystemv2.overfitting.strategies.dual_momentum import dual_momentum_backtest
from algosystemv2.overfitting.strategies.volatility import vol_regime_backtest
from algosystemv2.overfitting.strategies.mean_reversion import mean_reversion_backtest
from algosystemv2.overfitting.data_generators import generate_noise, generate_trending

import os
outdir = os.path.join(os.path.dirname(__file__), 'nd_plots')
os.makedirs(outdir, exist_ok=True)

# =====================================================
# 1. THREE-SIGNAL STRATEGY: Dual Momentum on NOISE (overfit)
# =====================================================
print("=" * 60)
print("1. Dual Momentum (3 signals) on NOISE — expect overfit")
print("=" * 60)

noise = generate_noise(n=3000, seed=42)

param_grid_3d = {
    'fast_lookback': [3, 5, 10, 15],
    'slow_lookback': [20, 40, 60, 80],
    'threshold': [0.0, 0.0005, 0.001],
}

det_noise = OverfitDetector(
    backtest_fn=dual_momentum_backtest,
    returns=noise,
    param_grid=param_grid_3d,
    n_reps=200, n_workers=1, seed=42,
)
res_noise = det_noise.run()
res_noise.report()
sa = res_noise.surface_analysis()
print(f"Plateau score: {sa['plateau_score']:.4f}")

# 3D Volume scatter — each dot is a param combo, color = Sharpe
print("\nGenerating 3D volume scatter (overfit)...")
plot_volume_3d(
    res_noise, 'fast_lookback', 'slow_lookback', 'threshold',
    save_path=os.path.join(outdir, '1_overfit_3d_volume.html'),
)

# 3D Surface with slider
print("Generating 3D slider surface (overfit)...")
plot_surface_3d_interactive(
    res_noise, 'fast_lookback', 'slow_lookback', 'threshold',
    save_path=os.path.join(outdir, '2_overfit_3d_surface.html'),
)

# =====================================================
# 2. THREE-SIGNAL STRATEGY: Dual Momentum on TRENDING (real edge)
# =====================================================
print("\n" + "=" * 60)
print("2. Dual Momentum (3 signals) on TRENDING — expect real edge")
print("=" * 60)

trending = generate_trending(n=3000, seed=42)

det_trend = OverfitDetector(
    backtest_fn=dual_momentum_backtest,
    returns=trending,
    param_grid=param_grid_3d,
    n_reps=200, n_workers=1, seed=42,
)
res_trend = det_trend.run()
res_trend.report()
sa = res_trend.surface_analysis()
print(f"Plateau score: {sa['plateau_score']:.4f}")

# 3D Volume scatter — real edge
print("\nGenerating 3D volume scatter (real edge)...")
plot_volume_3d(
    res_trend, 'fast_lookback', 'slow_lookback', 'threshold',
    save_path=os.path.join(outdir, '3_real_edge_3d_volume.html'),
)

# 3D Surface with slider — real edge
print("Generating 3D slider surface (real edge)...")
plot_surface_3d_interactive(
    res_trend, 'fast_lookback', 'slow_lookback', 'threshold',
    save_path=os.path.join(outdir, '4_real_edge_3d_surface.html'),
)

# =====================================================
# 3. FOUR-SIGNAL STRATEGY: Vol Regime (4D parallel coordinates)
# =====================================================
print("\n" + "=" * 60)
print("3. Vol Regime (4 signals) — parallel coordinates + pairwise 3D")
print("=" * 60)

param_grid_4d = {
    'vol_lookback': [10, 20, 30, 40],
    'vol_threshold': [0.10, 0.15, 0.20, 0.25, 0.30],
    'low_weight': [0.1, 0.3, 0.5],
    'high_weight': [0.8, 1.0, 1.5],
}

# On noise (overfit)
det_vol_noise = OverfitDetector(
    backtest_fn=vol_regime_backtest,
    returns=noise,
    param_grid=param_grid_4d,
    n_reps=200, n_workers=1, seed=42,
)
res_vol_noise = det_vol_noise.run()
res_vol_noise.report()

print("\nGenerating 4D parallel coordinates (overfit)...")
plot_parallel_coordinates(
    res_vol_noise,
    save_path=os.path.join(outdir, '5_overfit_4d_parallel.html'),
)

print("Generating pairwise 3D grid (overfit)...")
plot_pairwise_3d_grid(
    res_vol_noise,
    save_path=os.path.join(outdir, '6_overfit_4d_pairwise.html'),
)

# On trending (real edge)
det_vol_trend = OverfitDetector(
    backtest_fn=vol_regime_backtest,
    returns=trending,
    param_grid=param_grid_4d,
    n_reps=200, n_workers=1, seed=42,
)
res_vol_trend = det_vol_trend.run()
res_vol_trend.report()

print("\nGenerating 4D parallel coordinates (real edge)...")
plot_parallel_coordinates(
    res_vol_trend,
    save_path=os.path.join(outdir, '7_real_edge_4d_parallel.html'),
)

print("Generating pairwise 3D grid (real edge)...")
plot_pairwise_3d_grid(
    res_vol_trend,
    save_path=os.path.join(outdir, '8_real_edge_4d_pairwise.html'),
)

# =====================================================
# 4. THREE-SIGNAL: Mean Reversion (3D)
# =====================================================
print("\n" + "=" * 60)
print("4. Mean Reversion (3 signals) — auto-routed visualization")
print("=" * 60)

param_grid_mr = {
    'lookback': [10, 15, 20, 30, 40],
    'entry_z': [1.0, 1.5, 2.0, 2.5],
    'exit_z': [0.0, 0.25, 0.5],
}

# Noise
det_mr = OverfitDetector(
    backtest_fn=mean_reversion_backtest,
    returns=noise,
    param_grid=param_grid_mr,
    n_reps=200, n_workers=1, seed=42,
)
res_mr = det_mr.run()
print(f"Best SR={res_mr.best_sharpe:.4f}, p={res_mr.unbiased_pvalue:.4f}")

print("\nGenerating 3D plots for mean reversion (overfit)...")
plot_volume_3d(
    res_mr, 'lookback', 'entry_z', 'exit_z',
    save_path=os.path.join(outdir, '9_mr_overfit_volume.html'),
)

print("\n" + "=" * 60)
print("ALL DONE! Open the HTML files in your browser.")
print(f"Files saved to: {outdir}")
print("=" * 60)
print("\nFiles generated:")
for f in sorted(os.listdir(outdir)):
    print(f"  {f}")

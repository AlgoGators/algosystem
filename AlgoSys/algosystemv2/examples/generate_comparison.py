"""
Generate side-by-side comparison: REAL SIGNAL vs OVERFIT.
Shows how each diagnostic panel looks for genuine vs fake strategies.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

from algosystemv2.overfitting import (
    OverfitDetector, check_autocorrelation, walk_forward_analysis,
)
from algosystemv2.overfitting.strategies import momentum_backtest, PARAM_GRIDS
from algosystemv2.overfitting.data_generators import generate_trending, generate_noise

grid = {k: v[:5] for k, v in PARAM_GRIDS['momentum'].items()}

# === REAL SIGNAL ===
print('Running REAL SIGNAL...')
trending = generate_trending(n=3000, seed=42)
det_real = OverfitDetector(
    backtest_fn=momentum_backtest, returns=trending,
    param_grid=grid, n_reps=100, n_workers=1, seed=42,
)
res_real = det_real.run()
wf_real = walk_forward_analysis(
    backtest_fn=momentum_backtest, returns=trending,
    param_grid=grid, n_folds=6, purge_gap=20,
)

# === OVERFIT ===
print('Running OVERFIT...')
noise = generate_noise(n=3000, seed=42)
det_overfit = OverfitDetector(
    backtest_fn=momentum_backtest, returns=noise,
    param_grid=grid, n_reps=100, n_workers=1, seed=42,
)
res_overfit = det_overfit.run()
wf_overfit = walk_forward_analysis(
    backtest_fn=momentum_backtest, returns=noise,
    param_grid=grid, n_folds=6, purge_gap=20,
)

# === BUILD COMPARISON FIGURE ===
fig, axes = plt.subplots(2, 4, figsize=(24, 11))

param_keys = sorted({k for p in res_real.param_list for k in p})
px, py = param_keys[0], param_keys[1]
xvals = sorted(set(p[px] for p in res_real.param_list))
yvals = sorted(set(p[py] for p in res_real.param_list))


def draw_row(row, res, wf, label, color):
    # A) Null distribution
    ax = axes[row, 0]
    ax.hist(res.null_best_sharpes, bins=35, density=True, alpha=0.7,
            color='steelblue', edgecolor='black')
    ax.axvline(res.best_sharpe, color='red', linewidth=2.5, linestyle='--')
    ax.set_xlabel('Best Sharpe (permuted)')
    ax.set_ylabel('Density')
    ax.set_title(
        f'{label}: Null Distribution\n'
        f'S*={res.best_sharpe:.2f}, p={res.unbiased_pvalue:.4f}',
        fontsize=11, fontweight='bold', color=color)

    # B) P-value comparison
    ax = axes[row, 1]
    n = min(res.n_params, 20)
    ranks = np.arange(1, n + 1)
    solo = np.array([res.solo_pvalues[res.sort_indices[i]] for i in range(n)])
    unbiased = res.unbiased_pvalues[:n]
    ax.scatter(ranks, solo, c='steelblue', s=30, label='Solo')
    ax.scatter(ranks, unbiased, c='#d9534f', s=30, marker='s', label='Unbiased')
    for i in range(n):
        ax.plot([ranks[i], ranks[i]], [solo[i], unbiased[i]],
                color='grey', linewidth=0.5, alpha=0.5)
    ax.axhline(0.05, color='green', linestyle='--', alpha=0.5)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel('Param rank')
    ax.set_ylabel('P-value')
    fd = int(np.sum((solo < 0.05) & (unbiased >= 0.05)))
    ax.set_title(
        f'{label}: P-values ({fd} false disc.)\n'
        f'Gap = multiple-testing penalty',
        fontsize=11, fontweight='bold', color=color)
    ax.legend(fontsize=8)

    # C) Walk-forward
    ax = axes[row, 2]
    for i in range(len(wf.is_sharpes)):
        ax.scatter(wf.is_sharpes[i], wf.oos_sharpes[i],
                   c=color, s=80, edgecolors='black', linewidths=0.5, zorder=3)
    all_vals = list(wf.is_sharpes) + list(wf.oos_sharpes)
    lo = min(all_vals) - 0.5
    hi = max(all_vals) + 0.5
    ax.plot([lo, hi], [lo, hi], 'k--', alpha=0.3)
    ax.plot([lo, hi], [lo * 0.5, hi * 0.5], 'r--', alpha=0.3)
    ax.axhline(0, color='grey', linewidth=0.5)
    ax.set_xlabel('IS Sharpe')
    ax.set_ylabel('OOS Sharpe')
    ax.set_title(
        f'{label}: Walk-Forward\nWFE={wf.wfe:.2f}',
        fontsize=11, fontweight='bold', color=color)

    # D) Parameter surface
    ax = axes[row, 3]
    g = np.full((len(yvals), len(xvals)), np.nan)
    c = np.zeros_like(g)
    for i, p in enumerate(res.param_list):
        xi, yi = xvals.index(p[px]), yvals.index(p[py])
        if np.isnan(g[yi, xi]):
            g[yi, xi] = 0.0
        g[yi, xi] += res.original_sharpes[i]
        c[yi, xi] += 1
    mask = c > 0
    g[mask] /= c[mask]
    vmin, vmax = np.nanmin(g), np.nanmax(g)
    if vmin < 0 < vmax:
        norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
        cmap = 'RdYlGn'
    else:
        norm = None
        cmap = 'viridis'
    im = ax.imshow(g, aspect='auto', origin='lower', cmap=cmap, norm=norm)
    ax.set_xticks(range(len(xvals)))
    ax.set_xticklabels([str(v) for v in xvals], fontsize=7, rotation=45)
    ax.set_yticks(range(len(yvals)))
    ax.set_yticklabels([str(v) for v in yvals], fontsize=7)
    ax.set_xlabel(px)
    ax.set_ylabel(py)
    sa = res.surface_analysis()
    ax.set_title(
        f'{label}: Param Surface\nPlateau={sa["plateau_score"]:.2f}',
        fontsize=11, fontweight='bold', color=color)
    plt.colorbar(im, ax=ax, shrink=0.8)


draw_row(0, res_real, wf_real, 'REAL SIGNAL', '#2d7d2d')
draw_row(1, res_overfit, wf_overfit, 'OVERFIT', '#d9534f')

fig.suptitle(
    'HOW TO SEE OVERFITTING: Real Signal (top) vs Overfit (bottom)',
    fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig('overfit_comparison.png', dpi=150, bbox_inches='tight')
print('Saved overfit_comparison.png')

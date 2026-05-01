"""Generate overfit vs real edge comparison plots."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from algosystemv2.overfitting import (
    OverfitDetector, probabilistic_sharpe_ratio, deflated_sharpe_ratio,
)
from algosystemv2.overfitting.strategies.momentum import momentum_backtest
from algosystemv2.overfitting.data_generators import generate_noise, generate_trending

param_grid = {
    'lookback': [5, 10, 20, 30, 40, 60],
    'threshold': [-0.001, 0.0, 0.0005, 0.001, 0.002],
}
n_reps = 300

# === SCENARIO 1: OVERFIT (momentum on pure noise) ===
print('Running OVERFIT scenario (momentum on noise)...')
noise = generate_noise(n=3000, seed=42)
det_overfit = OverfitDetector(
    backtest_fn=momentum_backtest, returns=noise,
    param_grid=param_grid, n_reps=n_reps, n_workers=1, seed=42,
)
res_overfit = det_overfit.run()
res_overfit.report()
dsr_o = deflated_sharpe_ratio(noise, n_trials=res_overfit.n_params,
                               all_sharpes=res_overfit.original_sharpes,
                               sr_hat=res_overfit.best_sharpe)
sa_o = res_overfit.surface_analysis()
print(f'DSR: {dsr_o.dsr:.4f}, Plateau: {sa_o["plateau_score"]:.4f}')

# === SCENARIO 2: REAL EDGE (momentum on trending data) ===
print('\nRunning REAL EDGE scenario (momentum on trending data)...')
trending = generate_trending(n=3000, seed=42)
det_real = OverfitDetector(
    backtest_fn=momentum_backtest, returns=trending,
    param_grid=param_grid, n_reps=n_reps, n_workers=1, seed=42,
)
res_real = det_real.run()
res_real.report()
dsr_r = deflated_sharpe_ratio(trending, n_trials=res_real.n_params,
                               all_sharpes=res_real.original_sharpes,
                               sr_hat=res_real.best_sharpe)
sa_r = res_real.surface_analysis()
print(f'DSR: {dsr_r.dsr:.4f}, Plateau: {sa_r["plateau_score"]:.4f}')

# === GENERATE PLOTS ===
print('\nGenerating plots...')
fig, axes = plt.subplots(2, 3, figsize=(22, 14))

xvals = sorted(set(p['lookback'] for p in res_overfit.param_list))
yvals = sorted(set(p['threshold'] for p in res_overfit.param_list))

for row, (res, dsr, sa, label, color) in enumerate([
    (res_overfit, dsr_o, sa_o, 'OVERFIT', '#d9534f'),
    (res_real, dsr_r, sa_r, 'REAL EDGE', '#5cb85c'),
]):
    # A) Null distribution
    ax = axes[row, 0]
    ax.hist(res.null_best_sharpes, bins=40, density=True, alpha=0.7,
            color='steelblue', edgecolor='black', label='Null (permuted best SR)')
    ax.axvline(res.best_sharpe, color='red', linewidth=2.5, linestyle='--',
               label=f'S* = {res.best_sharpe:.3f}')
    ax.set_xlabel('Best Sharpe (permuted)', fontsize=11)
    ax.set_ylabel('Density', fontsize=11)
    ax.set_title(f'{label}: Null Distribution\np={res.unbiased_pvalue:.4f}',
                 fontsize=13, fontweight='bold', color=color)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # B) Parameter surface heatmap
    ax = axes[row, 1]
    grid = np.full((len(yvals), len(xvals)), np.nan)
    counts = np.zeros_like(grid)
    for i, p in enumerate(res.param_list):
        xi = xvals.index(p['lookback'])
        yi = yvals.index(p['threshold'])
        if np.isnan(grid[yi, xi]):
            grid[yi, xi] = 0.0
        grid[yi, xi] += res.original_sharpes[i]
        counts[yi, xi] += 1
    mask = counts > 0
    grid[mask] /= counts[mask]

    vabs = max(abs(np.nanmin(grid)), abs(np.nanmax(grid)), 0.5)
    im = ax.imshow(grid, aspect='auto', origin='lower', cmap='RdYlGn',
                   vmin=-vabs, vmax=vabs)
    ax.set_xticks(range(len(xvals)))
    ax.set_xticklabels(xvals, fontsize=9)
    ax.set_yticks(range(len(yvals)))
    ax.set_yticklabels([f'{v:.4f}' for v in yvals], fontsize=9)
    ax.set_xlabel('lookback', fontsize=11)
    ax.set_ylabel('threshold', fontsize=11)

    best_p = res.param_list[res.best_param_index]
    bx = xvals.index(best_p['lookback'])
    by = yvals.index(best_p['threshold'])
    ax.plot(bx, by, 'r*', markersize=18, markeredgecolor='black')
    plt.colorbar(im, ax=ax, shrink=0.8, label='Sharpe')

    if label == 'OVERFIT':
        subtitle = 'Spike = overfit (isolated bright spot)'
    else:
        subtitle = 'Plateau = robust (broad warm region)'
    ax.set_title(f'{label}: Parameter Surface\nPlateau={sa["plateau_score"]:.3f} | {subtitle}',
                 fontsize=13, fontweight='bold', color=color)

    # C) Sensitivity to lookback
    ax = axes[row, 2]
    val_sharpes = {}
    for i, p in enumerate(res.param_list):
        v = p['lookback']
        val_sharpes.setdefault(v, []).append(res.original_sharpes[i])

    xs = sorted(val_sharpes.keys())
    means = [np.mean(val_sharpes[v]) for v in xs]
    stds = [np.std(val_sharpes[v]) for v in xs]

    ax.fill_between(xs, [m - s for m, s in zip(means, stds)],
                    [m + s for m, s in zip(means, stds)],
                    alpha=0.25, color='steelblue')
    ax.plot(xs, means, 'o-', color='steelblue', linewidth=2, markersize=5,
            label='mean +/- std')

    # Individual slices (one line per threshold value)
    for th in sorted(set(p['threshold'] for p in res.param_list)):
        pts = [(p['lookback'], res.original_sharpes[i])
               for i, p in enumerate(res.param_list) if p['threshold'] == th]
        pts.sort()
        ax.plot([x for x, y in pts], [y for x, y in pts],
                color='grey', alpha=0.2, linewidth=0.8)

    ax.axhline(0, color='black', linewidth=0.5, alpha=0.5)
    ax.set_xlabel('lookback', fontsize=11)
    ax.set_ylabel('Sharpe', fontsize=11)

    if label == 'OVERFIT':
        subtitle = 'Erratic lines = fragile'
    else:
        subtitle = 'Parallel lines = robust'
    ax.set_title(f'{label}: Sensitivity to lookback\nDSR={dsr.dsr:.4f} | {subtitle}',
                 fontsize=13, fontweight='bold', color=color)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

fig.suptitle('OVERFITTING DETECTION: Overfit vs Real Edge\n'
             'Top row: momentum on pure noise (overfit) | '
             'Bottom row: momentum on regime-trending data (real edge)',
             fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig('overfit_vs_real_comparison.png', dpi=150, bbox_inches='tight')
print(f'\nSaved to overfit_vs_real_comparison.png')
print('Done!')

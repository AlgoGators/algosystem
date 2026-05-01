"""
Plotting functions for overfitting detection results.

Separated from the results dataclass to keep visualization concerns
isolated from data/statistics.

Visual Guide — How to Read Each Plot:
    A) Null Distribution: The blue histogram shows what the BEST Sharpe
       across all params looks like when there's NO real signal (permuted).
       The red line is YOUR best Sharpe. If red is far right → real signal.
       If red is inside the blue mass → likely overfit / noise.

    B) Parameter Surface: Heatmap of Sharpe across 2 parameters.
       A smooth, broad plateau = robust strategy.
       A single sharp spike = overfit to specific param values.

    C) IS vs OOS Degradation: Each dot is one walk-forward fold.
       Points near the diagonal (45° line) = strategy generalizes well.
       Points below the diagonal = OOS degrades vs IS → overfitting.

    D) PBO Logit Distribution: Histogram of logit(rank) values.
       Mass left of zero = the IS-best choice underperforms OOS median.
       PBO = fraction left of zero. PBO > 0.5 = likely overfit.

    E) Autocorrelation: ACF bars at each lag. Bars outside the blue band
       (95% CI) indicate serial correlation that can make p-values
       anti-conservative with complete shuffling.

    F) P-value Comparison: Solo vs Unbiased p-values per param set.
       The gap between them is the multiple-testing penalty.
       Larger gap = more selection bias being corrected.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, Optional

import numpy as np

if TYPE_CHECKING:
    from .results import OverfitResults
    from .cscv import PBOResults
    from .walkforward import WalkForwardResults
    from .diagnostics import AutocorrelationDiagnostic


def plot_null_distribution(
    results: OverfitResults,
    save_path: str | None = None,
):
    """
    Histogram of null distribution of best-Sharpe-across-all-params
    under permutation, with S* marked.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is required for plotting. Install with: pip install matplotlib")
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(results.null_best_sharpes, bins=50, density=True, alpha=0.7,
            color='steelblue', edgecolor='black',
            label='Null distribution (permuted best Sharpe)')
    ax.axvline(results.best_sharpe, color='red', linewidth=2, linestyle='--',
               label=f'S* = {results.best_sharpe:.4f}')
    ax.set_xlabel('Best Sharpe ratio across all parameter sets')
    ax.set_ylabel('Density')
    ax.set_title(
        f'Null Distribution of Best Sharpe Under Permutation\n'
        f'Unbiased p-value = {results.unbiased_pvalue:.4f}, '
        f'P(overfit) = {results.prob_overfit:.4f}'
    )
    ax.legend()
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()
    return fig


def plot_parameter_sensitivity(
    results: OverfitResults,
    save_path: str | None = None,
    show_individual: bool = True,
):
    """
    Grid of subplots — one per parameter dimension.

    For each parameter, the x-axis shows that parameter's values and the
    y-axis shows Sharpe. Three layers:

    1. Individual slices (thin grey lines): each holds all other params
       fixed and sweeps the focal parameter.
    2. Mean +/- 1 std (blue band): average Sharpe at each value.
    3. Best-set marker (red star): where the overall best falls.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is required for plotting. Install with: pip install matplotlib")
        return None

    param_keys = sorted({k for p in results.param_list for k in p})
    param_values = {
        k: sorted(set(p[k] for p in results.param_list))
        for k in param_keys
    }
    n_dims = len(param_keys)
    if n_dims == 0:
        print("No parameters to plot.")
        return None

    best_params = results.param_list[results.best_param_index]

    ncols = min(n_dims, 3)
    nrows = math.ceil(n_dims / ncols)
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(5.5 * ncols, 4 * nrows),
                             squeeze=False)

    for dim_idx, key in enumerate(param_keys):
        ax = axes[dim_idx // ncols][dim_idx % ncols]
        vals = param_values[key]
        is_numeric = all(isinstance(v, (int, float)) for v in vals)

        if is_numeric:
            x_positions = {v: v for v in vals}
        else:
            x_positions = {v: i for i, v in enumerate(vals)}

        other_keys = [k for k in param_keys if k != key]
        slices: Dict[tuple, list] = {}
        for i, p in enumerate(results.param_list):
            other_vals = tuple(p[k] for k in other_keys)
            slices.setdefault(other_vals, []).append(
                (x_positions[p[key]], results.original_sharpes[i])
            )

        if show_individual:
            for other_vals, points in slices.items():
                points.sort()
                xs, ys = zip(*points)
                ax.plot(xs, ys, color='grey', alpha=0.15, linewidth=0.7, zorder=1)

        val_sharpes = {v: [] for v in vals}
        for i, p in enumerate(results.param_list):
            val_sharpes[p[key]].append(results.original_sharpes[i])

        xs_mean = [x_positions[v] for v in vals]
        means = [np.mean(val_sharpes[v]) for v in vals]
        stds = [np.std(val_sharpes[v]) for v in vals]

        ax.fill_between(xs_mean,
                        [m - s for m, s in zip(means, stds)],
                        [m + s for m, s in zip(means, stds)],
                        alpha=0.25, color='steelblue', zorder=2)
        ax.plot(xs_mean, means, color='steelblue', linewidth=2,
                marker='o', markersize=4, zorder=3, label='mean +/- std')

        best_x = x_positions[best_params[key]]
        ax.axvline(best_x, color='red', linewidth=1, linestyle='--',
                   alpha=0.6, zorder=4)
        ax.plot(best_x, results.best_sharpe, marker='*', color='red',
                markersize=14, zorder=5,
                label=f'best (S*={results.best_sharpe:.2f})')

        ax.set_xlabel(key)
        ax.set_ylabel('Sharpe')
        ax.set_title(f'Sensitivity to {key}')
        if not is_numeric:
            ax.set_xticks(list(x_positions.values()))
            ax.set_xticklabels([str(v) for v in vals], rotation=45, ha='right')
        ax.legend(fontsize=7, loc='best')
        ax.grid(True, alpha=0.3)

    for dim_idx in range(n_dims, nrows * ncols):
        axes[dim_idx // ncols][dim_idx % ncols].set_visible(False)

    fig.suptitle('Parameter Sensitivity (overfit = spiky/narrow peaks)',
                 fontsize=13, y=1.01)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    else:
        plt.show()
    return fig


def plot_surface_2d(
    results: OverfitResults,
    param_x: str,
    param_y: str,
    save_path: str | None = None,
):
    """
    2D heatmap of Sharpe across two parameters, marginalizing over the rest.
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import TwoSlopeNorm
    except ImportError:
        print("matplotlib required")
        return None

    param_keys = sorted({k for p in results.param_list for k in p})
    if param_x not in param_keys or param_y not in param_keys:
        print(f"Parameters must be from: {param_keys}")
        return None

    xvals = sorted(set(p[param_x] for p in results.param_list))
    yvals = sorted(set(p[param_y] for p in results.param_list))

    grid = np.full((len(yvals), len(xvals)), np.nan)
    counts = np.zeros_like(grid)

    for i, p in enumerate(results.param_list):
        xi = xvals.index(p[param_x])
        yi = yvals.index(p[param_y])
        if np.isnan(grid[yi, xi]):
            grid[yi, xi] = 0.0
        grid[yi, xi] += results.original_sharpes[i]
        counts[yi, xi] += 1

    mask = counts > 0
    grid[mask] /= counts[mask]

    fig, ax = plt.subplots(figsize=(8, 6))

    vmin, vmax = np.nanmin(grid), np.nanmax(grid)
    if vmin < 0 < vmax:
        norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
        cmap = 'RdYlGn'
    else:
        norm = None
        cmap = 'viridis'

    im = ax.imshow(grid, aspect='auto', origin='lower', cmap=cmap, norm=norm)
    ax.set_xticks(range(len(xvals)))
    ax.set_xticklabels([f'{v}' for v in xvals], rotation=45, ha='right')
    ax.set_yticks(range(len(yvals)))
    ax.set_yticklabels([f'{v}' for v in yvals])
    ax.set_xlabel(param_x)
    ax.set_ylabel(param_y)

    best_params = results.param_list[results.best_param_index]
    if best_params[param_x] in xvals and best_params[param_y] in yvals:
        bx = xvals.index(best_params[param_x])
        by = yvals.index(best_params[param_y])
        ax.plot(bx, by, 'r*', markersize=15, markeredgecolor='black')

    plt.colorbar(im, ax=ax, label='Mean Sharpe')
    ax.set_title(f'Sharpe surface: {param_x} vs {param_y}\n'
                 f'(averaged over other params)')
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    else:
        plt.show()
    return fig


# -----------------------------------------------------------------------
# NEW: Walk-Forward IS vs OOS Degradation
# -----------------------------------------------------------------------

def plot_walkforward_degradation(wf_results, save_path=None):
    """
    Scatter of IS Sharpe vs OOS Sharpe per fold. Points near the 45-degree
    line = good generalization. Below = overfitting.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(8, 7))
    is_s, oos_s = wf_results.is_sharpes, wf_results.oos_sharpes
    n = len(is_s)
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, n))
    for i in range(n):
        ax.scatter(is_s[i], oos_s[i], c=[colors[i]], s=80, zorder=3,
                   edgecolors='black', linewidths=0.5)
        ax.annotate(f'F{i+1}', (is_s[i], oos_s[i]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8)
    lims = [min(min(is_s), min(oos_s)) - 0.5, max(max(is_s), max(oos_s)) + 0.5]
    ax.plot(lims, lims, 'k--', alpha=0.3, label='Perfect (WFE=1.0)')
    ax.plot(lims, [x * 0.5 for x in lims], 'r--', alpha=0.4, label='WFE=0.50')
    ax.axhline(0, color='grey', linewidth=0.5, alpha=0.5)
    ax.set_xlabel('In-Sample Sharpe')
    ax.set_ylabel('Out-of-Sample Sharpe')
    ax.set_title(f'Walk-Forward: IS vs OOS\nWFE = {wf_results.wfe:.3f}')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    return fig


def plot_pbo_distribution(pbo_results, save_path=None):
    """PBO logit histogram. Red = overfit (logit<0), Green = genuine (logit>=0)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    logits = pbo_results.logits[np.isfinite(pbo_results.logits)]
    ax.hist(logits[logits < 0], bins=30, alpha=0.7, color='#d9534f',
            edgecolor='black', label=f'Overfit: {pbo_results.pbo:.1%}')
    ax.hist(logits[logits >= 0], bins=30, alpha=0.7, color='#5cb85c',
            edgecolor='black', label=f'Genuine: {1-pbo_results.pbo:.1%}')
    ax.axvline(0, color='black', linewidth=2)
    ax.set_xlabel('Logit of OOS rank')
    ax.set_ylabel('Count')
    verdict = "LIKELY OVERFIT" if pbo_results.pbo > 0.5 else "BORDERLINE" if pbo_results.pbo > 0.3 else "ACCEPTABLE"
    ax.set_title(f'PBO = {pbo_results.pbo:.4f} [{verdict}]')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    return fig


def plot_autocorrelation(diagnostic, n_obs, save_path=None):
    """ACF bar chart with 95% confidence bands. Red bars = significant."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    lags = np.arange(1, len(diagnostic.acf_values) + 1)
    threshold = 2.0 / np.sqrt(n_obs)
    colors = ['#d9534f' if abs(v) > threshold else 'steelblue'
              for v in diagnostic.acf_values]
    ax.bar(lags, diagnostic.acf_values, color=colors, edgecolor='black',
           linewidth=0.5, alpha=0.8)
    ax.axhline(threshold, color='steelblue', linestyle='--', alpha=0.6)
    ax.axhline(-threshold, color='steelblue', linestyle='--', alpha=0.6)
    ax.axhline(0, color='black', linewidth=0.5)
    status = "AC DETECTED" if diagnostic.has_autocorrelation else "Clean"
    ax.set_xlabel('Lag')
    ax.set_ylabel('ACF')
    ax.set_title(f'Autocorrelation: {status} (LB p={diagnostic.ljung_box_pvalue:.4f})')
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    return fig


def plot_pvalue_comparison(results, save_path=None):
    """Solo vs Unbiased p-values. The gap = multiple-testing penalty."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))
    n = min(results.n_params, 40)
    ranks = np.arange(1, n + 1)
    solo = np.array([results.solo_pvalues[results.sort_indices[i]] for i in range(n)])
    unbiased = results.unbiased_pvalues[:n]
    ax.scatter(ranks, solo, c='steelblue', s=30, label='Solo p-value', zorder=3)
    ax.scatter(ranks, unbiased, c='#d9534f', s=30, marker='s', label='Unbiased p-value', zorder=3)
    for i in range(n):
        ax.plot([ranks[i], ranks[i]], [solo[i], unbiased[i]], color='grey', linewidth=0.3, alpha=0.5)
    ax.axhline(0.05, color='green', linestyle='--', alpha=0.5, label='alpha=0.05')
    false_disc = int(np.sum((solo < 0.05) & (unbiased >= 0.05)))
    ax.set_xlabel('Parameter set rank')
    ax.set_ylabel('P-value')
    ax.set_title(f'Solo vs Unbiased P-values ({false_disc} false discoveries averted)')
    ax.legend(fontsize=9)
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    return fig


def plot_overfit_dashboard(results, pbo_results=None, wf_results=None,
                           ac_diagnostic=None, n_obs=None, save_path=None):
    """
    6-panel diagnostic dashboard showing HOW overfitting is detected.

    Layout (2x3):
        A) Null Distribution    B) Parameter Surface    E) Autocorrelation
        C) WF Degradation       D) PBO Distribution     F) P-value Comparison
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import TwoSlopeNorm
    except ImportError:
        return None

    fig, axes = plt.subplots(2, 3, figsize=(20, 12))

    # A) Null Distribution
    ax = axes[0, 0]
    ax.hist(results.null_best_sharpes, bins=40, density=True, alpha=0.7,
            color='steelblue', edgecolor='black')
    ax.axvline(results.best_sharpe, color='red', linewidth=2, linestyle='--')
    ax.set_xlabel('Best Sharpe (permuted)')
    ax.set_ylabel('Density')
    ax.set_title(f'A) Null Distribution\np={results.unbiased_pvalue:.4f}',
                 fontsize=11, fontweight='bold')

    # B) Parameter Surface
    ax = axes[0, 1]
    param_keys = sorted({k for p in results.param_list for k in p})
    if len(param_keys) >= 2:
        px, py = param_keys[0], param_keys[1]
        xvals = sorted(set(p[px] for p in results.param_list))
        yvals = sorted(set(p[py] for p in results.param_list))
        grid = np.full((len(yvals), len(xvals)), np.nan)
        counts = np.zeros_like(grid)
        for i, p in enumerate(results.param_list):
            xi, yi = xvals.index(p[px]), yvals.index(p[py])
            if np.isnan(grid[yi, xi]): grid[yi, xi] = 0.0
            grid[yi, xi] += results.original_sharpes[i]
            counts[yi, xi] += 1
        mask = counts > 0
        grid[mask] /= counts[mask]
        vmin, vmax = np.nanmin(grid), np.nanmax(grid)
        norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax) if vmin < 0 < vmax else None
        im = ax.imshow(grid, aspect='auto', origin='lower',
                       cmap='RdYlGn' if norm else 'viridis', norm=norm)
        ax.set_xticks(range(len(xvals)))
        ax.set_xticklabels([f'{v}' for v in xvals], rotation=45, fontsize=7)
        ax.set_yticks(range(len(yvals)))
        ax.set_yticklabels([f'{v}' for v in yvals], fontsize=7)
        ax.set_xlabel(px, fontsize=9)
        ax.set_ylabel(py, fontsize=9)
        plt.colorbar(im, ax=ax, shrink=0.8)
        sa = results.surface_analysis()
        ax.set_title(f'B) Param Surface\nPlateau={sa["plateau_score"]:.2f}',
                     fontsize=11, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'Need 2+ params', ha='center', va='center', color='grey')
        ax.set_title('B) Parameter Surface', fontsize=11, fontweight='bold')

    # C) Walk-Forward
    ax = axes[1, 0]
    if wf_results is not None:
        for i in range(len(wf_results.is_sharpes)):
            ax.scatter(wf_results.is_sharpes[i], wf_results.oos_sharpes[i],
                       c='steelblue', s=60, edgecolors='black', linewidths=0.5)
        lims = [min(min(wf_results.is_sharpes), min(wf_results.oos_sharpes)) - 0.5,
                max(max(wf_results.is_sharpes), max(wf_results.oos_sharpes)) + 0.5]
        ax.plot(lims, lims, 'k--', alpha=0.3)
        ax.set_xlabel('IS Sharpe'); ax.set_ylabel('OOS Sharpe')
        ax.set_title(f'C) Walk-Forward\nWFE={wf_results.wfe:.3f}',
                     fontsize=11, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'Run walk_forward_analysis()', ha='center', va='center', color='grey')
        ax.set_title('C) Walk-Forward', fontsize=11, fontweight='bold')

    # D) PBO
    ax = axes[1, 1]
    if pbo_results is not None:
        logits = pbo_results.logits[np.isfinite(pbo_results.logits)]
        ax.hist(logits[logits < 0], bins=25, alpha=0.7, color='#d9534f', edgecolor='black')
        ax.hist(logits[logits >= 0], bins=25, alpha=0.7, color='#5cb85c', edgecolor='black')
        ax.axvline(0, color='black', linewidth=2)
        ax.set_xlabel('Logit(rank)'); ax.set_ylabel('Count')
        ax.set_title(f'D) PBO={pbo_results.pbo:.4f}', fontsize=11, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'Run compute_pbo()', ha='center', va='center', color='grey')
        ax.set_title('D) PBO Distribution', fontsize=11, fontweight='bold')

    # E) Autocorrelation
    ax = axes[0, 2]
    if ac_diagnostic is not None:
        obs = n_obs or 1000
        lags = np.arange(1, len(ac_diagnostic.acf_values) + 1)
        thr = 2.0 / np.sqrt(obs)
        bar_colors = ['#d9534f' if abs(v) > thr else 'steelblue' for v in ac_diagnostic.acf_values]
        ax.bar(lags, ac_diagnostic.acf_values, color=bar_colors, edgecolor='black', linewidth=0.5)
        ax.axhline(thr, color='steelblue', linestyle='--', alpha=0.5)
        ax.axhline(-thr, color='steelblue', linestyle='--', alpha=0.5)
        ax.set_xlabel('Lag'); ax.set_ylabel('ACF')
        ax.set_title(f'E) Autocorrelation\nrec: {ac_diagnostic.recommended_shuffle}',
                     fontsize=11, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'Run check_autocorrelation()', ha='center', va='center', color='grey')
        ax.set_title('E) Autocorrelation', fontsize=11, fontweight='bold')

    # F) P-value Comparison
    ax = axes[1, 2]
    n_show = min(results.n_params, 30)
    ranks = np.arange(1, n_show + 1)
    solo = np.array([results.solo_pvalues[results.sort_indices[i]] for i in range(n_show)])
    unbiased = results.unbiased_pvalues[:n_show]
    ax.scatter(ranks, solo, c='steelblue', s=20, label='Solo')
    ax.scatter(ranks, unbiased, c='#d9534f', s=20, marker='s', label='Unbiased')
    for i in range(n_show):
        ax.plot([ranks[i], ranks[i]], [solo[i], unbiased[i]], color='grey', linewidth=0.3, alpha=0.5)
    ax.axhline(0.05, color='green', linestyle='--', alpha=0.5)
    ax.set_xlabel('Rank'); ax.set_ylabel('P-value')
    fd = int(np.sum((solo < 0.05) & (unbiased >= 0.05)))
    ax.set_title(f'F) P-values ({fd} false disc. averted)', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8); ax.set_ylim(-0.02, 1.05)

    fig.suptitle('OVERFITTING DETECTION DASHBOARD', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Dashboard saved to {save_path}")
    else:
        plt.show()
    return fig

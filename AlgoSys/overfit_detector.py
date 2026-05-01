"""
Permutation-based overfitting detector for trading strategy backtests.

Inspired by the RANSAC/VarScreen approach to unbiased p-values (Timothy Masters).
Detects whether an optimized strategy's performance could have been achieved
by overfitting to noise, correcting for the multiple-testing problem inherent
in searching over many parameter combinations.

Usage:
    from overfit_detector import OverfitDetector

    def my_backtest(params, returns):
        # your backtest logic
        return sharpe_ratio

    detector = OverfitDetector(
        backtest_fn=my_backtest,
        returns=my_returns_series,
        param_grid={'lookback': [10, 20, 50], 'threshold': [0.5, 1.0, 1.5]},
    )
    results = detector.run()
    results.report()
    results.plot_null_distribution()
"""

from __future__ import annotations

import itertools
import math
import multiprocessing as mp
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Shuffling helpers
# ---------------------------------------------------------------------------

def _complete_shuffle(rng: np.random.Generator, returns: np.ndarray) -> np.ndarray:
    """IID shuffle — destroys all autocorrelation."""
    shuffled = returns.copy()
    rng.shuffle(shuffled)
    return shuffled


def _cyclic_permutation(rng: np.random.Generator, returns: np.ndarray) -> np.ndarray:
    """Cyclic shift — preserves all autocorrelation structure."""
    n = len(returns)
    shift = rng.integers(1, n)
    return np.roll(returns, shift)


def _block_bootstrap(rng: np.random.Generator, returns: np.ndarray,
                     block_size: int | None = None) -> np.ndarray:
    """
    Stationary block bootstrap — preserves local autocorrelation.
    Block size defaults to sqrt(n) if not specified.
    """
    n = len(returns)
    if block_size is None:
        block_size = max(2, int(np.sqrt(n)))

    result = np.empty(n, dtype=returns.dtype)
    pos = 0
    while pos < n:
        start = rng.integers(0, n)
        length = min(block_size, n - pos)
        indices = np.arange(start, start + length) % n
        result[pos:pos + length] = returns[indices]
        pos += length
    return result


# ---------------------------------------------------------------------------
# Worker function for multiprocessing
# ---------------------------------------------------------------------------

def _worker_run_pass(args):
    """
    Worker that runs one permutation pass (or the unpermuted pass).

    Returns (irep, sharpes_array) where sharpes_array has one Sharpe per
    parameter combination.
    """
    (irep, returns, param_list, backtest_fn, shuffle_method,
     block_size, seed, subsample_indices) = args

    rng = np.random.default_rng(seed)

    if irep == 0:
        shuffled = returns  # unpermuted
    else:
        if shuffle_method == 'complete':
            shuffled = _complete_shuffle(rng, returns)
        elif shuffle_method == 'cyclic':
            shuffled = _cyclic_permutation(rng, returns)
        elif shuffle_method == 'block':
            shuffled = _block_bootstrap(rng, returns, block_size)
        else:
            raise ValueError(f"Unknown shuffle method: {shuffle_method}")

    if subsample_indices is not None:
        eval_params = [param_list[i] for i in subsample_indices]
    else:
        eval_params = param_list

    sharpes = np.empty(len(eval_params), dtype=np.float64)
    for i, params in enumerate(eval_params):
        sharpes[i] = backtest_fn(params, shuffled)

    return irep, sharpes


# ---------------------------------------------------------------------------
# Results container
# ---------------------------------------------------------------------------

@dataclass
class OverfitResults:
    """Container for all overfitting detection results."""

    # Inputs
    param_list: list
    n_params: int
    n_reps: int
    shuffle_method: str

    # Pass 0 (unpermuted) results
    original_sharpes: np.ndarray          # Sharpe for each param set on real data
    best_param_index: int                 # index of best param set
    best_sharpe: float                    # S* — best Sharpe on real data

    # Permutation results
    solo_pvalues: np.ndarray              # solo p-value per param set
    unbiased_pvalue: float                # unbiased p-value for best param set
    unbiased_pvalues: np.ndarray          # unbiased p-value per param set (ordered)
    null_best_sharpes: np.ndarray         # best Sharpe from each permuted pass
    prob_overfit: float                   # fraction of permuted best >= S*
    deflated_sharpe: float                # S* adjusted for multiple testing

    # For ordered reporting
    sort_indices: np.ndarray              # indices that sort original_sharpes descending

    def report(self):
        """Print a summary report."""
        print("=" * 72)
        print("PERMUTATION-BASED OVERFITTING DETECTION REPORT")
        print("=" * 72)
        print(f"Parameter combinations tested : {self.n_params}")
        print(f"Permutation replications      : {self.n_reps}")
        print(f"Shuffle method                : {self.shuffle_method}")
        print()
        print(f"Best in-sample Sharpe (S*)     : {self.best_sharpe:.4f}")
        print(f"Best parameter set             : {self.param_list[self.best_param_index]}")
        print()
        print(f"Unbiased p-value (best set)    : {self.unbiased_pvalue:.4f}")
        print(f"Probability of overfitting     : {self.prob_overfit:.4f}")
        print(f"Deflated Sharpe ratio          : {self.deflated_sharpe:.4f}")
        print()

        # Top 20 parameter sets
        n_show = min(20, self.n_params)
        print(f"Top {n_show} parameter sets (sorted by unpermuted Sharpe):")
        print("-" * 72)
        print(f"{'Rank':>4}  {'Sharpe':>8}  {'Solo pval':>10}  {'Unbiased pval':>14}  Params")
        print("-" * 72)
        prior_pval = 0.0
        for rank in range(n_show):
            idx = self.sort_indices[rank]
            spval = self.solo_pvalues[idx]
            upval = self.unbiased_pvalues[rank]
            print(f"{rank+1:4d}  {self.original_sharpes[idx]:8.4f}  "
                  f"{spval:10.4f}  {upval:14.4f}  {self.param_list[idx]}")
        print("-" * 72)

    def plot_parameter_sensitivity(self, save_path: str | None = None,
                                    show_individual: bool = True):
        """
        Grid of subplots — one per parameter dimension.

        For each parameter, the x-axis shows that parameter's values and the
        y-axis shows Sharpe.  Three layers are drawn:

        1. **Individual slices** (thin grey lines): each line holds all *other*
           parameters fixed at one combination and sweeps the focal parameter.
           Spiky, divergent lines = fragile / overfit.  Smooth, parallel lines
           = robust edge.
        2. **Mean +/- 1 std** (blue band): the average Sharpe at each value of
           the focal parameter, marginalizing over all other params.
        3. **Best-set marker** (red star): where the overall best parameter set
           falls on this axis.

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        show_individual : bool
            If True, draw the individual slice lines (can be noisy with very
            large grids; set False for cleaner plots).
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib is required for plotting. "
                  "Install with: pip install matplotlib")
            return

        # Extract the parameter keys and their unique values
        param_keys = sorted({k for p in self.param_list for k in p})
        param_values = {
            k: sorted(set(p[k] for p in self.param_list))
            for k in param_keys
        }
        n_dims = len(param_keys)
        if n_dims == 0:
            print("No parameters to plot.")
            return

        best_params = self.param_list[self.best_param_index]

        ncols = min(n_dims, 3)
        nrows = math.ceil(n_dims / ncols)
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(5.5 * ncols, 4 * nrows),
                                 squeeze=False)

        for dim_idx, key in enumerate(param_keys):
            ax = axes[dim_idx // ncols][dim_idx % ncols]
            vals = param_values[key]
            is_numeric = all(isinstance(v, (int, float)) for v in vals)

            # Map value -> x-position
            if is_numeric:
                x_positions = {v: v for v in vals}
            else:
                x_positions = {v: i for i, v in enumerate(vals)}

            # Group param combos by "all other params" to get slices
            # other_key -> {focal_value: sharpe}
            other_keys = [k for k in param_keys if k != key]
            slices: Dict[tuple, list] = {}  # other_vals_tuple -> [(x, sharpe)]
            for i, p in enumerate(self.param_list):
                other_vals = tuple(p[k] for k in other_keys)
                slices.setdefault(other_vals, []).append(
                    (x_positions[p[key]], self.original_sharpes[i])
                )

            # Draw individual slices
            if show_individual:
                for other_vals, points in slices.items():
                    points.sort()
                    xs, ys = zip(*points)
                    ax.plot(xs, ys, color='grey', alpha=0.15, linewidth=0.7,
                            zorder=1)

            # Mean +/- std band
            val_sharpes = {v: [] for v in vals}
            for i, p in enumerate(self.param_list):
                val_sharpes[p[key]].append(self.original_sharpes[i])

            xs_mean = [x_positions[v] for v in vals]
            means = [np.mean(val_sharpes[v]) for v in vals]
            stds = [np.std(val_sharpes[v]) for v in vals]

            ax.fill_between(xs_mean,
                            [m - s for m, s in zip(means, stds)],
                            [m + s for m, s in zip(means, stds)],
                            alpha=0.25, color='steelblue', zorder=2)
            ax.plot(xs_mean, means, color='steelblue', linewidth=2,
                    marker='o', markersize=4, zorder=3, label='mean +/- std')

            # Mark the best parameter set
            best_x = x_positions[best_params[key]]
            ax.axvline(best_x, color='red', linewidth=1, linestyle='--',
                       alpha=0.6, zorder=4)
            ax.plot(best_x, self.best_sharpe, marker='*', color='red',
                    markersize=14, zorder=5, label=f'best (S*={self.best_sharpe:.2f})')

            ax.set_xlabel(key)
            ax.set_ylabel('Sharpe')
            ax.set_title(f'Sensitivity to {key}')
            if not is_numeric:
                ax.set_xticks(list(x_positions.values()))
                ax.set_xticklabels([str(v) for v in vals], rotation=45,
                                   ha='right')
            ax.legend(fontsize=7, loc='best')
            ax.grid(True, alpha=0.3)

        # Hide unused axes
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
        param_values = {
            k: sorted(set(p[k] for p in self.param_list))
            for k in param_keys
        }
        sharpes = self.original_sharpes
        best = self.best_sharpe
        best_params = self.param_list[self.best_param_index]

        # --- Global surface metrics ---
        frac_positive = np.mean(sharpes > 0)
        frac_above_half = np.mean(sharpes > 0.5 * best) if best > 0 else 0.0
        plateau_score = np.mean(sharpes > 0.7 * best) if best > 0 else 0.0

        # --- Neighbor analysis for best param set ---
        # Neighbors = param combos that differ in exactly 1 parameter by 1 step
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
            peak_to_neighbor = best / nb_mean if nb_mean != 0 else float('inf')
            cv_neighbors = np.std(nb, ddof=1) / abs(nb_mean) if nb_mean != 0 else float('inf')
        else:
            robustness_ratio = 1.0
            peak_to_neighbor = 1.0
            cv_neighbors = 0.0

        # --- Per-parameter sensitivity (first-order Sobol approximation) ---
        total_var = np.var(sharpes)
        per_param = {}
        for k in param_keys:
            vals = param_values[k]
            # E[S | param_k = v] for each v
            conditional_means = []
            for v in vals:
                subset = [sharpes[i] for i, p in enumerate(self.param_list) if p[k] == v]
                conditional_means.append(np.mean(subset))
            cm = np.array(conditional_means)

            # First-order Sobol index: Var(E[S|theta_k]) / Var(S)
            sobol_first = np.var(cm) / total_var if total_var > 1e-12 else 0.0

            # Marginal range: max - min of conditional means
            marginal_range = cm.max() - cm.min()

            per_param[k] = {
                'sobol_first': float(sobol_first),
                'marginal_range': float(marginal_range),
                'conditional_means': cm.tolist(),
                'values': [float(v) if isinstance(v, (int, float)) else v for v in vals],
            }

        return {
            'robustness_ratio': float(robustness_ratio),
            'frac_positive': float(frac_positive),
            'frac_above_half': float(frac_above_half),
            'plateau_score': float(plateau_score),
            'cv_neighbors': float(cv_neighbors),
            'peak_to_neighbor': float(peak_to_neighbor),
            'per_param_sensitivity': per_param,
        }

    def surface_report(self):
        """Print the surface analysis metrics with interpretation."""
        sa = self.surface_analysis()
        print("=" * 72)
        print("PARAMETER SURFACE ANALYSIS")
        print("=" * 72)

        def rating(val, good, bad, higher_is_better=True):
            if higher_is_better:
                if val >= good: return "GOOD"
                if val >= bad:  return "WARN"
                return "BAD "
            else:
                if val <= good: return "GOOD"
                if val <= bad:  return "WARN"
                return "BAD "

        rr = sa['robustness_ratio']
        fp = sa['frac_positive']
        fh = sa['frac_above_half']
        ps = sa['plateau_score']
        cv = sa['cv_neighbors']
        pn = sa['peak_to_neighbor']

        print(f"  Robustness ratio (neighbor/best)  : {rr:.4f}  "
              f"[{rating(rr, 0.8, 0.5)}]  (1.0 = flat plateau)")
        print(f"  Frac param space with Sharpe > 0  : {fp:.4f}  "
              f"[{rating(fp, 0.5, 0.2)}]  (>0.5 = structural edge)")
        print(f"  Frac above 50% of best            : {fh:.4f}  "
              f"[{rating(fh, 0.3, 0.1)}]")
        print(f"  Plateau score (>70% of best)      : {ps:.4f}  "
              f"[{rating(ps, 0.2, 0.05)}]")
        print(f"  CV of neighbors                   : {cv:.4f}  "
              f"[{rating(cv, 0.3, 0.5, higher_is_better=False)}]  (lower = more stable)")
        print(f"  Peak-to-neighbor ratio             : {pn:.4f}  "
              f"[{rating(pn, 1.2, 1.5, higher_is_better=False)}]  (1.0 = flat)")
        print()
        print("  Per-parameter sensitivity (Sobol first-order index):")
        print(f"    {'Parameter':<20} {'Sobol S1':>10} {'Marginal range':>15}")
        print(f"    {'-'*20} {'-'*10} {'-'*15}")
        for k, v in sorted(sa['per_param_sensitivity'].items(),
                           key=lambda x: -x[1]['sobol_first']):
            print(f"    {k:<20} {v['sobol_first']:>10.4f} {v['marginal_range']:>15.4f}")
        print("=" * 72)

    def plot_surface_2d(self, param_x: str, param_y: str,
                        save_path: str | None = None):
        """
        2D heatmap of Sharpe across two parameters, marginalizing over the rest.
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.colors import TwoSlopeNorm
        except ImportError:
            print("matplotlib required")
            return

        param_keys = sorted({k for p in self.param_list for k in p})
        if param_x not in param_keys or param_y not in param_keys:
            print(f"Parameters must be from: {param_keys}")
            return

        xvals = sorted(set(p[param_x] for p in self.param_list))
        yvals = sorted(set(p[param_y] for p in self.param_list))

        grid = np.full((len(yvals), len(xvals)), np.nan)
        counts = np.zeros_like(grid)

        for i, p in enumerate(self.param_list):
            xi = xvals.index(p[param_x])
            yi = yvals.index(p[param_y])
            if np.isnan(grid[yi, xi]):
                grid[yi, xi] = 0.0
            grid[yi, xi] += self.original_sharpes[i]
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

        best_params = self.param_list[self.best_param_index]
        if best_params[param_x] in xvals and best_params[param_y] in yvals:
            bx = xvals.index(best_params[param_x])
            by = yvals.index(best_params[param_y])
            ax.plot(bx, by, 'r*', markersize=15, markeredgecolor='black')

        plt.colorbar(im, ax=ax, label='Mean Sharpe')
        ax.set_title(f'Sharpe surface: {param_x} vs {param_y}\n(averaged over other params)')
        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
        return fig

    def plot_null_distribution(self, save_path: str | None = None):
        """
        Plot histogram of null distribution of best-Sharpe-across-all-params
        under permutation, with S* marked.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib is required for plotting. Install with: pip install matplotlib")
            return

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(self.null_best_sharpes, bins=50, density=True, alpha=0.7,
                color='steelblue', edgecolor='black', label='Null distribution (permuted best Sharpe)')
        ax.axvline(self.best_sharpe, color='red', linewidth=2, linestyle='--',
                   label=f'S* = {self.best_sharpe:.4f}')
        ax.set_xlabel('Best Sharpe ratio across all parameter sets')
        ax.set_ylabel('Density')
        ax.set_title(
            f'Null Distribution of Best Sharpe Under Permutation\n'
            f'Unbiased p-value = {self.unbiased_pvalue:.4f}, '
            f'P(overfit) = {self.prob_overfit:.4f}'
        )
        ax.legend()
        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150)
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
        return fig


# ---------------------------------------------------------------------------
# Main detector
# ---------------------------------------------------------------------------

class OverfitDetector:
    """
    Permutation-based overfitting detector for strategy backtests.

    Parameters
    ----------
    backtest_fn : callable
        Function with signature (params_dict, returns_array) -> float (Sharpe ratio).
        Must be picklable for multiprocessing (i.e., a module-level function,
        not a lambda or closure).
    returns : array-like
        Historical returns series (1-D).
    param_grid : dict
        Maps parameter names to lists of values to search over.
        All combinations are tested (Cartesian product).
    n_reps : int
        Number of Monte Carlo permutation replications (default 1000).
        Pass 0 is unpermuted; passes 1..n_reps are permuted.
    shuffle_method : str
        One of 'complete', 'cyclic', 'block'.
    block_size : int or None
        Block size for block bootstrap. Defaults to sqrt(n) if None.
    max_param_trials : int or None
        If set and the total grid is larger, randomly subsample this many
        parameter combinations per pass (same subset for every pass).
    n_workers : int or None
        Number of parallel workers. Defaults to all available cores.
    seed : int
        Master random seed for reproducibility.
    """

    def __init__(
        self,
        backtest_fn: Callable,
        returns: np.ndarray | Sequence[float],
        param_grid: Dict[str, List[Any]],
        n_reps: int = 1000,
        shuffle_method: str = 'complete',
        block_size: int | None = None,
        max_param_trials: int | None = None,
        n_workers: int | None = None,
        seed: int = 42,
    ):
        self.backtest_fn = backtest_fn
        self.returns = np.asarray(returns, dtype=np.float64)
        self.param_grid = param_grid
        self.n_reps = n_reps
        self.shuffle_method = shuffle_method
        self.block_size = block_size
        self.max_param_trials = max_param_trials
        self.n_workers = n_workers or os.cpu_count() or 1
        self.seed = seed

        # Build full parameter list (Cartesian product)
        keys = sorted(param_grid.keys())
        values = [param_grid[k] for k in keys]
        self._param_list = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
        self._keys = keys

    @property
    def param_list(self) -> list:
        return self._param_list

    def run(self) -> OverfitResults:
        """Execute the full permutation test and return results."""
        rng = np.random.default_rng(self.seed)
        n_params_full = len(self._param_list)

        # Handle subsampling if grid is too large
        subsample_indices = None
        if self.max_param_trials is not None and n_params_full > self.max_param_trials:
            subsample_indices = rng.choice(
                n_params_full, size=self.max_param_trials, replace=False
            )
            subsample_indices.sort()
            effective_param_list = [self._param_list[i] for i in subsample_indices]
            print(f"Grid has {n_params_full} combinations; subsampling to "
                  f"{self.max_param_trials} per pass.")
        else:
            effective_param_list = self._param_list

        n_params = len(effective_param_list)
        total_passes = 1 + self.n_reps  # pass 0 + permuted passes

        print(f"Running {total_passes} passes × {n_params} parameter sets "
              f"= {total_passes * n_params:,} backtests")
        print(f"Using {self.n_workers} worker(s), shuffle={self.shuffle_method}")

        # Generate seeds for each pass
        pass_seeds = rng.integers(0, 2**63, size=total_passes).tolist()

        # Build work items
        work_items = []
        for irep in range(total_passes):
            work_items.append((
                irep,
                self.returns,
                effective_param_list,
                self.backtest_fn,
                self.shuffle_method,
                self.block_size,
                pass_seeds[irep],
                None,  # subsample already applied above
            ))

        # Execute
        t0 = time.time()
        all_sharpes = [None] * total_passes  # irep -> sharpes array

        if self.n_workers == 1:
            # Single-process mode (easier to debug)
            for item in work_items:
                irep, sharpes = _worker_run_pass(item)
                all_sharpes[irep] = sharpes
                if irep == 0:
                    elapsed = time.time() - t0
                    print(f"  Pass 0 (unpermuted) done in {elapsed:.1f}s")
                elif irep % max(1, self.n_reps // 10) == 0:
                    elapsed = time.time() - t0
                    rate = irep / elapsed if elapsed > 0 else 0
                    eta = (self.n_reps - irep) / rate if rate > 0 else 0
                    print(f"  Pass {irep}/{self.n_reps} "
                          f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")
        else:
            # Multiprocessing
            completed = 0
            with mp.Pool(processes=self.n_workers) as pool:
                for irep, sharpes in pool.imap_unordered(_worker_run_pass, work_items):
                    all_sharpes[irep] = sharpes
                    completed += 1
                    if irep == 0:
                        elapsed = time.time() - t0
                        print(f"  Pass 0 (unpermuted) done in {elapsed:.1f}s")
                    elif completed % max(1, self.n_reps // 10) == 0:
                        elapsed = time.time() - t0
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (total_passes - completed) / rate if rate > 0 else 0
                        print(f"  {completed}/{total_passes} passes done "
                              f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

        elapsed = time.time() - t0
        print(f"All passes complete in {elapsed:.1f}s")

        # -----------------------------------------------------------------
        # Compute p-values using the RANSAC/VarScreen algorithm
        # -----------------------------------------------------------------
        original_sharpes = all_sharpes[0]  # shape (n_params,)

        # Sort indices: best (highest Sharpe) first
        sort_indices = np.argsort(-original_sharpes)

        # Initialize counts (start at 1 as in the reference code — the unpermuted
        # pass counts as one observation)
        solo_count = np.ones(n_params, dtype=np.int64)
        unbiased_count = np.ones(n_params, dtype=np.int64)

        null_best_sharpes = np.empty(self.n_reps, dtype=np.float64)

        for irep in range(1, total_passes):
            perm_sharpes = all_sharpes[irep]

            # Solo count: for each param set, did this permutation beat or match
            # its unpermuted Sharpe?
            for i in range(n_params):
                if perm_sharpes[i] >= original_sharpes[i]:
                    solo_count[i] += 1

            # Unbiased count: process from worst original Sharpe to best.
            # Track the running best permuted Sharpe as we go.
            # If at any rank position the running-best permuted Sharpe >= the
            # original Sharpe for that rank, increment its unbiased count.
            #
            # This mirrors the reference code exactly:
            #   best_crit = 1e60
            #   for i in range(n_competitors-1, -1, -1):  # worst to best
            #       k = sort_indices[i]
            #       if crits[i] < best_crit: best_crit = crits[i]
            #       if best_crit <= original_crits[k]: unbiased_count[k] += 1
            #
            # But note: the reference MINIMIZES criterion (error), while we
            # MAXIMIZE Sharpe. So we flip the comparisons.

            running_best = -np.inf
            for rank in range(n_params - 1, -1, -1):  # worst to best
                idx = sort_indices[rank]
                if perm_sharpes[idx] > running_best:
                    running_best = perm_sharpes[idx]
                if running_best >= original_sharpes[idx]:
                    unbiased_count[idx] += 1

            # The best Sharpe across ALL param sets in this permutation
            null_best_sharpes[irep - 1] = np.max(perm_sharpes)

        # Compute p-values
        total_obs = 1 + self.n_reps  # unpermuted + permuted
        solo_pvalues = solo_count / total_obs

        # Unbiased p-values ordered from best to worst, enforcing monotonicity
        raw_unbiased = unbiased_count / total_obs
        unbiased_pvalues_ordered = np.empty(n_params, dtype=np.float64)
        prior = 0.0
        for rank in range(n_params):
            idx = sort_indices[rank]
            pval = raw_unbiased[idx]
            if pval < prior:
                pval = prior
            unbiased_pvalues_ordered[rank] = pval
            prior = pval

        best_idx = sort_indices[0]
        best_sharpe = original_sharpes[best_idx]
        unbiased_pvalue = unbiased_pvalues_ordered[0]

        # Probability of overfitting
        prob_overfit = np.mean(null_best_sharpes >= best_sharpe)

        # Deflated Sharpe ratio
        # Adjust S* by subtracting the expected maximum Sharpe under the null
        # (the mean of the null best-Sharpe distribution)
        null_mean = np.mean(null_best_sharpes)
        null_std = np.std(null_best_sharpes, ddof=1) if self.n_reps > 1 else 1.0
        deflated_sharpe = (best_sharpe - null_mean) / null_std if null_std > 0 else 0.0

        # Map subsample indices back to full param list if needed
        if subsample_indices is not None:
            report_param_list = effective_param_list
        else:
            report_param_list = self._param_list

        return OverfitResults(
            param_list=report_param_list,
            n_params=n_params,
            n_reps=self.n_reps,
            shuffle_method=self.shuffle_method,
            original_sharpes=original_sharpes,
            best_param_index=int(best_idx),
            best_sharpe=float(best_sharpe),
            solo_pvalues=solo_pvalues,
            unbiased_pvalue=float(unbiased_pvalue),
            unbiased_pvalues=unbiased_pvalues_ordered,
            null_best_sharpes=null_best_sharpes,
            prob_overfit=float(prob_overfit),
            deflated_sharpe=float(deflated_sharpe),
            sort_indices=sort_indices,
        )


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

def _demo_backtest(params: dict, returns: np.ndarray) -> float:
    """
    Toy backtest: momentum strategy.
    Goes long when rolling mean > threshold, flat otherwise.
    Returns annualized Sharpe (assuming daily returns).
    """
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

    strat_returns = strat_returns[lookback:]  # drop warmup
    if len(strat_returns) == 0:
        return 0.0
    mean_r = np.mean(strat_returns)
    std_r = np.std(strat_returns, ddof=1)
    if std_r < 1e-12:
        return 0.0
    return (mean_r / std_r) * np.sqrt(252)


if __name__ == '__main__':
    print("Running demo with synthetic data...\n")

    # Generate synthetic returns with NO real signal (pure noise)
    rng = np.random.default_rng(123)
    returns = rng.normal(0.0002, 0.01, size=1000)  # ~1000 days

    param_grid = {
        'lookback': [5, 10, 20, 40, 60, 80, 100],
        'threshold': [-0.001, 0.0, 0.0002, 0.0005, 0.001, 0.002],
    }

    detector = OverfitDetector(
        backtest_fn=_demo_backtest,
        returns=returns,
        param_grid=param_grid,
        n_reps=200,        # use more (1000+) for real work
        shuffle_method='complete',
        n_workers=1,       # set to None for all cores
        seed=42,
    )

    results = detector.run()
    print()
    results.report()

    # Uncomment to show the plots:
    # results.plot_null_distribution()
    # results.plot_parameter_sensitivity()

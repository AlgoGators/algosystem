"""
Generate PNG examples showing overfit vs. real-edge detection for strategies
with 2, 3, 4, and 5 signal parameters.

For each signal count, runs the same strategy family on:
    - pure noise data  -> should flag as OVERFIT
    - regime-trending data  -> should flag as REAL EDGE

Outputs 4 PNGs to ./signal_count_examples/.
"""

# Pin BLAS threads BEFORE importing numpy to avoid OpenBLAS alloc errors
import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from algosystemv2.overfitting.detector import OverfitDetector
from algosystemv2.overfitting.data_generators import (
    generate_noise,
    generate_trending,
)
from algosystemv2.overfitting.strategies._utils import sharpe


# ---------------------------------------------------------------------------
# Backtest functions with 2, 3, 4, 5 parameters (module-level = picklable)
# ---------------------------------------------------------------------------


def backtest_2sig(params, returns):
    """2 signals: fast MA crossover with threshold."""
    lb = params["lookback"]
    th = params["threshold"]
    n = len(returns)
    if n <= lb + 1:
        return 0.0
    cs = np.cumsum(returns)
    ma = np.zeros(n)
    ma[lb:] = (cs[lb:] - cs[: n - lb]) / lb
    sig = np.where(ma > th, 1.0, np.where(ma < -th, -1.0, 0.0))
    return sharpe(sig[lb:-1] * returns[lb + 1 :])


def backtest_3sig(params, returns):
    """3 signals: dual MA + threshold."""
    flb = params["fast_lookback"]
    slb = params["slow_lookback"]
    th = params["threshold"]
    n = len(returns)
    warm = max(flb, slb)
    if n <= warm + 1:
        return 0.0
    cs = np.cumsum(returns)
    fma = np.zeros(n)
    sma = np.zeros(n)
    fma[flb:] = (cs[flb:] - cs[: n - flb]) / flb
    sma[slb:] = (cs[slb:] - cs[: n - slb]) / slb
    sig = np.zeros(n)
    for i in range(warm, n):
        if fma[i] > th and sma[i] > th:
            sig[i] = 1.0
        elif fma[i] < -th and sma[i] < -th:
            sig[i] = -1.0
    return sharpe(sig[warm:-1] * returns[warm + 1 :])


def backtest_4sig(params, returns):
    """4 signals: dual MA + threshold + vol filter."""
    flb = params["fast_lookback"]
    slb = params["slow_lookback"]
    th = params["threshold"]
    vf = params["vol_filter"]
    n = len(returns)
    warm = max(flb, slb, vf)
    if n <= warm + 1:
        return 0.0
    cs = np.cumsum(returns)
    fma = np.zeros(n)
    sma = np.zeros(n)
    fma[flb:] = (cs[flb:] - cs[: n - flb]) / flb
    sma[slb:] = (cs[slb:] - cs[: n - slb]) / slb
    # rolling std for vol filter
    vol = np.zeros(n)
    for i in range(vf, n):
        vol[i] = np.std(returns[i - vf : i], ddof=1)
    vol_median = np.median(vol[vf:]) if (n > vf) else 0.0
    sig = np.zeros(n)
    for i in range(warm, n):
        if vol[i] > vol_median * 1.5:  # skip high-vol periods
            continue
        if fma[i] > th and sma[i] > th:
            sig[i] = 1.0
        elif fma[i] < -th and sma[i] < -th:
            sig[i] = -1.0
    return sharpe(sig[warm:-1] * returns[warm + 1 :])


def backtest_5sig(params, returns):
    """5 signals: dual MA + threshold + vol filter + momentum confirmation."""
    flb = params["fast_lookback"]
    slb = params["slow_lookback"]
    th = params["threshold"]
    vf = params["vol_filter"]
    mo = params["momentum_lb"]
    n = len(returns)
    warm = max(flb, slb, vf, mo)
    if n <= warm + 1:
        return 0.0
    cs = np.cumsum(returns)
    fma = np.zeros(n)
    sma = np.zeros(n)
    fma[flb:] = (cs[flb:] - cs[: n - flb]) / flb
    sma[slb:] = (cs[slb:] - cs[: n - slb]) / slb
    mom = np.zeros(n)
    mom[mo:] = cs[mo:] - cs[: n - mo]  # cumulative return over mo days
    vol = np.zeros(n)
    for i in range(vf, n):
        vol[i] = np.std(returns[i - vf : i], ddof=1)
    vol_median = np.median(vol[vf:]) if (n > vf) else 0.0
    sig = np.zeros(n)
    for i in range(warm, n):
        if vol[i] > vol_median * 1.5:
            continue
        if fma[i] > th and sma[i] > th and mom[i] > 0:
            sig[i] = 1.0
        elif fma[i] < -th and sma[i] < -th and mom[i] < 0:
            sig[i] = -1.0
    return sharpe(sig[warm:-1] * returns[warm + 1 :])


# ---------------------------------------------------------------------------
# Parameter grids (kept small for fast iteration)
# ---------------------------------------------------------------------------

GRIDS = {
    2: {"lookback": [5, 10, 20, 30, 50, 80], "threshold": [0.0, 0.0005, 0.001, 0.002]},
    3: {
        "fast_lookback": [5, 10, 20],
        "slow_lookback": [40, 60, 80, 100],
        "threshold": [0.0, 0.0005, 0.001],
    },
    4: {
        "fast_lookback": [5, 10, 20],
        "slow_lookback": [40, 60, 80],
        "threshold": [0.0, 0.0005],
        "vol_filter": [10, 20, 30],
    },
    5: {
        "fast_lookback": [5, 10, 20],
        "slow_lookback": [40, 80],
        "threshold": [0.0, 0.0005],
        "vol_filter": [10, 20],
        "momentum_lb": [20, 60],
    },
}

BACKTESTS = {2: backtest_2sig, 3: backtest_3sig, 4: backtest_4sig, 5: backtest_5sig}


# ---------------------------------------------------------------------------
# Run detector + plot a single comparison figure for a given n_signals
# ---------------------------------------------------------------------------


def run_and_plot(n_signals, out_path, n_reps=60, n_obs=1500):
    bt = BACKTESTS[n_signals]
    grid = GRIDS[n_signals]
    n_combos = int(np.prod([len(v) for v in grid.values()]))
    print(flush=True)
    print(f"\n=== {n_signals} signals === grid={grid}, combos={n_combos}")

    # Two datasets
    noise_returns = generate_noise(n=n_obs, seed=42)
    trend_returns = generate_trending(n=n_obs, seed=42)

    # Run detector on each (single-worker, complete shuffle)
    print(flush=True)
    print(f"  running on NOISE...")
    det_noise = OverfitDetector(
        backtest_fn=bt,
        returns=noise_returns,
        param_grid=grid,
        n_reps=n_reps,
        shuffle_method="complete",
        n_workers=1,
        seed=42,
    )
    res_noise = det_noise.run()

    print(flush=True)
    print(f"  running on TRENDING...")
    det_trend = OverfitDetector(
        backtest_fn=bt,
        returns=trend_returns,
        param_grid=grid,
        n_reps=n_reps,
        shuffle_method="complete",
        n_workers=1,
        seed=42,
    )
    res_trend = det_trend.run()

    sa_noise = res_noise.surface_analysis()
    sa_trend = res_trend.surface_analysis()

    # ---- Plot: 2 rows (noise=OVERFIT, trend=REAL), 3 columns ----
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle(
        f"{n_signals}-Signal Strategy: Overfit (noise, top) vs Real Edge (trending, bottom)",
        fontsize=14,
        fontweight="bold",
    )

    def plot_row(ax_row, res, sa, label, color):
        # --- Col 1: Null distribution ---
        ax = ax_row[0]
        nb = res.null_best_sharpes
        ax.hist(
            nb,
            bins=30,
            alpha=0.6,
            color="steelblue",
            density=True,
            label=f"Null (n={len(nb)})",
        )
        ax.axvline(
            res.best_sharpe,
            color=color,
            linestyle="--",
            lw=2,
            label=f"Real S*={res.best_sharpe:.2f}",
        )
        ax.set_title(
            f"{label}: Null Distribution\np={res.prob_overfit:.4f}",
            color=color,
            fontweight="bold",
        )
        ax.set_xlabel("Best Sharpe (permuted)")
        ax.set_ylabel("Density")
        ax.legend(loc="upper right", fontsize=8)

        # --- Col 2: Parameter surface (2D slice if >2 dims) ---
        ax = ax_row[1]
        sharpes = res.original_sharpes
        # Pick first two parameter axes for the heatmap
        keys = sorted(grid.keys())
        k0, k1 = keys[0], keys[1]
        v0, v1 = grid[k0], grid[k1]
        # Average over other dimensions
        grid_shape = tuple(len(grid[k]) for k in keys)
        surf = sharpes.reshape(grid_shape)
        # Average over axes 2+
        while surf.ndim > 2:
            surf = surf.mean(axis=-1)
        im = ax.imshow(
            surf, aspect="auto", origin="lower", cmap="RdYlGn", vmin=-1, vmax=1
        )
        ax.set_xticks(range(len(v1)))
        ax.set_xticklabels(v1, rotation=45, fontsize=8)
        ax.set_yticks(range(len(v0)))
        ax.set_yticklabels(v0, fontsize=8)
        ax.set_xlabel(k1)
        ax.set_ylabel(k0)
        ax.set_title(
            f"{label}: Param Surface\n"
            f"Plateau={sa['plateau_score']:.3f} | Robust={sa['robustness_ratio']:.3f}",
            color=color,
            fontweight="bold",
        )
        # Mark the best point
        best_idx = res.best_param_index
        # locate best in 2D projection: flatten then unravel original
        best_multi = np.unravel_index(best_idx, grid_shape)
        # Project to 2D axes (first two params)
        best_y, best_x = best_multi[0], best_multi[1]
        ax.plot(
            best_x,
            best_y,
            marker="*",
            color="white",
            markersize=16,
            markeredgecolor="black",
        )
        plt.colorbar(im, ax=ax, shrink=0.7)

        # --- Col 3: Sorted Sharpe ranks w/ p-values ---
        ax = ax_row[2]
        sorted_sr = np.sort(sharpes)[::-1]
        ranks = np.arange(1, len(sorted_sr) + 1)
        ax.plot(
            ranks,
            sorted_sr,
            "o-",
            color=color,
            lw=1.5,
            markersize=4,
            label="Real Sharpes (sorted)",
        )
        null_mean = np.mean(nb)
        ax.axhline(
            null_mean, color="red", linestyle=":", label=f"Null mean={null_mean:.2f}"
        )
        ax.axhline(
            np.percentile(nb, 95),
            color="orange",
            linestyle=":",
            label=f"Null 95th %ile={np.percentile(nb, 95):.2f}",
        )
        ax.set_xlabel("Parameter rank (best first)")
        ax.set_ylabel("Sharpe")
        ax.set_title(
            f"{label}: Sharpe vs rank\nunbiased p={res.unbiased_pvalue:.4f}",
            color=color,
            fontweight="bold",
        )
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)

    plot_row(axes[0], res_noise, sa_noise, "OVERFIT", "firebrick")
    plot_row(axes[1], res_trend, sa_trend, "REAL EDGE", "darkgreen")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close()
    print(flush=True)
    print(f"  saved -> {out_path}")

    return {
        "n_signals": n_signals,
        "n_combos": n_combos,
        "overfit": {
            "best_sharpe": float(res_noise.best_sharpe),
            "prob_overfit": float(res_noise.prob_overfit),
            "unbiased_p": float(res_noise.unbiased_pvalue),
            "plateau": float(sa_noise["plateau_score"]),
            "robustness": float(sa_noise["robustness_ratio"]),
        },
        "real": {
            "best_sharpe": float(res_trend.best_sharpe),
            "prob_overfit": float(res_trend.prob_overfit),
            "unbiased_p": float(res_trend.unbiased_pvalue),
            "plateau": float(sa_trend["plateau_score"]),
            "robustness": float(sa_trend["robustness_ratio"]),
        },
    }


def main():
    out_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "signal_count_examples"
    )
    os.makedirs(out_dir, exist_ok=True)

    summaries = []
    for n_sig in [2, 3, 4, 5]:
        out = os.path.join(out_dir, f"{n_sig}_signal_overfit_vs_real.png")
        summary = run_and_plot(n_sig, out)
        summaries.append(summary)

    # Print final comparison table
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(flush=True)
    print(f"{'n_sig':>5} {'combos':>7} | {'OVERFIT':^30} | {'REAL EDGE':^30}")
    print(
        f"{'':>5} {'':>7} | {'S*   p    plat robust':^30} | {'S*   p    plat robust':^30}"
    )
    print("-" * 90)
    for s in summaries:
        of, rl = s["overfit"], s["real"]
        print(
            f"{s['n_signals']:>5} {s['n_combos']:>7} | "
            f"{of['best_sharpe']:>5.2f} {of['prob_overfit']:>5.3f} "
            f"{of['plateau']:>5.3f} {of['robustness']:>5.2f}  | "
            f"{rl['best_sharpe']:>5.2f} {rl['prob_overfit']:>5.3f} "
            f"{rl['plateau']:>5.3f} {rl['robustness']:>5.2f}"
        )
    print("=" * 90)


if __name__ == "__main__":
    main()

"""Matplotlib-backed validation chart renderer."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

import numpy as np

from algosystem.shared.errors import ValidationError


class MatplotlibChartRenderer:
    """ChartRenderer implementation backed by matplotlib."""

    def plot_null_distribution(self, results: object, save_path: object | None = None) -> object:
        """Render the permutation null distribution."""
        return plot_null_distribution(results, save_path=save_path)

    def plot_parameter_sensitivity(
        self,
        results: object,
        save_path: object | None = None,
        show_individual: bool = True,
    ) -> object:
        """Render per-parameter sensitivity."""
        return plot_parameter_sensitivity(
            results,
            save_path=save_path,
            show_individual=show_individual,
        )

    def plot_surface_2d(
        self,
        results: object,
        param_x: str,
        param_y: str,
        save_path: object | None = None,
    ) -> object:
        """Render a two-dimensional parameter surface."""
        return plot_surface_2d(results, param_x, param_y, save_path=save_path)

    def plot_overfit_dashboard(
        self,
        results: object,
        pbo_results: object | None = None,
        wf_results: object | None = None,
        ac_diagnostic: object | None = None,
        n_obs: int | None = None,
        save_path: object | None = None,
    ) -> object:
        """Render the combined overfitting dashboard."""
        return plot_overfit_dashboard(
            results,
            pbo_results=pbo_results,
            wf_results=wf_results,
            ac_diagnostic=ac_diagnostic,
            n_obs=n_obs,
            save_path=save_path,
        )


def plot_null_distribution(results, save_path: object | None = None):
    """Plot null distribution of best Sharpe under permutation."""

    def draw(plt):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(
            results.null_best_sharpes,
            bins=50,
            density=True,
            alpha=0.7,
            color="steelblue",
            edgecolor="black",
            label="Null distribution (permuted best Sharpe)",
        )
        ax.axvline(
            results.best_sharpe,
            color="red",
            linewidth=2,
            linestyle="--",
            label=f"S* = {results.best_sharpe:.4f}",
        )
        ax.set_xlabel("Best Sharpe ratio across all parameter sets")
        ax.set_ylabel("Density")
        ax.set_title(
            "Null Distribution of Best Sharpe Under Permutation\n"
            f"Unbiased p-value = {results.unbiased_pvalue:.4f}, "
            f"P(overfit) = {results.prob_overfit:.4f}"
        )
        ax.legend()
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def plot_parameter_sensitivity(
    results,
    save_path: object | None = None,
    show_individual: bool = True,
):
    """Plot Sharpe sensitivity for each parameter dimension."""

    def draw(plt):
        param_keys = sorted({key for params in results.param_list for key in params})
        param_values = {
            key: sorted({params[key] for params in results.param_list}) for key in param_keys
        }
        n_dims = len(param_keys)
        if n_dims == 0:
            raise ValidationError("no parameters to plot")

        best_params = results.param_list[results.best_param_index]
        ncols = min(n_dims, 3)
        nrows = math.ceil(n_dims / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            figsize=(5.5 * ncols, 4 * nrows),
            squeeze=False,
        )

        for dim_index, key in enumerate(param_keys):
            ax = axes[dim_index // ncols][dim_index % ncols]
            values = param_values[key]
            is_numeric = all(isinstance(value, (int, float)) for value in values)
            x_positions = {
                value: value if is_numeric else index for index, value in enumerate(values)
            }

            other_keys = [other for other in param_keys if other != key]
            slices: dict[tuple[object, ...], list[tuple[object, float]]] = {}
            for index, params in enumerate(results.param_list):
                other_values = tuple(params[other] for other in other_keys)
                slices.setdefault(other_values, []).append(
                    (x_positions[params[key]], results.original_sharpes[index])
                )

            if show_individual:
                for points in slices.values():
                    points.sort()
                    xs, ys = zip(*points)
                    ax.plot(xs, ys, color="grey", alpha=0.15, linewidth=0.7, zorder=1)

            value_sharpes = {value: [] for value in values}
            for index, params in enumerate(results.param_list):
                value_sharpes[params[key]].append(results.original_sharpes[index])

            xs_mean = [x_positions[value] for value in values]
            means = [np.mean(value_sharpes[value]) for value in values]
            stds = [np.std(value_sharpes[value]) for value in values]

            ax.fill_between(
                xs_mean,
                [mean - std for mean, std in zip(means, stds)],
                [mean + std for mean, std in zip(means, stds)],
                alpha=0.25,
                color="steelblue",
                zorder=2,
            )
            ax.plot(
                xs_mean,
                means,
                color="steelblue",
                linewidth=2,
                marker="o",
                markersize=4,
                zorder=3,
                label="mean +/- std",
            )

            best_x = x_positions[best_params[key]]
            ax.axvline(best_x, color="red", linewidth=1, linestyle="--", alpha=0.6, zorder=4)
            ax.plot(
                best_x,
                results.best_sharpe,
                marker="*",
                color="red",
                markersize=14,
                zorder=5,
                label=f"best (S*={results.best_sharpe:.2f})",
            )

            ax.set_xlabel(key)
            ax.set_ylabel("Sharpe")
            ax.set_title(f"Sensitivity to {key}")
            if not is_numeric:
                ax.set_xticks(list(x_positions.values()))
                ax.set_xticklabels([str(value) for value in values], rotation=45, ha="right")
            ax.legend(fontsize=7, loc="best")
            ax.grid(True, alpha=0.3)

        for dim_index in range(n_dims, nrows * ncols):
            axes[dim_index // ncols][dim_index % ncols].set_visible(False)

        fig.suptitle(
            "Parameter Sensitivity (overfit = spiky/narrow peaks)",
            fontsize=13,
            y=1.01,
        )
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def plot_surface_2d(
    results,
    param_x: str,
    param_y: str,
    save_path: object | None = None,
):
    """Plot a 2-D heatmap of Sharpe across two parameters."""

    def draw(plt):
        from matplotlib.colors import TwoSlopeNorm

        param_keys = sorted({key for params in results.param_list for key in params})
        if param_x not in param_keys or param_y not in param_keys:
            raise ValidationError(f"parameters must be from: {param_keys}")

        xvalues = sorted({params[param_x] for params in results.param_list})
        yvalues = sorted({params[param_y] for params in results.param_list})
        grid, _ = _mean_surface_grid(results, param_x, param_y, xvalues, yvalues)

        fig, ax = plt.subplots(figsize=(8, 6))
        vmin, vmax = np.nanmin(grid), np.nanmax(grid)
        if vmin < 0 < vmax:
            norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
            cmap = "RdYlGn"
        else:
            norm = None
            cmap = "viridis"

        image = ax.imshow(grid, aspect="auto", origin="lower", cmap=cmap, norm=norm)
        ax.set_xticks(range(len(xvalues)))
        ax.set_xticklabels([f"{value}" for value in xvalues], rotation=45, ha="right")
        ax.set_yticks(range(len(yvalues)))
        ax.set_yticklabels([f"{value}" for value in yvalues])
        ax.set_xlabel(param_x)
        ax.set_ylabel(param_y)

        best_params = results.param_list[results.best_param_index]
        if best_params[param_x] in xvalues and best_params[param_y] in yvalues:
            best_x = xvalues.index(best_params[param_x])
            best_y = yvalues.index(best_params[param_y])
            ax.plot(best_x, best_y, "r*", markersize=15, markeredgecolor="black")

        fig.colorbar(image, ax=ax, label="Mean Sharpe")
        ax.set_title(f"Sharpe surface: {param_x} vs {param_y}\n(averaged over other params)")
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def plot_walkforward_degradation(wf_results, save_path: object | None = None):
    """Plot in-sample versus out-of-sample Sharpe per walk-forward fold."""

    def draw(plt):
        fig, ax = plt.subplots(figsize=(8, 7))
        is_sharpes = wf_results.is_sharpes
        oos_sharpes = wf_results.oos_sharpes
        colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(is_sharpes)))
        for index in range(len(is_sharpes)):
            ax.scatter(
                is_sharpes[index],
                oos_sharpes[index],
                c=[colors[index]],
                s=80,
                zorder=3,
                edgecolors="black",
                linewidths=0.5,
            )
            ax.annotate(
                f"F{index + 1}",
                (is_sharpes[index], oos_sharpes[index]),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=8,
            )
        limits = [
            min(min(is_sharpes), min(oos_sharpes)) - 0.5,
            max(max(is_sharpes), max(oos_sharpes)) + 0.5,
        ]
        ax.plot(limits, limits, "k--", alpha=0.3, label="Perfect (WFE=1.0)")
        ax.plot(limits, [value * 0.5 for value in limits], "r--", alpha=0.4, label="WFE=0.50")
        ax.axhline(0, color="grey", linewidth=0.5, alpha=0.5)
        ax.set_xlabel("In-Sample Sharpe")
        ax.set_ylabel("Out-of-Sample Sharpe")
        ax.set_title(f"Walk-Forward: IS vs OOS\nWFE = {wf_results.wfe:.3f}")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def plot_pbo_distribution(pbo_results, save_path: object | None = None):
    """Plot the PBO logit distribution."""

    def draw(plt):
        fig, ax = plt.subplots(figsize=(10, 6))
        logits = pbo_results.logits[np.isfinite(pbo_results.logits)]
        ax.hist(
            logits[logits < 0],
            bins=30,
            alpha=0.7,
            color="#d9534f",
            edgecolor="black",
            label=f"Overfit: {pbo_results.pbo:.1%}",
        )
        ax.hist(
            logits[logits >= 0],
            bins=30,
            alpha=0.7,
            color="#5cb85c",
            edgecolor="black",
            label=f"Genuine: {1 - pbo_results.pbo:.1%}",
        )
        ax.axvline(0, color="black", linewidth=2)
        ax.set_xlabel("Logit of OOS rank")
        ax.set_ylabel("Count")
        verdict = (
            "LIKELY OVERFIT"
            if pbo_results.pbo > 0.5
            else "BORDERLINE" if pbo_results.pbo > 0.3 else "ACCEPTABLE"
        )
        ax.set_title(f"PBO = {pbo_results.pbo:.4f} [{verdict}]")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def plot_autocorrelation(diagnostic, n_obs: int, save_path: object | None = None):
    """Plot ACF bars with 95 percent confidence bands."""

    def draw(plt):
        fig, ax = plt.subplots(figsize=(10, 5))
        lags = np.arange(1, len(diagnostic.acf_values) + 1)
        threshold = 2.0 / np.sqrt(n_obs)
        colors = [
            "#d9534f" if abs(value) > threshold else "steelblue" for value in diagnostic.acf_values
        ]
        ax.bar(
            lags,
            diagnostic.acf_values,
            color=colors,
            edgecolor="black",
            linewidth=0.5,
            alpha=0.8,
        )
        ax.axhline(threshold, color="steelblue", linestyle="--", alpha=0.6)
        ax.axhline(-threshold, color="steelblue", linestyle="--", alpha=0.6)
        ax.axhline(0, color="black", linewidth=0.5)
        status = "AC DETECTED" if diagnostic.has_autocorrelation else "Clean"
        ax.set_xlabel("Lag")
        ax.set_ylabel("ACF")
        ax.set_title(f"Autocorrelation: {status} (LB p={diagnostic.ljung_box_pvalue:.4f})")
        ax.grid(True, alpha=0.3, axis="y")
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def plot_pvalue_comparison(results, save_path: object | None = None):
    """Plot solo versus unbiased p-values by parameter rank."""

    def draw(plt):
        fig, ax = plt.subplots(figsize=(12, 6))
        n_show = min(results.n_params, 40)
        ranks = np.arange(1, n_show + 1)
        solo = np.array(
            [results.solo_pvalues[results.sort_indices[index]] for index in range(n_show)]
        )
        unbiased = results.unbiased_pvalues[:n_show]
        ax.scatter(ranks, solo, c="steelblue", s=30, label="Solo p-value", zorder=3)
        ax.scatter(
            ranks,
            unbiased,
            c="#d9534f",
            s=30,
            marker="s",
            label="Unbiased p-value",
            zorder=3,
        )
        for index in range(n_show):
            ax.plot(
                [ranks[index], ranks[index]],
                [solo[index], unbiased[index]],
                color="grey",
                linewidth=0.3,
                alpha=0.5,
            )
        ax.axhline(0.05, color="green", linestyle="--", alpha=0.5, label="alpha=0.05")
        false_discoveries = int(np.sum((solo < 0.05) & (unbiased >= 0.05)))
        ax.set_xlabel("Parameter set rank")
        ax.set_ylabel("P-value")
        ax.set_title(f"Solo vs Unbiased P-values ({false_discoveries} false discoveries averted)")
        ax.legend(fontsize=9)
        ax.set_ylim(-0.02, 1.05)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def plot_overfit_dashboard(
    results,
    pbo_results=None,
    wf_results=None,
    ac_diagnostic=None,
    n_obs: int | None = None,
    save_path: object | None = None,
):
    """Plot a six-panel diagnostic dashboard."""

    def draw(plt):
        from matplotlib.colors import TwoSlopeNorm

        fig, axes = plt.subplots(2, 3, figsize=(20, 12))

        ax = axes[0, 0]
        ax.hist(
            results.null_best_sharpes,
            bins=40,
            density=True,
            alpha=0.7,
            color="steelblue",
            edgecolor="black",
        )
        ax.axvline(results.best_sharpe, color="red", linewidth=2, linestyle="--")
        ax.set_xlabel("Best Sharpe (permuted)")
        ax.set_ylabel("Density")
        ax.set_title(f"A) Null Distribution\np={results.unbiased_pvalue:.4f}", fontsize=11)

        ax = axes[0, 1]
        param_keys = sorted({key for params in results.param_list for key in params})
        if len(param_keys) >= 2:
            param_x, param_y = param_keys[0], param_keys[1]
            xvalues = sorted({params[param_x] for params in results.param_list})
            yvalues = sorted({params[param_y] for params in results.param_list})
            grid, _ = _mean_surface_grid(results, param_x, param_y, xvalues, yvalues)
            vmin, vmax = np.nanmin(grid), np.nanmax(grid)
            norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax) if vmin < 0 < vmax else None
            image = ax.imshow(
                grid,
                aspect="auto",
                origin="lower",
                cmap="RdYlGn" if norm else "viridis",
                norm=norm,
            )
            ax.set_xticks(range(len(xvalues)))
            ax.set_xticklabels([f"{value}" for value in xvalues], rotation=45, fontsize=7)
            ax.set_yticks(range(len(yvalues)))
            ax.set_yticklabels([f"{value}" for value in yvalues], fontsize=7)
            ax.set_xlabel(param_x, fontsize=9)
            ax.set_ylabel(param_y, fontsize=9)
            fig.colorbar(image, ax=ax, shrink=0.8)
            surface = results.surface_analysis()
            ax.set_title(f"B) Param Surface\nPlateau={surface['plateau_score']:.2f}", fontsize=11)
        else:
            ax.text(0.5, 0.5, "Need 2+ params", ha="center", va="center", color="grey")
            ax.set_title("B) Parameter Surface", fontsize=11)

        ax = axes[1, 0]
        if wf_results is not None:
            for index in range(len(wf_results.is_sharpes)):
                ax.scatter(
                    wf_results.is_sharpes[index],
                    wf_results.oos_sharpes[index],
                    c="steelblue",
                    s=60,
                    edgecolors="black",
                    linewidths=0.5,
                )
            limits = [
                min(min(wf_results.is_sharpes), min(wf_results.oos_sharpes)) - 0.5,
                max(max(wf_results.is_sharpes), max(wf_results.oos_sharpes)) + 0.5,
            ]
            ax.plot(limits, limits, "k--", alpha=0.3)
            ax.set_xlabel("IS Sharpe")
            ax.set_ylabel("OOS Sharpe")
            ax.set_title(f"C) Walk-Forward\nWFE={wf_results.wfe:.3f}", fontsize=11)
        else:
            ax.text(0.5, 0.5, "No walk-forward results", ha="center", va="center", color="grey")
            ax.set_title("C) Walk-Forward", fontsize=11)

        ax = axes[1, 1]
        if pbo_results is not None:
            logits = pbo_results.logits[np.isfinite(pbo_results.logits)]
            ax.hist(logits[logits < 0], bins=25, alpha=0.7, color="#d9534f", edgecolor="black")
            ax.hist(logits[logits >= 0], bins=25, alpha=0.7, color="#5cb85c", edgecolor="black")
            ax.axvline(0, color="black", linewidth=2)
            ax.set_xlabel("Logit(rank)")
            ax.set_ylabel("Count")
            ax.set_title(f"D) PBO={pbo_results.pbo:.4f}", fontsize=11)
        else:
            ax.text(0.5, 0.5, "No PBO results", ha="center", va="center", color="grey")
            ax.set_title("D) PBO Distribution", fontsize=11)

        ax = axes[0, 2]
        if ac_diagnostic is not None:
            obs = n_obs or 1000
            lags = np.arange(1, len(ac_diagnostic.acf_values) + 1)
            threshold = 2.0 / np.sqrt(obs)
            colors = [
                "#d9534f" if abs(value) > threshold else "steelblue"
                for value in ac_diagnostic.acf_values
            ]
            ax.bar(lags, ac_diagnostic.acf_values, color=colors, edgecolor="black", linewidth=0.5)
            ax.axhline(threshold, color="steelblue", linestyle="--", alpha=0.5)
            ax.axhline(-threshold, color="steelblue", linestyle="--", alpha=0.5)
            ax.set_xlabel("Lag")
            ax.set_ylabel("ACF")
            ax.set_title(
                f"E) Autocorrelation\nrec: {ac_diagnostic.recommended_shuffle}", fontsize=11
            )
        else:
            ax.text(
                0.5, 0.5, "No autocorrelation diagnostic", ha="center", va="center", color="grey"
            )
            ax.set_title("E) Autocorrelation", fontsize=11)

        ax = axes[1, 2]
        n_show = min(results.n_params, 30)
        ranks = np.arange(1, n_show + 1)
        solo = np.array(
            [results.solo_pvalues[results.sort_indices[index]] for index in range(n_show)]
        )
        unbiased = results.unbiased_pvalues[:n_show]
        ax.scatter(ranks, solo, c="steelblue", s=20, label="Solo")
        ax.scatter(ranks, unbiased, c="#d9534f", s=20, marker="s", label="Unbiased")
        for index in range(n_show):
            ax.plot(
                [ranks[index], ranks[index]],
                [solo[index], unbiased[index]],
                color="grey",
                linewidth=0.3,
                alpha=0.5,
            )
        ax.axhline(0.05, color="green", linestyle="--", alpha=0.5)
        ax.set_xlabel("Rank")
        ax.set_ylabel("P-value")
        false_discoveries = int(np.sum((solo < 0.05) & (unbiased >= 0.05)))
        ax.set_title(f"F) P-values ({false_discoveries} false disc. averted)", fontsize=11)
        ax.legend(fontsize=8)
        ax.set_ylim(-0.02, 1.05)

        fig.suptitle("OVERFITTING DETECTION DASHBOARD", fontsize=16, y=1.02)
        fig.tight_layout()
        return fig

    return _render_matplotlib(draw, save_path)


def _mean_surface_grid(results, param_x: str, param_y: str, xvalues: list, yvalues: list):
    grid = np.full((len(yvalues), len(xvalues)), np.nan)
    counts = np.zeros_like(grid)

    for index, params in enumerate(results.param_list):
        x_index = xvalues.index(params[param_x])
        y_index = yvalues.index(params[param_y])
        if np.isnan(grid[y_index, x_index]):
            grid[y_index, x_index] = 0.0
        grid[y_index, x_index] += results.original_sharpes[index]
        counts[y_index, x_index] += 1

    mask = counts > 0
    grid[mask] /= counts[mask]
    return grid, counts


def _render_matplotlib(draw: Callable[[object], object], save_path: object | None):
    import matplotlib

    original_backend = matplotlib.get_backend()
    fig = None
    try:
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt

        fig = draw(plt)
        if save_path is not None:
            fig.savefig(Path(save_path), dpi=150, bbox_inches="tight")
        return fig
    finally:
        if fig is not None:
            import matplotlib.pyplot as plt

            plt.close(fig)
        try:
            matplotlib.use(original_backend, force=True)
        except (ImportError, ValueError):
            pass


__all__ = [
    "MatplotlibChartRenderer",
    "plot_autocorrelation",
    "plot_null_distribution",
    "plot_overfit_dashboard",
    "plot_parameter_sensitivity",
    "plot_pbo_distribution",
    "plot_pvalue_comparison",
    "plot_surface_2d",
    "plot_walkforward_degradation",
]

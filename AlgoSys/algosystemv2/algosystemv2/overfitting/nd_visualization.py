"""
N-dimensional parameter surface visualization for overfitting detection.

Handles the "X signals → X-dimensional graph" requirement:

    1 signal  → 1D line plot (existing plot_parameter_sensitivity)
    2 signals → 2D heatmap (existing plot_surface_2d)
    3 signals → 3D surface plot (Plotly interactive + matplotlib static)
    N signals → Parallel coordinates + pairwise 3D slices

The core insight: overfitting shows up as a NEEDLE (isolated peak) while
a robust strategy shows a BROAD PLATEAU. In 3D this is a mountain vs a
spike; in N-D you see it via parallel coordinates bunching or spreading.

Requires: plotly (for interactive 3D), matplotlib (for static fallback).
"""

from __future__ import annotations

import itertools
import math
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    from .results import OverfitResults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_param_grid(results: OverfitResults) -> Tuple[list, dict, dict]:
    """Extract sorted param keys, unique values, and value-to-index maps."""
    param_keys = sorted({k for p in results.param_list for k in p})
    param_values = {
        k: sorted(set(p[k] for p in results.param_list))
        for k in param_keys
    }
    param_idx = {
        k: {v: i for i, v in enumerate(vals)}
        for k, vals in param_values.items()
    }
    return param_keys, param_values, param_idx


def _build_sharpe_grid(
    results: OverfitResults,
    dim_keys: list[str],
    param_values: dict,
    marginalize: bool = True,
) -> Tuple[np.ndarray, list[list]]:
    """
    Build an N-D grid of Sharpe values for the given dimension keys.

    If there are other parameters not in dim_keys, they are marginalized
    (averaged) over. Returns (grid, axis_values) where grid.shape matches
    [len(param_values[k]) for k in dim_keys].
    """
    shape = tuple(len(param_values[k]) for k in dim_keys)
    grid = np.zeros(shape, dtype=np.float64)
    counts = np.zeros(shape, dtype=np.float64)

    idx_maps = {k: {v: i for i, v in enumerate(param_values[k])} for k in dim_keys}

    for i, p in enumerate(results.param_list):
        coords = tuple(idx_maps[k][p[k]] for k in dim_keys)
        grid[coords] += results.original_sharpes[i]
        counts[coords] += 1

    mask = counts > 0
    grid[mask] /= counts[mask]

    axis_values = [param_values[k] for k in dim_keys]
    return grid, axis_values


# ---------------------------------------------------------------------------
# 3D Surface Plot (Plotly interactive)
# ---------------------------------------------------------------------------

def plot_surface_3d_interactive(
    results: OverfitResults,
    param_x: str,
    param_y: str,
    param_z: str,
    fixed_params: dict | None = None,
    save_path: str | None = None,
    colorscale: str = 'RdYlGn',
) -> object:
    """
    Interactive 3D surface plot for a strategy with 3 signal parameters.

    Each axis is one signal parameter; the color/height represents Sharpe.
    For 3 params (x, y, z) this creates a volumetric scatter where each
    point is a parameter combination, colored by Sharpe ratio.

    For true surface rendering, one param is fixed and the other two form
    the surface grid — use the slider to sweep through the third param.

    Parameters
    ----------
    results : OverfitResults
        Output from OverfitDetector.run().
    param_x, param_y, param_z : str
        The three parameter names to visualize.
    fixed_params : dict, optional
        Fix other parameters (beyond x, y, z) to specific values.
        If None, marginalizes (averages) over extra params.
    save_path : str, optional
        If set, saves to HTML file.
    colorscale : str
        Plotly colorscale name.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("plotly is required for 3D interactive plots. pip install plotly")
        return None

    param_keys, param_values, _ = _extract_param_grid(results)
    for p in [param_x, param_y, param_z]:
        if p not in param_keys:
            print(f"Parameter '{p}' not found. Available: {param_keys}")
            return None

    # Filter to fixed params if specified
    if fixed_params:
        mask = np.ones(len(results.param_list), dtype=bool)
        for k, v in fixed_params.items():
            if k not in [param_x, param_y, param_z]:
                mask &= np.array([p[k] == v for p in results.param_list])
        filtered_indices = np.where(mask)[0]
    else:
        filtered_indices = np.arange(len(results.param_list))

    # Create frames: one surface per z-value
    z_values = param_values[param_z]
    x_values = param_values[param_x]
    y_values = param_values[param_y]

    frames = []
    surfaces = []

    for zi, zv in enumerate(z_values):
        # Build 2D grid for this z-slice
        grid = np.full((len(y_values), len(x_values)), np.nan)
        counts = np.zeros_like(grid)

        for idx in filtered_indices:
            p = results.param_list[idx]
            if p[param_z] != zv:
                continue
            xi = x_values.index(p[param_x])
            yi = y_values.index(p[param_y])
            if np.isnan(grid[yi, xi]):
                grid[yi, xi] = 0.0
            grid[yi, xi] += results.original_sharpes[idx]
            counts[yi, xi] += 1

        valid = counts > 0
        grid[valid] /= counts[valid]

        x_mesh, y_mesh = np.meshgrid(
            [float(v) for v in x_values],
            [float(v) for v in y_values],
        )

        surface = go.Surface(
            x=x_mesh, y=y_mesh, z=grid,
            colorscale=colorscale,
            colorbar=dict(title='Sharpe'),
            showscale=(zi == 0),
            name=f'{param_z}={zv}',
        )

        if zi == 0:
            surfaces.append(surface)

        frames.append(go.Frame(
            data=[go.Surface(
                x=x_mesh, y=y_mesh, z=grid,
                colorscale=colorscale,
                colorbar=dict(title='Sharpe'),
            )],
            name=str(zv),
        ))

    # Build figure with slider
    fig = go.Figure(data=surfaces, frames=frames)

    steps = []
    for zv in z_values:
        step = dict(
            method='animate',
            args=[[str(zv)], dict(mode='immediate',
                                  frame=dict(duration=300, redraw=True))],
            label=str(zv),
        )
        steps.append(step)

    sliders = [dict(
        active=0,
        currentvalue=dict(prefix=f'{param_z} = '),
        steps=steps,
        pad=dict(t=50),
    )]

    # Mark the best parameter set
    best_p = results.param_list[results.best_param_index]
    fig.add_trace(go.Scatter3d(
        x=[float(best_p[param_x])],
        y=[float(best_p[param_y])],
        z=[results.best_sharpe],
        mode='markers',
        marker=dict(size=8, color='red', symbol='diamond'),
        name=f'Best (SR={results.best_sharpe:.3f})',
    ))

    fig.update_layout(
        title=f'3D Parameter Surface: {param_x} x {param_y} x {param_z}<br>'
              f'<sub>Slide {param_z} to see surface evolution | '
              f'Plateau = robust, Spike = overfit</sub>',
        scene=dict(
            xaxis_title=param_x,
            yaxis_title=param_y,
            zaxis_title='Sharpe',
        ),
        sliders=sliders,
        width=900,
        height=700,
    )

    if save_path:
        fig.write_html(save_path)
        print(f"Interactive 3D plot saved to {save_path}")
    else:
        fig.show()

    return fig


# ---------------------------------------------------------------------------
# 3D Scatter Volume (all 3 params as axes, color = Sharpe)
# ---------------------------------------------------------------------------

def plot_volume_3d(
    results: OverfitResults,
    param_x: str,
    param_y: str,
    param_z: str,
    fixed_params: dict | None = None,
    save_path: str | None = None,
    colorscale: str = 'RdYlGn',
) -> object:
    """
    3D scatter volume: each point is a parameter combination.
    Position = (param_x, param_y, param_z), color = Sharpe, size = |Sharpe|.

    This is the vectorbt-style "volume cube" visualization.
    Overfitting shows as an isolated bright point; robust strategies
    show as a glowing cloud.

    Parameters
    ----------
    results : OverfitResults
    param_x, param_y, param_z : str
        The three parameter names.
    fixed_params : dict, optional
        Fix extra parameters to specific values.
    save_path : str, optional
        Save as HTML.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("plotly required. pip install plotly")
        return None

    param_keys, _, _ = _extract_param_grid(results)
    for p in [param_x, param_y, param_z]:
        if p not in param_keys:
            print(f"Parameter '{p}' not found. Available: {param_keys}")
            return None

    # Collect data points
    xs, ys, zs, sharpes, texts = [], [], [], [], []
    for i, p in enumerate(results.param_list):
        if fixed_params:
            skip = False
            for k, v in fixed_params.items():
                if k not in [param_x, param_y, param_z] and p[k] != v:
                    skip = True
                    break
            if skip:
                continue

        xs.append(float(p[param_x]))
        ys.append(float(p[param_y]))
        zs.append(float(p[param_z]))
        sharpes.append(results.original_sharpes[i])
        texts.append(
            f"{param_x}={p[param_x]}<br>"
            f"{param_y}={p[param_y]}<br>"
            f"{param_z}={p[param_z]}<br>"
            f"Sharpe={results.original_sharpes[i]:.4f}"
        )

    sharpes_arr = np.array(sharpes)
    sizes = np.clip(np.abs(sharpes_arr) * 8, 3, 20)

    fig = go.Figure(data=[go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode='markers',
        marker=dict(
            size=sizes,
            color=sharpes,
            colorscale=colorscale,
            colorbar=dict(title='Sharpe'),
            opacity=0.7,
            line=dict(width=0.5, color='black'),
        ),
        text=texts,
        hoverinfo='text',
        name='Parameter space',
    )])

    # Mark best
    best_p = results.param_list[results.best_param_index]
    fig.add_trace(go.Scatter3d(
        x=[float(best_p[param_x])],
        y=[float(best_p[param_y])],
        z=[float(best_p[param_z])],
        mode='markers',
        marker=dict(size=12, color='red', symbol='diamond',
                    line=dict(width=2, color='black')),
        name=f'Best (SR={results.best_sharpe:.3f})',
    ))

    fig.update_layout(
        title=f'3D Parameter Volume: {param_x} x {param_y} x {param_z}<br>'
              f'<sub>Size & color = Sharpe | Cluster = robust, Outlier = overfit</sub>',
        scene=dict(
            xaxis_title=param_x,
            yaxis_title=param_y,
            zaxis_title=param_z,
        ),
        width=900,
        height=700,
    )

    if save_path:
        fig.write_html(save_path)
        print(f"3D volume plot saved to {save_path}")
    else:
        fig.show()

    return fig


# ---------------------------------------------------------------------------
# 3D Surface (matplotlib static fallback)
# ---------------------------------------------------------------------------

def plot_surface_3d_static(
    results: OverfitResults,
    param_x: str,
    param_y: str,
    z_param_value: dict | None = None,
    save_path: str | None = None,
) -> object:
    """
    Static 3D surface plot using matplotlib (no plotly needed).

    The z-axis is Sharpe ratio; x and y are two parameters.
    Other parameters are marginalized (averaged).

    Parameters
    ----------
    results : OverfitResults
    param_x, param_y : str
        Two parameter names for the surface axes.
    z_param_value : dict, optional
        Fix other parameters. If None, averages over them.
    save_path : str, optional
        Save as PNG.
    """
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
    except ImportError:
        print("matplotlib required")
        return None

    param_keys, param_values, _ = _extract_param_grid(results)

    x_vals = param_values[param_x]
    y_vals = param_values[param_y]

    grid = np.full((len(y_vals), len(x_vals)), np.nan)
    counts = np.zeros_like(grid)

    for i, p in enumerate(results.param_list):
        if z_param_value:
            skip = False
            for k, v in z_param_value.items():
                if k not in [param_x, param_y] and p[k] != v:
                    skip = True
                    break
            if skip:
                continue

        xi = x_vals.index(p[param_x])
        yi = y_vals.index(p[param_y])
        if np.isnan(grid[yi, xi]):
            grid[yi, xi] = 0.0
        grid[yi, xi] += results.original_sharpes[i]
        counts[yi, xi] += 1

    valid = counts > 0
    grid[valid] /= counts[valid]
    grid[~valid] = 0.0

    x_mesh, y_mesh = np.meshgrid(
        [float(v) for v in x_vals],
        [float(v) for v in y_vals],
    )

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    surf = ax.plot_surface(
        x_mesh, y_mesh, grid,
        cmap='RdYlGn', edgecolor='none', alpha=0.85,
    )

    # Mark best
    best_p = results.param_list[results.best_param_index]
    ax.scatter(
        [float(best_p[param_x])],
        [float(best_p[param_y])],
        [results.best_sharpe],
        color='red', s=100, marker='*', zorder=5,
        label=f'Best (SR={results.best_sharpe:.3f})',
    )

    ax.set_xlabel(param_x)
    ax.set_ylabel(param_y)
    ax.set_zlabel('Sharpe')
    ax.set_title(
        f'3D Parameter Surface\n'
        f'Plateau = robust | Spike = overfit'
    )
    fig.colorbar(surf, ax=ax, shrink=0.5, label='Sharpe')
    ax.legend()

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Static 3D plot saved to {save_path}")
    else:
        plt.show()

    return fig


# ---------------------------------------------------------------------------
# N-D Parallel Coordinates (for N > 3 signals)
# ---------------------------------------------------------------------------

def plot_parallel_coordinates(
    results: OverfitResults,
    params_to_show: list[str] | None = None,
    top_n: int | None = None,
    save_path: str | None = None,
    colorscale: str = 'RdYlGn',
) -> object:
    """
    Parallel coordinates plot for N-dimensional parameter space.

    Each vertical axis is one parameter; each line is one parameter
    combination, colored by Sharpe ratio. The rightmost axis is Sharpe.

    Robust strategies: lines fan out broadly across all axes (many combos
    have similar, positive Sharpe).
    Overfit strategies: a single bright line stands alone; others are grey/red.

    Parameters
    ----------
    results : OverfitResults
    params_to_show : list of str, optional
        Which parameters to include. Default: all.
    top_n : int, optional
        Only show the top N parameter combos (by Sharpe). Useful when
        the grid is huge.
    save_path : str, optional
        Save as HTML.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("plotly required. pip install plotly")
        return None

    param_keys, param_values, param_idx = _extract_param_grid(results)
    if params_to_show is None:
        params_to_show = param_keys
    else:
        params_to_show = [p for p in params_to_show if p in param_keys]

    # Build data arrays
    if top_n is not None:
        indices = results.sort_indices[:top_n]
    else:
        indices = np.arange(len(results.param_list))

    dimensions = []
    for key in params_to_show:
        vals = [results.param_list[i][key] for i in indices]
        unique_vals = param_values[key]

        if all(isinstance(v, (int, float)) for v in unique_vals):
            dimensions.append(dict(
                range=[min(unique_vals), max(unique_vals)],
                label=key,
                values=[float(v) for v in vals],
            ))
        else:
            # Categorical — map to integers
            val_map = {v: i for i, v in enumerate(unique_vals)}
            dimensions.append(dict(
                range=[0, len(unique_vals) - 1],
                label=key,
                values=[val_map[v] for v in vals],
                tickvals=list(range(len(unique_vals))),
                ticktext=[str(v) for v in unique_vals],
            ))

    # Add Sharpe as the final dimension
    sharpe_vals = [results.original_sharpes[i] for i in indices]
    dimensions.append(dict(
        range=[min(sharpe_vals), max(sharpe_vals)],
        label='Sharpe',
        values=sharpe_vals,
    ))

    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=sharpe_vals,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(title='Sharpe'),
        ),
        dimensions=dimensions,
    ))

    n_dims = len(params_to_show)
    fig.update_layout(
        title=f'{n_dims}D Parameter Space (Parallel Coordinates)<br>'
              f'<sub>Bright lines = high Sharpe | Dense band = robust plateau</sub>',
        width=max(800, 200 * n_dims),
        height=500,
    )

    if save_path:
        fig.write_html(save_path)
        print(f"Parallel coordinates plot saved to {save_path}")
    else:
        fig.show()

    return fig


# ---------------------------------------------------------------------------
# Pairwise 3D Slice Grid (for N > 3)
# ---------------------------------------------------------------------------

def plot_pairwise_3d_grid(
    results: OverfitResults,
    params_to_show: list[str] | None = None,
    save_path: str | None = None,
) -> object:
    """
    For N parameters, generate a grid of 3D surface plots for every
    pair of parameters (z-axis = Sharpe, marginalized over the rest).

    This is the "comprehensive view" — C(N, 2) subplots, each showing
    how Sharpe varies across two dimensions.

    Parameters
    ----------
    results : OverfitResults
    params_to_show : list of str, optional
        Which parameters to include. Default: all.
    save_path : str, optional
        Save as HTML.

    Returns
    -------
    plotly.graph_objects.Figure (subplots)
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        print("plotly required")
        return None

    param_keys, param_values, _ = _extract_param_grid(results)
    if params_to_show is None:
        params_to_show = param_keys
    else:
        params_to_show = [p for p in params_to_show if p in param_keys]

    pairs = list(itertools.combinations(params_to_show, 2))
    n_pairs = len(pairs)
    if n_pairs == 0:
        print("Need at least 2 parameters for pairwise plots.")
        return None

    ncols = min(3, n_pairs)
    nrows = math.ceil(n_pairs / ncols)

    specs = [[{'type': 'surface'} for _ in range(ncols)] for _ in range(nrows)]
    titles = [f'{px} x {py}' for px, py in pairs]
    # Pad titles for empty cells
    while len(titles) < nrows * ncols:
        titles.append('')

    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=titles,
        specs=specs,
    )

    for idx, (px, py) in enumerate(pairs):
        row = idx // ncols + 1
        col = idx % ncols + 1

        grid, axis_vals = _build_sharpe_grid(results, [px, py], param_values)
        x_vals = [float(v) for v in axis_vals[0]]
        y_vals = [float(v) for v in axis_vals[1]]
        x_mesh, y_mesh = np.meshgrid(x_vals, y_vals)

        # grid shape is (len(px_values), len(py_values)) but meshgrid
        # produces (len(y_vals), len(x_vals)), so transpose
        fig.add_trace(
            go.Surface(
                x=x_mesh, y=y_mesh, z=grid.T,
                colorscale='RdYlGn',
                showscale=(idx == 0),
                name=f'{px} x {py}',
            ),
            row=row, col=col,
        )

        fig.update_scenes(
            dict(
                xaxis_title=px,
                yaxis_title=py,
                zaxis_title='SR',
            ),
            row=row, col=col,
        )

    fig.update_layout(
        title=f'Pairwise 3D Parameter Surfaces ({len(params_to_show)} dimensions)<br>'
              f'<sub>Each surface shows Sharpe across two params, averaged over the rest</sub>',
        width=400 * ncols,
        height=400 * nrows,
    )

    if save_path:
        fig.write_html(save_path)
        print(f"Pairwise 3D grid saved to {save_path}")
    else:
        fig.show()

    return fig


# ---------------------------------------------------------------------------
# Auto-router: picks the best visualization for N dimensions
# ---------------------------------------------------------------------------

def plot_parameter_space(
    results: OverfitResults,
    params: list[str] | None = None,
    save_path: str | None = None,
    interactive: bool = True,
) -> object:
    """
    Automatically choose the best visualization based on dimension count.

    This is the main entry point. Give it your results and it picks:
        1 param  → 1D sensitivity line (falls back to existing)
        2 params → 2D heatmap or 3D surface (z = Sharpe)
        3 params → 3D volume scatter + slider surface
        4+ params → Parallel coordinates + pairwise 3D grid

    Parameters
    ----------
    results : OverfitResults
        Output from OverfitDetector.run().
    params : list of str, optional
        Which parameters to visualize. Default: all.
    save_path : str, optional
        Base path for saved files (extension added automatically).
    interactive : bool
        If True, use Plotly. If False, use matplotlib.

    Returns
    -------
    Figure or list of Figures
    """
    param_keys, _, _ = _extract_param_grid(results)
    if params is None:
        params = param_keys
    else:
        params = [p for p in params if p in param_keys]

    n_dims = len(params)

    if n_dims == 0:
        print("No parameters to visualize.")
        return None

    if n_dims == 1:
        # 1D: sensitivity line
        from .visualization import plot_parameter_sensitivity
        path = f"{save_path}_1d.png" if save_path else None
        return plot_parameter_sensitivity(results, save_path=path)

    if n_dims == 2:
        # 2D: 3D surface (z = Sharpe) if interactive, 2D heatmap otherwise
        if interactive:
            # Use Plotly volume scatter as an interactive 2D+Sharpe view
            from .visualization import plot_surface_2d
            path = f"{save_path}_2d.html" if save_path else None
            # Return both a heatmap and a static 3D surface
            figs = []
            figs.append(plot_surface_2d(results, params[0], params[1],
                                        save_path=f"{save_path}_heatmap.png" if save_path else None))
            figs.append(plot_surface_3d_static(
                results, params[0], params[1],
                save_path=f"{save_path}_3d.png" if save_path else None,
            ))
            return figs
        else:
            from .visualization import plot_surface_2d
            path = f"{save_path}_2d.png" if save_path else None
            return plot_surface_2d(results, params[0], params[1], save_path=path)

    if n_dims == 3:
        # 3D: interactive volume + slider surface
        figs = []
        path1 = f"{save_path}_volume.html" if save_path else None
        figs.append(plot_volume_3d(
            results, params[0], params[1], params[2], save_path=path1,
        ))
        path2 = f"{save_path}_surface.html" if save_path else None
        figs.append(plot_surface_3d_interactive(
            results, params[0], params[1], params[2], save_path=path2,
        ))
        return figs

    # N > 3: parallel coordinates + pairwise surfaces
    figs = []
    path1 = f"{save_path}_parallel.html" if save_path else None
    figs.append(plot_parallel_coordinates(
        results, params_to_show=params, save_path=path1,
    ))
    path2 = f"{save_path}_pairwise.html" if save_path else None
    figs.append(plot_pairwise_3d_grid(
        results, params_to_show=params, save_path=path2,
    ))
    return figs

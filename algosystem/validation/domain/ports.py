"""Validation domain ports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
import numpy.typing as npt

from .strategy import ParameterSet, StrategySpec


class StrategyEvaluator(Protocol):
    """Port satisfied by a strategy backtest function."""

    def __call__(
        self,
        params: Mapping[str, object],
        returns: npt.NDArray[np.float64],
    ) -> float:
        """Evaluate one parameter set against one return series."""
        ...


class PassRunner(Protocol):
    """Port for running permutation passes over a parameter grid."""

    def run_passes(
        self,
        strategy: StrategySpec,
        returns: npt.NDArray[np.float64],
        parameter_sets: Sequence[ParameterSet],
        pass_seeds: Sequence[int],
        shuffle_method: str,
        block_size: int | None = None,
    ) -> npt.NDArray[np.float64]:
        """Run all passes and return a matrix shaped passes x parameter sets."""
        ...


class ChartRenderer(Protocol):
    """Port for validation chart renderers."""

    def plot_null_distribution(self, results: object, save_path: object | None = None) -> object:
        """Render the permutation null distribution."""
        ...

    def plot_parameter_sensitivity(
        self,
        results: object,
        save_path: object | None = None,
        show_individual: bool = True,
    ) -> object:
        """Render per-parameter sensitivity."""
        ...

    def plot_surface_2d(
        self,
        results: object,
        param_x: str,
        param_y: str,
        save_path: object | None = None,
    ) -> object:
        """Render a two-dimensional parameter surface."""
        ...

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
        ...


class ReportRenderer(Protocol):
    """Port for validation report renderers."""

    def render(
        self,
        results: object,
        output_path: Path,
        *,
        pbo_results: object | None = None,
        wf_results: object | None = None,
        ac_diagnostic: object | None = None,
        robustness: Mapping[str, object] | None = None,
        title: str = "Overfitting Detection Report",
        open_browser: bool = False,
    ) -> Path:
        """Render a validation report and return the written path."""
        ...

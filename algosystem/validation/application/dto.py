"""Validation application DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import numpy.typing as npt

from algosystem.validation.domain.results import OverfitResults
from algosystem.validation.domain.statistics.signal_analyzer import SignalAnalysisReport
from algosystem.validation.domain.statistics.walkforward import WalkForwardResults
from algosystem.validation.domain.strategy import StrategySpec


@dataclass(frozen=True)
class DetectOverfittingRequest:
    """Request to run permutation-based overfitting detection."""

    strategy: StrategySpec
    returns: npt.NDArray[np.float64] | Sequence[float]
    n_reps: int = 1000
    shuffle_method: str = "complete"
    block_size: Optional[int] = None
    max_param_trials: Optional[int] = None
    seed: Optional[int] = None


@dataclass(frozen=True)
class DetectOverfittingResponse:
    """Response containing overfitting detection results."""

    results: OverfitResults


@dataclass(frozen=True)
class RunWalkForwardRequest:
    """Request to run walk-forward validation."""

    strategy: StrategySpec
    returns: npt.NDArray[np.float64] | Sequence[float]
    n_folds: int = 5
    is_ratio: float = 0.8
    purge_gap: int = 0


@dataclass(frozen=True)
class RunWalkForwardResponse:
    """Response containing walk-forward validation results."""

    results: WalkForwardResults


@dataclass(frozen=True)
class ScreenSignalsRequest:
    """Request to screen a signal parameter space."""

    strategy: StrategySpec
    returns: npt.NDArray[np.float64] | Sequence[float]
    n_reps: int = 500
    shuffle_method: str = "complete"
    seed: Optional[int] = None
    run_pbo: bool = True
    run_walkforward: bool = True
    run_tracker: bool = True


@dataclass(frozen=True)
class ScreenSignalsResponse:
    """Response containing a signal-analysis report."""

    report: SignalAnalysisReport

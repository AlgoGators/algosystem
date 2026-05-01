"""
Permutation-based overfitting detection for trading strategy backtests.

Core API:
    OverfitDetector  — runs the permutation test
    OverfitResults   — holds results, reports, surface analysis

New features:
    diagnostics      — autocorrelation detection + shuffle recommendation
    cscv             — CSCV / Probability of Backtest Overfitting (PBO)
    stepwise         — stepwise permutation test (Romano-Wolf / Masters)
    walkforward      — walk-forward analysis with purging + WFE

Visualization:
    plot_null_distribution       — null distribution histogram
    plot_parameter_sensitivity   — per-parameter sensitivity grid
    plot_surface_2d              — 2D heatmap across two parameters
    plot_overfit_dashboard       — 6-panel diagnostic dashboard
    plot_pbo_distribution        — PBO logit histogram
    plot_walkforward_degradation — IS vs OOS scatter
    plot_autocorrelation         — ACF bar chart
    plot_pvalue_comparison       — solo vs unbiased p-values

Shufflers:
    complete_shuffle, cyclic_shuffle, block_shuffle

Strategies:
    strategies subpackage with 6 archetypes + param grids

Data generators:
    generate_noise, generate_trending, generate_mean_reverting, generate_volatile_regimes
"""

from .detector import OverfitDetector
from .results import OverfitResults
from .shufflers import block_shuffle, complete_shuffle, cyclic_shuffle
from .diagnostics import check_autocorrelation, AutocorrelationDiagnostic
from .cscv import compute_pbo, PBOResults, cost_sensitivity_pbo
from .stepwise import stepwise_permutation_test, StepwiseResults
from .walkforward import walk_forward_analysis, WalkForwardResults
from .costs import CostModel, apply_transaction_costs, compute_trade_log, trade_log_summary
from .costs import ZERO_COST, RETAIL_EQUITY, INSTITUTIONAL_EQUITY, CRYPTO_SPOT, FUTURES
from .data_validation import validate_returns, ValidationResult
from .dashboard import generate_overfit_dashboard
from .robustness import (
    bootstrap_sharpe_ci, SharpeCI,
    monte_carlo_trades, MonteCarloResults,
    alpha_beta_decomposition, AlphaBetaResult,
    kelly_criterion, KellyResult,
    regime_conditional_performance, RegimeResult,
)
from .visualization import (
    plot_null_distribution,
    plot_parameter_sensitivity,
    plot_surface_2d,
    plot_overfit_dashboard,
    plot_pbo_distribution,
    plot_walkforward_degradation,
    plot_autocorrelation,
    plot_pvalue_comparison,
)
from .psr_dsr import (
    probabilistic_sharpe_ratio,
    PSRResult,
    deflated_sharpe_ratio,
    DSRResult,
    batch_deflated_sharpe,
    BatchDSRResult,
    compute_return_stats,
    ReturnStats,
    TrialTracker,
    TrialRecord,
)
from .nd_visualization import (
    plot_surface_3d_interactive,
    plot_volume_3d,
    plot_surface_3d_static,
    plot_parallel_coordinates,
    plot_pairwise_3d_grid,
    plot_parameter_space,
)
from .signal_analyzer import SignalAnalyzer, SignalAnalysisReport

__all__ = [
    # Core detector
    'OverfitDetector',
    'OverfitResults',
    # Shufflers
    'complete_shuffle',
    'cyclic_shuffle',
    'block_shuffle',
    # Diagnostics
    'check_autocorrelation',
    'AutocorrelationDiagnostic',
    # CSCV / PBO
    'compute_pbo',
    'PBOResults',
    'cost_sensitivity_pbo',
    # Stepwise
    'stepwise_permutation_test',
    'StepwiseResults',
    # Walk-forward
    'walk_forward_analysis',
    'WalkForwardResults',
    # Costs
    'CostModel',
    'apply_transaction_costs',
    'compute_trade_log',
    'trade_log_summary',
    'ZERO_COST',
    'RETAIL_EQUITY',
    'INSTITUTIONAL_EQUITY',
    'CRYPTO_SPOT',
    'FUTURES',
    # Data validation
    'validate_returns',
    'ValidationResult',
    # Dashboard
    'generate_overfit_dashboard',
    # Robustness
    'bootstrap_sharpe_ci',
    'SharpeCI',
    'monte_carlo_trades',
    'MonteCarloResults',
    'alpha_beta_decomposition',
    'AlphaBetaResult',
    'kelly_criterion',
    'KellyResult',
    'regime_conditional_performance',
    'RegimeResult',
    # 2D Visualization
    'plot_null_distribution',
    'plot_parameter_sensitivity',
    'plot_surface_2d',
    'plot_overfit_dashboard',
    'plot_pbo_distribution',
    'plot_walkforward_degradation',
    'plot_autocorrelation',
    'plot_pvalue_comparison',
    # PSR / DSR (jsharpe-style)
    'probabilistic_sharpe_ratio',
    'PSRResult',
    'deflated_sharpe_ratio',
    'DSRResult',
    'batch_deflated_sharpe',
    'BatchDSRResult',
    'compute_return_stats',
    'ReturnStats',
    'TrialTracker',
    'TrialRecord',
    # N-D Visualization
    'plot_surface_3d_interactive',
    'plot_volume_3d',
    'plot_surface_3d_static',
    'plot_parallel_coordinates',
    'plot_pairwise_3d_grid',
    'plot_parameter_space',
    # Signal Analyzer
    'SignalAnalyzer',
    'SignalAnalysisReport',
]

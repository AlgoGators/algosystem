"""Validation domain model."""

from .costs import (
    CRYPTO_SPOT,
    FUTURES,
    INSTITUTIONAL_EQUITY,
    RETAIL_EQUITY,
    ZERO_COST,
    CostModel,
    TransactionCostBacktest,
    apply_transaction_costs,
    compute_trade_log,
    compute_turnover,
    trade_log_summary,
)
from .ports import ChartRenderer, PassRunner, ReportRenderer, StrategyEvaluator
from .results import OverfitResults
from .shufflers import SHUFFLE_METHODS, block_shuffle, complete_shuffle, cyclic_shuffle
from .statistics.cscv import PBOResults, compute_pbo, cost_sensitivity_pbo
from .statistics.diagnostics import AutocorrelationDiagnostic, check_autocorrelation
from .statistics.psr_dsr import (
    BatchDSRResult,
    DSRResult,
    PSRResult,
    ReturnStats,
    TrialRecord,
    TrialTracker,
    batch_deflated_sharpe,
    compute_return_stats,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)
from .statistics.robustness import (
    AlphaBetaResult,
    KellyResult,
    MonteCarloResults,
    RegimeResult,
    SharpeCI,
    alpha_beta_decomposition,
    bootstrap_sharpe_ci,
    kelly_criterion,
    monte_carlo_trades,
    regime_conditional_performance,
)
from .statistics.signal_analyzer import SignalAnalysisReport
from .statistics.stepwise import StepwiseResults, stepwise_permutation_test
from .statistics.validity import ValidationResult, validate_returns
from .statistics.walkforward import WalkForwardResults, walk_forward_analysis
from .strategy import ParameterGrid, ParameterSet, StrategySpec
from .validation_metric import LEGACY_ALIASES, ValidationMetricKey

__all__ = [
    "AlphaBetaResult",
    "AutocorrelationDiagnostic",
    "BatchDSRResult",
    "CRYPTO_SPOT",
    "ChartRenderer",
    "CostModel",
    "DSRResult",
    "FUTURES",
    "INSTITUTIONAL_EQUITY",
    "KellyResult",
    "LEGACY_ALIASES",
    "MonteCarloResults",
    "OverfitResults",
    "PBOResults",
    "ParameterGrid",
    "ParameterSet",
    "PassRunner",
    "PSRResult",
    "RETAIL_EQUITY",
    "RegimeResult",
    "ReturnStats",
    "SHUFFLE_METHODS",
    "SharpeCI",
    "SignalAnalysisReport",
    "StepwiseResults",
    "ReportRenderer",
    "StrategySpec",
    "StrategyEvaluator",
    "TrialRecord",
    "TrialTracker",
    "TransactionCostBacktest",
    "ValidationMetricKey",
    "ValidationResult",
    "WalkForwardResults",
    "ZERO_COST",
    "alpha_beta_decomposition",
    "apply_transaction_costs",
    "batch_deflated_sharpe",
    "block_shuffle",
    "bootstrap_sharpe_ci",
    "check_autocorrelation",
    "complete_shuffle",
    "compute_pbo",
    "compute_return_stats",
    "compute_trade_log",
    "compute_turnover",
    "cost_sensitivity_pbo",
    "cyclic_shuffle",
    "deflated_sharpe_ratio",
    "kelly_criterion",
    "monte_carlo_trades",
    "probabilistic_sharpe_ratio",
    "regime_conditional_performance",
    "stepwise_permutation_test",
    "trade_log_summary",
    "validate_returns",
    "walk_forward_analysis",
]

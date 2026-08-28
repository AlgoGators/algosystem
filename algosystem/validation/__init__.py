"""Validation public surface."""

from __future__ import annotations

from importlib import import_module

_LAZY_EXPORTS = {
    "DetectOverfitting": (
        "algosystem.validation.application.detect_overfitting",
        "DetectOverfitting",
    ),
    "OverfitDetector": ("algosystem.validation.facade", "OverfitDetector"),
    "OverfitResults": ("algosystem.validation.domain.results", "OverfitResults"),
    "ParameterGrid": ("algosystem.validation.domain.strategy", "ParameterGrid"),
    "ParameterSet": ("algosystem.validation.domain.strategy", "ParameterSet"),
    "SignalAnalysisReport": (
        "algosystem.validation.domain.statistics.signal_analyzer",
        "SignalAnalysisReport",
    ),
    "SignalAnalyzer": ("algosystem.validation.application.signal_analyzer", "SignalAnalyzer"),
    "StrategySpec": ("algosystem.validation.domain.strategy", "StrategySpec"),
    "ValidationMetricKey": (
        "algosystem.validation.domain.validation_metric",
        "ValidationMetricKey",
    ),
    "detect_overfitting": ("algosystem.validation.facade", "detect_overfitting"),
}


def __getattr__(name: str) -> object:
    if name in _LAZY_EXPORTS:
        module_name, attribute = _LAZY_EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attribute)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DetectOverfitting",
    "OverfitDetector",
    "OverfitResults",
    "ParameterGrid",
    "ParameterSet",
    "SignalAnalysisReport",
    "SignalAnalyzer",
    "StrategySpec",
    "ValidationMetricKey",
    "detect_overfitting",
]

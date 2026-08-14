"""Validation infrastructure adapters."""

from __future__ import annotations

from importlib import import_module

_LAZY_EXPORTS = {
    "MultiprocessingPassRunner": (
        "algosystem.validation.infrastructure.multiprocessing_runner",
        "MultiprocessingPassRunner",
    ),
    "SequentialPassRunner": (
        "algosystem.validation.infrastructure.sequential_runner",
        "SequentialPassRunner",
    ),
    "MatplotlibChartRenderer": (
        "algosystem.validation.infrastructure.matplotlib_charts",
        "MatplotlibChartRenderer",
    ),
    "HtmlReportRenderer": (
        "algosystem.validation.infrastructure.html_report",
        "HtmlReportRenderer",
    ),
    "default_pass_runner": (
        "algosystem.validation.infrastructure.default_runner",
        "default_pass_runner",
    ),
    "worker_run_pass": (
        "algosystem.validation.infrastructure.multiprocessing_runner",
        "worker_run_pass",
    ),
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
    "MultiprocessingPassRunner",
    "SequentialPassRunner",
    "MatplotlibChartRenderer",
    "HtmlReportRenderer",
    "default_pass_runner",
    "worker_run_pass",
]

"""Default validation runner composition."""

from __future__ import annotations

from algosystem.validation.domain.ports import PassRunner, StrategyEvaluator
from algosystem.validation.infrastructure.multiprocessing_runner import MultiprocessingPassRunner
from algosystem.validation.infrastructure.sequential_runner import SequentialPassRunner


def default_pass_runner(
    evaluator: StrategyEvaluator,
    n_workers: int | None,
) -> PassRunner:
    """Return the default pass runner for a worker-count request."""
    if n_workers == 1:
        return SequentialPassRunner(evaluator=evaluator)
    return MultiprocessingPassRunner(evaluator=evaluator, worker_count=n_workers)

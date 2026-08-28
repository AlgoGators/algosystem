"""Tests for validation strategy value objects."""

import pytest

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.strategy import ParameterGrid, ParameterSet, StrategySpec


def test_parameter_grid_combinations_are_stable_and_hashable():
    grid = ParameterGrid({"threshold": [0.0, 0.1], "lookback": [5, 10]})

    combinations = list(grid.combinations())

    assert grid.size == 4
    assert combinations == [
        ParameterSet({"lookback": 5, "threshold": 0.0}),
        ParameterSet({"lookback": 5, "threshold": 0.1}),
        ParameterSet({"lookback": 10, "threshold": 0.0}),
        ParameterSet({"lookback": 10, "threshold": 0.1}),
    ]
    assert len(set(combinations)) == 4


@pytest.mark.parametrize(
    "grid",
    [
        {},
        {"lookback": []},
        {"lookback": [5, 5]},
        {"lookback": [[5]]},
    ],
)
def test_parameter_grid_rejects_invalid_declarations(grid):
    with pytest.raises(ValidationError):
        ParameterGrid(grid)


def test_strategy_spec_accepts_mapping_grid():
    spec = StrategySpec(
        name="momentum",
        backtest_fn_path="tests.validation.conftest.backtest_noise",
        parameter_grid={"lookback": [5], "threshold": [0.0]},
    )

    assert spec.parameter_grid.size == 1
    assert spec.qualified_path == "tests.validation.conftest.backtest_noise"

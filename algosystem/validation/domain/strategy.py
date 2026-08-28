"""Strategy parameter value objects for validation runs."""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from algosystem.shared.errors import ValidationError


@dataclass(frozen=True, slots=True, init=False, eq=False)
class ParameterSet(Mapping[str, object]):
    """One immutable strategy parameter combination."""

    _items: tuple[tuple[str, object], ...]

    def __init__(self, values: Mapping[str, object] | Iterable[tuple[str, object]]) -> None:
        items = _normalize_parameter_items(values)
        try:
            hash(items)
        except TypeError as exc:
            raise ValidationError("parameter values must be hashable") from exc
        object.__setattr__(self, "_items", items)

    def __getitem__(self, key: str) -> object:
        for name, value in self._items:
            if name == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (name for name, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return repr(self.to_dict())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return self.to_dict() == dict(other.items())
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._items)

    def to_dict(self) -> dict[str, object]:
        """Return a mutable dict copy for legacy strategy functions."""
        return dict(self._items)


@dataclass(frozen=True, slots=True, init=False)
class ParameterGrid:
    """Immutable Cartesian parameter-grid declaration."""

    _items: tuple[tuple[str, tuple[object, ...]], ...]

    def __init__(self, values: Mapping[str, Sequence[object]]) -> None:
        if not isinstance(values, Mapping):
            raise ValidationError("parameter grid must be a mapping")
        if not values:
            raise ValidationError("parameter grid must not be empty")

        normalized: list[tuple[str, tuple[object, ...]]] = []
        for raw_name, raw_values in values.items():
            name = _normalize_parameter_name(raw_name)
            if isinstance(raw_values, (str, bytes)) or not isinstance(raw_values, Sequence):
                raise ValidationError(f"parameter {name!r} values must be a non-empty sequence")
            value_tuple = tuple(raw_values)
            if not value_tuple:
                raise ValidationError(f"parameter {name!r} has no values")
            _validate_unique_hashable_values(name, value_tuple)
            normalized.append((name, value_tuple))

        normalized.sort(key=lambda item: item[0])
        total = 1
        for _, value_tuple in normalized:
            total *= len(value_tuple)
        if total == 0:
            raise ValidationError("parameter grid would produce zero combinations")

        object.__setattr__(self, "_items", tuple(normalized))

    @property
    def size(self) -> int:
        """Return the number of Cartesian-product combinations."""
        total = 1
        for _, value_tuple in self._items:
            total *= len(value_tuple)
        return total

    def combinations(self) -> Iterator[ParameterSet]:
        """Yield all parameter combinations in stable name-sorted order."""
        keys = [name for name, _ in self._items]
        value_lists = [values for _, values in self._items]
        for combo in itertools.product(*value_lists):
            yield ParameterSet(zip(keys, combo))

    def to_dict(self) -> dict[str, list[object]]:
        """Return a mutable dict copy preserving stable parameter order."""
        return {name: list(values) for name, values in self._items}


@dataclass(frozen=True, slots=True)
class StrategySpec:
    """Picklable description of a parameterized strategy validation run."""

    name: str
    backtest_fn_path: str
    parameter_grid: ParameterGrid

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("strategy name must be a non-empty string")
        if not isinstance(self.backtest_fn_path, str) or not self.backtest_fn_path.strip():
            raise ValidationError("backtest_fn path must be a non-empty string")
        if "." not in self.backtest_fn_path:
            raise ValidationError("backtest_fn path must be a qualified module path")
        if not isinstance(self.parameter_grid, ParameterGrid):
            if isinstance(self.parameter_grid, Mapping):
                object.__setattr__(self, "parameter_grid", ParameterGrid(self.parameter_grid))
            else:
                raise ValidationError("strategy parameter_grid must be a ParameterGrid")

    @property
    def qualified_path(self) -> str:
        """Return the qualified path of the strategy evaluator."""
        return self.backtest_fn_path


def _normalize_parameter_items(
    values: Mapping[str, object] | Iterable[tuple[str, object]],
) -> tuple[tuple[str, object], ...]:
    if isinstance(values, Mapping):
        raw_items = list(values.items())
    else:
        raw_items = list(values)
    if not raw_items:
        raise ValidationError("parameter set must not be empty")

    names: set[str] = set()
    normalized: list[tuple[str, object]] = []
    for raw_name, value in raw_items:
        name = _normalize_parameter_name(raw_name)
        if name in names:
            raise ValidationError(f"duplicate parameter name: {name}")
        names.add(name)
        normalized.append((name, value))
    normalized.sort(key=lambda item: item[0])
    return tuple(normalized)


def _normalize_parameter_name(raw_name: object) -> str:
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise ValidationError("parameter names must be non-empty strings")
    return raw_name


def _validate_unique_hashable_values(name: str, values: tuple[object, ...]) -> None:
    seen: set[object] = set()
    for value in values:
        try:
            if value in seen:
                raise ValidationError(f"parameter {name!r} has duplicate value {value!r}")
            seen.add(value)
        except TypeError as exc:
            raise ValidationError(f"parameter {name!r} values must be hashable") from exc

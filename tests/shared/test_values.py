import math
import re

import pandas as pd
import pytest

from algosystem.shared.errors import ConfigurationError, InvalidCapitalError, InvalidDateRangeError
from algosystem.shared.values import DateRange, Money, Percent, Ratio, RunId


@pytest.mark.parametrize("bad_amount", [math.nan, math.inf, -math.inf])
def test_money_rejects_non_finite_amounts(bad_amount):
    with pytest.raises(InvalidCapitalError):
        Money(bad_amount)


def test_money_rejects_invalid_currency():
    with pytest.raises(ConfigurationError):
        Money(100, "US")


def test_money_arithmetic_requires_same_currency():
    assert Money(100) + Money(50) == Money(150)
    assert Money(100) - Money(50) == Money(50)
    assert Money(100) * 1.5 == Money(150)
    assert 2 * Money(100) == Money(200)
    assert str(Money(1234.56)) == "$1,234.56"

    with pytest.raises(InvalidCapitalError):
        Money(100, "USD") + Money(100, "EUR")


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_ratio_rejects_non_finite_values(bad_value):
    with pytest.raises(InvalidCapitalError):
        Ratio(bad_value)


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_percent_rejects_non_finite_values(bad_value):
    with pytest.raises(InvalidCapitalError):
        Percent(bad_value)


def test_percent_round_trips_fraction_and_percent_units():
    percent = Percent(0.0523)
    assert percent.as_fraction == pytest.approx(0.0523)
    assert percent.as_percent == pytest.approx(5.23)
    assert str(percent) == "5.23%"

    from_display_value = Percent.from_percent(5.23)
    assert from_display_value.as_fraction == pytest.approx(0.0523)
    assert from_display_value.as_percent == pytest.approx(5.23)


@pytest.mark.parametrize("bad_run_id", ["", "has space", "tab\tid"])
def test_run_id_rejects_empty_or_whitespace_values(bad_run_id):
    with pytest.raises(ConfigurationError):
        RunId(bad_run_id)


def test_run_id_generate_uses_unique_timestamp_format():
    generated = [RunId.generate().value for _ in range(5)]

    assert len(set(generated)) == len(generated)
    for run_id in generated:
        assert re.fullmatch(r"\d{8}_\d{6}_\d{3}", run_id)


def test_date_range_rejects_end_before_start():
    with pytest.raises(InvalidDateRangeError):
        DateRange(pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-01"))


def test_date_range_mask_selects_expected_rows():
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    date_range = DateRange("2020-01-02", "2020-01-04")

    selected = index[date_range.mask(index)]

    assert list(selected) == list(pd.date_range("2020-01-02", periods=3, freq="D"))
    assert date_range.contains(pd.Timestamp("2020-01-03"))
    assert not date_range.contains(pd.Timestamp("2020-01-05"))
    assert date_range.days == 2


def test_date_range_from_index_requires_non_empty_datetime_index():
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    date_range = DateRange.from_index(index)

    assert date_range.start == pd.Timestamp("2020-01-01")
    assert date_range.end == pd.Timestamp("2020-01-03")

    with pytest.raises(InvalidDateRangeError):
        DateRange.from_index(pd.DatetimeIndex([]))

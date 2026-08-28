from algosystem.shared.errors import (
    AlgoSystemError,
    CalculationError,
    ConfigurationError,
    DomainError,
    DuplicateRunError,
    InvalidCapitalError,
    InvalidDateRangeError,
    InvalidPriceSeriesError,
    MarketDataError,
    RepositoryError,
    RunNotFoundError,
    UnknownBenchmarkError,
)


def test_error_hierarchy_is_rooted_at_algosystem_error():
    error_classes = [
        DomainError,
        InvalidPriceSeriesError,
        InvalidDateRangeError,
        InvalidCapitalError,
        CalculationError,
        RepositoryError,
        DuplicateRunError,
        MarketDataError,
        UnknownBenchmarkError,
        ConfigurationError,
    ]

    for error_class in error_classes:
        assert issubclass(error_class, AlgoSystemError)


def test_run_not_found_error_keeps_run_id():
    error = RunNotFoundError("20240101_120000_001")

    assert error.run_id == "20240101_120000_001"
    assert "20240101_120000_001" in str(error)


def test_duplicate_run_error_keeps_run_id():
    error = DuplicateRunError("20240101_120000_001")

    assert error.run_id == "20240101_120000_001"
    assert "already exists" in str(error)

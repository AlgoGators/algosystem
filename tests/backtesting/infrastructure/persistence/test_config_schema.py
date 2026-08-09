import pytest
from sqlalchemy import String

from algosystem.backtesting.infrastructure.persistence import schema
from algosystem.backtesting.infrastructure.persistence.config import DatabaseConfig
from algosystem.shared.errors import ConfigurationError
from algosystem.shared.metric_key import MetricKey


def test_database_config_from_env_is_explicit_and_redacts_password():
    config = DatabaseConfig.from_env(
        {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "algosystem",
            "DB_USER": "tester",
            "DB_PASSWORD": "secret",
        }
    )

    assert config.host == "localhost"
    assert config.port == 5432
    assert config.schema == "backtest"
    assert config.url() == "postgresql://tester:secret@localhost:5432/algosystem"
    assert "secret" not in repr(config)
    assert "<redacted>" in repr(config)


def test_database_config_reports_the_missing_field_name():
    with pytest.raises(ConfigurationError, match="password"):
        DatabaseConfig.from_env(
            {
                "DB_HOST": "localhost",
                "DB_PORT": "5432",
                "DB_NAME": "algosystem",
                "DB_USER": "tester",
            }
        )


def test_results_columns_are_generated_from_metric_key_and_run_ids_are_strings():
    result_columns = set(schema.Result.__table__.columns.keys())

    assert {metric_key.value for metric_key in MetricKey}.issubset(result_columns)
    assert "win_rate" not in result_columns
    assert "profit_factor" not in result_columns
    assert "total_trades" not in result_columns
    assert "downside_volatility" not in result_columns

    for table in (
        schema.RunMetadata.__table__,
        schema.EquityCurve.__table__,
        schema.Result.__table__,
        schema.FinalPosition.__table__,
        schema.SymbolPnl.__table__,
    ):
        assert isinstance(table.c.run_id.type, String)

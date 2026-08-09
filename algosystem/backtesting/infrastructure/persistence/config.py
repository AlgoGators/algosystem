"""Explicit database configuration for persistence adapters."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import quote_plus

from algosystem.shared.errors import ConfigurationError

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, repr=False)
class DatabaseConfig:
    """Database settings supplied explicitly by callers."""

    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str = "backtest"
    pool_size: int = 5

    def __post_init__(self) -> None:
        host = self._require_text("host", self.host)
        database = self._require_text("database", self.database)
        user = self._require_text("user", self.user)
        password = self._require_text("password", self.password)
        schema = self._require_text("schema", self.schema)
        if _IDENTIFIER_RE.fullmatch(schema) is None:
            raise ConfigurationError("schema must be a valid SQL identifier")

        port = self._require_int("port", self.port)
        if port <= 0 or port > 65535:
            raise ConfigurationError("port must be between 1 and 65535")

        pool_size = self._require_int("pool_size", self.pool_size)
        if pool_size <= 0:
            raise ConfigurationError("pool_size must be positive")

        object.__setattr__(self, "host", host)
        object.__setattr__(self, "database", database)
        object.__setattr__(self, "user", user)
        object.__setattr__(self, "password", password)
        object.__setattr__(self, "schema", schema)
        object.__setattr__(self, "port", port)
        object.__setattr__(self, "pool_size", pool_size)

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "DatabaseConfig":
        """Build configuration from the required DB_* environment variables."""
        source = os.environ if env is None else env
        return cls(
            host=cls._read_env(source, "DB_HOST", "host"),
            port=cls._read_env(source, "DB_PORT", "port"),
            database=cls._read_env(source, "DB_NAME", "database"),
            user=cls._read_env(source, "DB_USER", "user"),
            password=cls._read_env(source, "DB_PASSWORD", "password"),
        )

    def url(self) -> str:
        """Return a SQLAlchemy PostgreSQL connection URL."""
        return (
            "postgresql://"
            f"{quote_plus(self.user)}:{quote_plus(self.password)}"
            f"@{quote_plus(self.host)}:{self.port}/{quote_plus(self.database)}"
        )

    def __repr__(self) -> str:
        return (
            "DatabaseConfig("
            f"host={self.host!r}, "
            f"port={self.port!r}, "
            f"database={self.database!r}, "
            f"user={self.user!r}, "
            "password='<redacted>', "
            f"schema={self.schema!r}, "
            f"pool_size={self.pool_size!r})"
        )

    @staticmethod
    def _read_env(source: Mapping[str, str], env_name: str, field_name: str) -> str:
        value = source.get(env_name)
        if value is None or str(value).strip() == "":
            raise ConfigurationError(f"missing database config field: {field_name}")
        return str(value)

    @staticmethod
    def _require_text(field_name: str, value: object) -> str:
        if value is None or str(value).strip() == "":
            raise ConfigurationError(f"missing database config field: {field_name}")
        return str(value)

    @staticmethod
    def _require_int(field_name: str, value: object) -> int:
        if value is None or str(value).strip() == "":
            raise ConfigurationError(f"missing database config field: {field_name}")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(f"{field_name} must be an integer") from exc

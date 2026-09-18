# Changelog

## Unreleased

- Exposed regime-conditional performance analysis through the validation stack:
  an `AnalyzeRegimes` use case, `AlgoSystem.analyze_regimes()`, an `algosystem
  regimes` CLI command, and a `RegimeResult.to_metrics()` accessor keyed by
  `ValidationMetricKey`. The underlying `regime_conditional_performance`
  statistics were already present but unreachable from any public entry point.
- Added the validation context for overfitting detection, porting John Riley's
  <john.p.riley1287@gmail.com> statistical core, shipped strategy archetypes,
  chart/report adapters, CLI commands, and facade methods into the
  domain-driven layout.
- Removed the custom dashboard, Flask editor, component configuration system, and
  PowerPoint-oriented reporting surface. quantstats tearsheets are now the reporting path.
- Split benchmark market data into domain catalog, provider/cache ports, yfinance
  provider, parquet cache adapter, and a fetch use case.
- Removed checked-in parquet benchmark cache files from the package. Benchmark
  data now fills an external user cache on demand.
- Replaced the CLI with thin `backtest`, `tearsheet`, `benchmarks`, and `db`
  command adapters.
- Added import-linter contracts and CI checks for the domain-driven package rules.
- Curated the top-level public API and kept heavy adapters lazy on `import algosystem`.
- Deprecated legacy Engine and quick-backtest style entry points remain as shims;
  new code should use `AlgoSystem().backtest()` and `run_backtest()`.

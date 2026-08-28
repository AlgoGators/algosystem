# Examples

Runnable notebooks for the two things AlgoSystem does.

| Notebook | What it covers |
|---|---|
| [`01_backtesting.ipynb`](01_backtesting.ipynb) | Running a backtest from an equity curve, reading metrics, benchmark comparison, quantstats tearsheet, saving and reloading a run |
| [`02_parameter_sensitivity.ipynb`](02_parameter_sensitivity.ipynb) | Overfitting detection, Sobol sensitivity indices, the parameter surface, cost sensitivity, and the HTML validation report |

Read them in order. The first measures a single equity curve; the second asks
whether that curve was found or merely chosen out of many attempts.

## Running them

```bash
poetry install
poetry run jupyter lab examples/
```

Both notebooks use synthetic data, so they run offline with no database and no
network access.

Each writes an HTML file into `examples/` when executed. Those are gitignored.

## A note on the numbers

The data in `02_parameter_sensitivity.ipynb` is deliberately noise with a
negligible drift, so the honest verdict is "no edge" — a p-value near 1.0, a PBO
near 1.0, and a negative deflated Sharpe. That is the method working, not
failing. A best-of-80 Sharpe near 0.9 on pure noise is exactly the trap the
validation context exists to catch.

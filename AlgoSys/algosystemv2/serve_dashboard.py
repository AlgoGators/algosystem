"""Generate overfit dashboard with all sections and serve on localhost."""

import http.server
import os
import webbrowser

import numpy as np

from algosystemv2.overfitting import OverfitDetector
from algosystemv2.overfitting.strategies.momentum import momentum_backtest
from algosystemv2.overfitting.dashboard import generate_overfit_dashboard
from algosystemv2.overfitting.cscv import compute_pbo
from algosystemv2.overfitting.walkforward import walk_forward_analysis
from algosystemv2.overfitting.diagnostics import check_autocorrelation
from algosystemv2.overfitting.robustness import (
    bootstrap_sharpe_ci,
    kelly_criterion,
    regime_conditional_performance,
)


def main():
    # Generate trending data with a planted signal
    rng = np.random.default_rng(100)
    n = 5000
    returns = np.empty(n)
    regime = 1.0
    for i in range(n):
        if rng.random() < 0.005:
            regime *= -1
        returns[i] = regime * 0.0015 + rng.normal(0.0, 0.01)

    param_grid = {
        'lookback': [3, 5, 8, 10, 15, 20, 30, 40, 60, 80, 100, 120],
        'threshold': [-0.002, -0.001, -0.0005, 0.0, 0.0002, 0.0005,
                      0.001, 0.0015, 0.002, 0.003],
    }

    print("Running overfitting detection (this may take a minute)...")
    det = OverfitDetector(
        backtest_fn=momentum_backtest,
        returns=returns,
        param_grid=param_grid,
        n_reps=200,
        shuffle_method='complete',
        n_workers=1,
        seed=42,
    )
    results = det.run()
    results.report()

    # Build returns matrix for PBO (T x N) — need per-period returns, not scalar Sharpe
    print("\nRunning PBO (CSCV)...")
    param_list = det.param_list
    def momentum_returns_series(params, rets):
        lb = params['lookback']
        th = params['threshold']
        nn = len(rets)
        if nn <= lb:
            return np.zeros(nn - max(p['lookback'] for p in param_list))
        cumsum = np.cumsum(rets)
        rm = np.empty(nn)
        rm[:lb] = 0.0
        rm[lb:] = (cumsum[lb:] - cumsum[:nn - lb]) / lb
        signal = (rm > th).astype(float)
        strat_rets = signal * rets
        # Trim to common length (max lookback)
        max_lb = max(p['lookback'] for p in param_list)
        return strat_rets[max_lb:]

    returns_matrix = np.column_stack([
        momentum_returns_series(p, returns) for p in param_list
    ])
    pbo_results = compute_pbo(returns_matrix, n_splits=8)

    # Walk-forward
    print("Running walk-forward validation...")
    wf_results = walk_forward_analysis(
        backtest_fn=momentum_backtest,
        returns=returns,
        param_grid=param_grid,
        n_folds=8,
    )

    # Autocorrelation diagnostics
    print("Running autocorrelation diagnostics...")
    ac_diagnostic = check_autocorrelation(returns)

    # Robustness checks
    print("Running robustness checks...")
    robustness = {}
    robustness['sharpe_ci'] = bootstrap_sharpe_ci(returns)
    robustness['kelly'] = kelly_criterion(returns)
    robustness['regime'] = regime_conditional_performance(returns)

    # Generate the dashboard
    output_path = os.path.join(os.path.dirname(__file__), "test_output", "overfit_dashboard.html")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    generate_overfit_dashboard(
        results=results,
        pbo_results=pbo_results,
        wf_results=wf_results,
        ac_diagnostic=ac_diagnostic,
        robustness=robustness,
        output_path=output_path,
        open_browser=False,
        title="Overfitting Detection Report - Momentum Strategy",
    )
    print(f"\nDashboard generated: {output_path}")

    # Serve on localhost
    serve_dir = os.path.dirname(output_path)
    filename = os.path.basename(output_path)
    port = 8765

    os.chdir(serve_dir)
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("127.0.0.1", port), handler)

    url = f"http://127.0.0.1:{port}/{filename}"
    print(f"\nServing at {url}")
    print("Press Ctrl+C to stop.\n")

    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()

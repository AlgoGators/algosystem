"""
Analyze each strategy from the graphs for overfitting.
Runs: permutation test, PSR, DSR, surface analysis, walk-forward.
"""
import numpy as np
from algosystemv2.overfitting import (
    OverfitDetector, probabilistic_sharpe_ratio, deflated_sharpe_ratio,
    walk_forward_analysis,
)
from algosystemv2.overfitting.strategies.dual_momentum import dual_momentum_backtest
from algosystemv2.overfitting.strategies.volatility import vol_regime_backtest
from algosystemv2.overfitting.strategies.mean_reversion import mean_reversion_backtest
from algosystemv2.overfitting.data_generators import generate_noise, generate_trending

noise = generate_noise(n=3000, seed=42)
trending = generate_trending(n=3000, seed=42)

strategies = [
    {
        'name': 'Dual Momentum on NOISE',
        'fn': dual_momentum_backtest,
        'data': noise,
        'data_label': 'noise',
        'grid': {
            'fast_lookback': [3, 5, 10, 15],
            'slow_lookback': [20, 40, 60, 80],
            'threshold': [0.0, 0.0005, 0.001],
        },
    },
    {
        'name': 'Dual Momentum on TRENDING',
        'fn': dual_momentum_backtest,
        'data': trending,
        'data_label': 'trending',
        'grid': {
            'fast_lookback': [3, 5, 10, 15],
            'slow_lookback': [20, 40, 60, 80],
            'threshold': [0.0, 0.0005, 0.001],
        },
    },
    {
        'name': 'Vol Regime on NOISE',
        'fn': vol_regime_backtest,
        'data': noise,
        'data_label': 'noise',
        'grid': {
            'vol_lookback': [10, 20, 30, 40],
            'vol_threshold': [0.10, 0.15, 0.20, 0.25, 0.30],
            'low_weight': [0.1, 0.3, 0.5],
            'high_weight': [0.8, 1.0, 1.5],
        },
    },
    {
        'name': 'Vol Regime on TRENDING',
        'fn': vol_regime_backtest,
        'data': trending,
        'data_label': 'trending',
        'grid': {
            'vol_lookback': [10, 20, 30, 40],
            'vol_threshold': [0.10, 0.15, 0.20, 0.25, 0.30],
            'low_weight': [0.1, 0.3, 0.5],
            'high_weight': [0.8, 1.0, 1.5],
        },
    },
    {
        'name': 'Mean Reversion on NOISE',
        'fn': mean_reversion_backtest,
        'data': noise,
        'data_label': 'noise',
        'grid': {
            'lookback': [10, 15, 20, 30, 40],
            'entry_z': [1.0, 1.5, 2.0, 2.5],
            'exit_z': [0.0, 0.25, 0.5],
        },
    },
]

n_reps = 300

for s in strategies:
    print("\n" + "=" * 72)
    print(f"  {s['name']}")
    print(f"  Data: {s['data_label']} | Combos: {np.prod([len(v) for v in s['grid'].values()])}")
    print("=" * 72)

    # 1. Permutation test
    det = OverfitDetector(
        backtest_fn=s['fn'], returns=s['data'],
        param_grid=s['grid'], n_reps=n_reps, n_workers=1, seed=42,
    )
    res = det.run()

    # 2. Surface analysis
    sa = res.surface_analysis()

    # 3. DSR
    dsr = deflated_sharpe_ratio(
        s['data'], n_trials=res.n_params,
        all_sharpes=res.original_sharpes,
        sr_hat=res.best_sharpe,
    )

    # 4. Walk-forward
    try:
        wf = walk_forward_analysis(
            backtest_fn=s['fn'], returns=s['data'],
            param_grid=s['grid'], n_folds=5,
        )
        wfe = wf.wfe
        mean_oos = wf.mean_oos_sharpe
        frac_oos_pos = wf.frac_oos_positive
        vetoed = wf.vetoed
    except Exception as e:
        wfe = 0.0
        mean_oos = 0.0
        frac_oos_pos = 0.0
        vetoed = False

    # Print results
    print(f"\n--- RESULTS ---")
    print(f"Best Sharpe (S*):        {res.best_sharpe:.4f}")
    print(f"Best params:             {res.param_list[res.best_param_index]}")
    print(f"")
    print(f"TEST 1 - Permutation p-value:  {res.unbiased_pvalue:.4f}")
    print(f"  Interpretation: ", end="")
    if res.unbiased_pvalue < 0.05:
        print("SIGNIFICANT (p < 0.05) -- unlikely due to chance")
    elif res.unbiased_pvalue < 0.10:
        print("MARGINAL (0.05 < p < 0.10)")
    else:
        print(f"NOT SIGNIFICANT (p = {res.unbiased_pvalue:.2f}) -- could easily be chance")

    print(f"")
    print(f"TEST 2 - Prob of overfitting:  {res.prob_overfit:.4f}")
    print(f"  Interpretation: ", end="")
    if res.prob_overfit > 0.5:
        print(f"{res.prob_overfit:.0%} of random shuffles beat your best -- LIKELY OVERFIT")
    elif res.prob_overfit > 0.1:
        print(f"{res.prob_overfit:.0%} of random shuffles beat your best -- BORDERLINE")
    else:
        print(f"Only {res.prob_overfit:.0%} of random shuffles beat your best -- REAL SIGNAL")

    print(f"")
    print(f"TEST 3 - Deflated Sharpe (DSR): {dsr.dsr:.4f}")
    print(f"  SR0* (haircut):        {dsr.sr0_star:.4f}")
    print(f"  Interpretation: ", end="")
    if dsr.dsr > 0.95:
        print("PASSES -- Sharpe survives multi-trial correction")
    else:
        print("FAILS -- Sharpe doesn't survive the haircut")

    print(f"")
    print(f"TEST 4 - Surface analysis:")
    print(f"  Plateau score:         {sa['plateau_score']:.4f}", end="")
    if sa['plateau_score'] > 0.2:
        print("  (BROAD PLATEAU -- robust)")
    elif sa['plateau_score'] > 0.05:
        print("  (narrow peak -- fragile)")
    else:
        print("  (ISOLATED SPIKE -- overfit)")
    print(f"  Frac positive:         {sa['frac_positive']:.4f}", end="")
    if sa['frac_positive'] > 0.5:
        print("  (majority of combos profitable -- structural edge)")
    else:
        print(f"  (only {sa['frac_positive']:.0%} of combos work -- cherry-picked)")
    print(f"  Robustness ratio:      {sa['robustness_ratio']:.4f}", end="")
    if sa['robustness_ratio'] > 0.8:
        print("  (neighbors perform similarly -- stable)")
    else:
        print("  (neighbors much worse -- fragile peak)")

    print(f"")
    print(f"TEST 5 - Walk-forward:")
    print(f"  WFE:                   {wfe:.4f}", end="")
    if wfe >= 0.7:
        print("  (EXCELLENT -- generalizes to new data)")
    elif wfe >= 0.5:
        print("  (PASSING)")
    elif wfe >= 0.3:
        print("  (WEAK)")
    else:
        print("  (FAILING -- does not generalize)")
    print(f"  Mean OOS Sharpe:       {mean_oos:.4f}")
    print(f"  Frac OOS positive:     {frac_oos_pos:.0%}")
    if vetoed:
        print(f"  CATASTROPHIC VETO:     YES")

    # Final verdict
    print(f"\n{'='*40}")
    scores = []
    scores.append(1.0 if res.unbiased_pvalue < 0.05 else 0.0)
    scores.append(1.0 if res.prob_overfit < 0.1 else 0.0)
    scores.append(1.0 if dsr.dsr > 0.95 else 0.0)
    scores.append(1.0 if sa['plateau_score'] > 0.2 else 0.0)
    scores.append(1.0 if sa['frac_positive'] > 0.5 else 0.0)
    scores.append(1.0 if wfe >= 0.5 else 0.0)

    passed = sum(scores)
    if passed >= 5:
        verdict = "GENUINE SIGNAL"
    elif passed >= 3:
        verdict = "MARGINAL -- needs more data"
    elif passed >= 1:
        verdict = "LIKELY OVERFIT"
    else:
        verdict = "OVERFIT -- noise mining"

    print(f"  Tests passed: {int(passed)}/6")
    print(f"  VERDICT: {verdict}")
    print(f"{'='*40}")

print("\n\nDONE")

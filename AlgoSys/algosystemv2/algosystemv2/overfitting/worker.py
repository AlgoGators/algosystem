"""
Multiprocessing worker for permutation passes.

Separated from the detector to keep the module boundary clean and
ensure picklability for multiprocessing.
"""

from __future__ import annotations

import numpy as np

from .shufflers import SHUFFLE_METHODS


def worker_run_pass(args):
    """
    Run one permutation pass (or the unpermuted pass).

    Returns (irep, sharpes_array) where sharpes_array has one Sharpe per
    parameter combination.
    """
    (irep, returns, param_list, backtest_fn, shuffle_method,
     block_size, seed, subsample_indices) = args

    rng = np.random.default_rng(seed)

    if irep == 0:
        shuffled = returns  # unpermuted
    else:
        shuffle_fn = SHUFFLE_METHODS.get(shuffle_method)
        if shuffle_fn is None:
            raise ValueError(f"Unknown shuffle method: {shuffle_method}")

        if shuffle_method == 'block':
            shuffled = shuffle_fn(returns, rng, block_size)
        else:
            shuffled = shuffle_fn(returns, rng)

    if subsample_indices is not None:
        eval_params = [param_list[i] for i in subsample_indices]
    else:
        eval_params = param_list

    sharpes = np.empty(len(eval_params), dtype=np.float64)
    for i, params in enumerate(eval_params):
        sharpes[i] = backtest_fn(params, shuffled)

    return irep, sharpes

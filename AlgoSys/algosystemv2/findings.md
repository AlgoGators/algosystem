# Findings

## Research Summary (completed prior to planning)

### VarScreen Manual (Timothy Masters, v3.1a PDF)
- **Solo p-value**: P(random candidate achieves this performance by luck). Uniform under null.
- **Unbiased p-value**: P(BEST candidate achieves this by luck if ALL are worthless). Corrects selection bias.
- **Stepwise algorithm** (p29-36): Romano-Wolf inspired. Tests hypotheses best-to-worst, each time computing max of ONLY not-yet-rejected competitors. Shrinks null at each step. Gives correct (not conservative) p-values for ALL competitors. Uses `count[i]/(m+1) <= alpha` with FWE control.
- **Critical warning** (p6,10): Permutation tests "fall apart" with serial correlation. Cyclic permutation partially helps but is "far from complete."
- **CSCV column** (p7): Bailey/Lopez de Prado PBO method implemented as supplementary metric.

### Reference C++ Code (RANSAC.CPP)
- Comparison direction: MINIMIZES criterion (we MAXIMIZE Sharpe — comparisons flipped)
- Running-best loop: worst-to-best sweep, tracks `running_best` permuted criterion
- Counts initialized to 1 (Phipson & Smyth 2010: p = (b+1)/(m+1))
- Monotonicity enforcement: `if (pval < prior) pval = prior`

### P-Hacking Research (web research agent)
- **Analytical DSR**: `DSR = Phi[(SR - SR0)*sqrt(T-1) / sqrt(1 - gamma3*SR + (gamma4-1)/4*SR^2)]`
- **SR0** (expected max under null): `sqrt(V[SR]) * ((1-0.5772)*Phi_inv(1-1/N) + 0.5772*Phi_inv(1-1/(N*e)))`
- **PBO algorithm**: Split T into S blocks, form C(S,S/2) IS/OOS combos, compute logit of best-IS rank in OOS, PBO = P(logit < 0)
- **Walk-Forward Efficiency**: WFE = SR_OOS / SR_IS >= 0.50 is passing
- **MinTRL formula**: Minimum track record length to reject null at given confidence

### Current System State
- 8 files in overfitting module (detector, results, visualization, worker, shufflers, data_generators, strategies/)
- 62 tests, all passing
- Traditional "best-of" MCPT implemented correctly
- Surface analysis (Sobol, robustness, plateau) implemented
- NO stepwise test, NO autocorrelation detection, NO CSCV/PBO, NO analytical DSR, NO walk-forward, NO integration with algosystemv2 engine/CLI

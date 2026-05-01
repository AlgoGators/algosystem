"""
Self-contained HTML dashboard for overfitting detection results.

Follows the same pattern as algosystemv2's backtesting dashboard:
single HTML file with embedded Plotly charts, no server required.

Combines all overfitting detection results into one interactive report.
"""

from __future__ import annotations

import json
import os
import webbrowser
from typing import Optional

import numpy as np


def generate_overfit_dashboard(
    results,
    pbo_results=None,
    wf_results=None,
    ac_diagnostic=None,
    robustness: dict | None = None,
    output_path: str | None = None,
    open_browser: bool = True,
    title: str = "Overfitting Detection Report",
) -> str:
    """
    Generate a self-contained HTML overfitting detection dashboard.

    Parameters
    ----------
    results : OverfitResults
        Core permutation test results.
    pbo_results : PBOResults, optional
        CSCV/PBO results.
    wf_results : WalkForwardResults, optional
        Walk-forward analysis results.
    ac_diagnostic : AutocorrelationDiagnostic, optional
        Autocorrelation check results.
    robustness : dict, optional
        Dict with keys: 'sharpe_ci', 'monte_carlo', 'alpha_beta',
        'kelly', 'regime' — from the robustness module.
    output_path : str, optional
        Output file path. Defaults to ./overfit_report.html.
    open_browser : bool
        Auto-open in browser.
    title : str
        Report title.

    Returns
    -------
    str : path to generated HTML file
    """
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "overfit_report.html")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    data = _build_data(results, pbo_results, wf_results, ac_diagnostic, robustness)
    html = _build_html(data, title)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    if open_browser:
        webbrowser.open("file://" + os.path.abspath(output_path))

    return output_path


def _safe_float(v, default=0.0):
    if v is None:
        return default
    v = float(v)
    if not np.isfinite(v):
        return default
    return round(v, 6)


def _build_data(results, pbo_results, wf_results, ac_diagnostic, robustness):
    """Build JSON-safe data dict for the dashboard."""
    d = {}

    # Core results
    d['best_sharpe'] = _safe_float(results.best_sharpe)
    d['unbiased_pvalue'] = _safe_float(results.unbiased_pvalue)
    d['prob_overfit'] = _safe_float(results.prob_overfit)
    d['deflated_sharpe'] = _safe_float(results.deflated_sharpe)
    d['n_params'] = results.n_params
    d['n_reps'] = results.n_reps
    d['shuffle_method'] = results.shuffle_method
    d['best_params'] = str(results.param_list[results.best_param_index])

    # Null distribution
    d['null_sharpes'] = [_safe_float(v) for v in results.null_best_sharpes]

    # Solo vs unbiased p-values
    n_show = min(results.n_params, 30)
    d['pvalue_ranks'] = list(range(1, n_show + 1))
    d['solo_pvals'] = [_safe_float(results.solo_pvalues[results.sort_indices[i]])
                       for i in range(n_show)]
    d['unbiased_pvals'] = [_safe_float(results.unbiased_pvalues[i])
                           for i in range(n_show)]

    # Surface analysis
    sa = results.surface_analysis()
    d['plateau_score'] = _safe_float(sa['plateau_score'])
    d['robustness_ratio'] = _safe_float(sa['robustness_ratio'])
    d['frac_positive'] = _safe_float(sa['frac_positive'])

    # Parameter surface heatmap
    param_keys = sorted({k for p in results.param_list for k in p})
    if len(param_keys) >= 2:
        px, py = param_keys[0], param_keys[1]
        xvals = sorted(set(p[px] for p in results.param_list))
        yvals = sorted(set(p[py] for p in results.param_list))
        grid = [[None] * len(xvals) for _ in range(len(yvals))]
        counts = [[0] * len(xvals) for _ in range(len(yvals))]
        for i, p in enumerate(results.param_list):
            xi, yi = xvals.index(p[px]), yvals.index(p[py])
            if grid[yi][xi] is None:
                grid[yi][xi] = 0.0
            grid[yi][xi] += results.original_sharpes[i]
            counts[yi][xi] += 1
        for yi in range(len(yvals)):
            for xi in range(len(xvals)):
                if counts[yi][xi] > 0:
                    grid[yi][xi] = round(grid[yi][xi] / counts[yi][xi], 4)
        d['heatmap'] = {
            'z': grid,
            'x': [str(v) for v in xvals],
            'y': [str(v) for v in yvals],
            'xlabel': px,
            'ylabel': py,
        }

    # PBO
    if pbo_results is not None:
        d['pbo'] = _safe_float(pbo_results.pbo)
        finite_logits = pbo_results.logits[np.isfinite(pbo_results.logits)]
        d['pbo_logits'] = [_safe_float(v) for v in finite_logits]

    # Walk-forward
    if wf_results is not None:
        d['wfe'] = _safe_float(wf_results.wfe)
        d['wf_is'] = [_safe_float(v) for v in wf_results.is_sharpes]
        d['wf_oos'] = [_safe_float(v) for v in wf_results.oos_sharpes]
        d['wf_vetoed'] = wf_results.vetoed

    # Autocorrelation
    if ac_diagnostic is not None:
        d['acf_values'] = [_safe_float(v) for v in ac_diagnostic.acf_values]
        d['acf_has_ac'] = ac_diagnostic.has_autocorrelation
        d['acf_recommended'] = ac_diagnostic.recommended_shuffle
        d['acf_lb_pvalue'] = _safe_float(ac_diagnostic.ljung_box_pvalue)

    # Robustness checks
    if robustness:
        if 'sharpe_ci' in robustness:
            ci = robustness['sharpe_ci']
            d['ci_lower'] = _safe_float(ci.ci_lower)
            d['ci_upper'] = _safe_float(ci.ci_upper)
            d['ci_includes_zero'] = ci.ci_includes_zero
        if 'kelly' in robustness:
            k = robustness['kelly']
            d['kelly_fraction'] = _safe_float(k.kelly_fraction)
            d['kelly_edge'] = _safe_float(k.edge)
            d['kelly_has_edge'] = k.has_edge
            d['kelly_win_rate'] = _safe_float(k.win_rate)
        if 'regime' in robustness:
            r = robustness['regime']
            d['regime_names'] = r.regime_names
            d['regime_sharpes'] = [_safe_float(v) for v in r.regime_sharpes]
            d['regime_all'] = r.works_in_all_regimes
        if 'alpha_beta' in robustness:
            ab = robustness['alpha_beta']
            d['alpha_annual'] = _safe_float(ab.alpha_annual)
            d['beta'] = _safe_float(ab.beta)
            d['r_squared'] = _safe_float(ab.r_squared)
            d['is_just_beta'] = ab.is_just_beta

    # Analytical DSR
    if results.returns is not None:
        try:
            adsr = results.analytical_deflated_sharpe()
            d['adsr'] = _safe_float(adsr['dsr'])
            d['sr0'] = _safe_float(adsr['sr0'])
            d['min_trl'] = _safe_float(adsr['min_trl'])
        except Exception:
            pass

    return d


def _build_html(data, title):
    """Build the complete HTML dashboard."""
    data_json = json.dumps(data, default=str)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root {{
    --bg-primary: #0b0e14;
    --bg-card: #151922;
    --bg-card-hover: #1a1f2b;
    --bg-elevated: #1c2231;
    --border: #232a38;
    --border-light: #2e3648;
    --text-primary: #e6eaf0;
    --text-secondary: #8892a4;
    --text-muted: #5c6578;
    --accent-blue: #5b8af5;
    --accent-indigo: #818cf8;
    --accent-green: #34d399;
    --accent-red: #f87171;
    --accent-amber: #fbbf24;
    --accent-purple: #a78bfa;
    --radius: 10px;
    --radius-sm: 6px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
    background: var(--bg-primary);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}}

/* === HEADER === */
.header {{
    background: linear-gradient(180deg, #131825 0%, var(--bg-primary) 100%);
    padding: 32px 40px 24px;
    border-bottom: 1px solid var(--border);
}}
.header-inner {{ max-width: 1440px; margin: 0 auto; }}
.header h1 {{
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.3px;
    margin-bottom: 6px;
}}
.header .subtitle {{
    color: var(--text-muted);
    font-size: 13px;
    font-weight: 400;
    letter-spacing: 0.2px;
}}

/* === VERDICT BAR === */
.verdict-bar {{
    display: flex;
    gap: 10px;
    margin-top: 20px;
    flex-wrap: wrap;
}}
.verdict-item {{
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    padding: 12px 18px;
    border: 1px solid var(--border);
    border-top: 3px solid;
    min-width: 130px;
    transition: background 0.15s;
}}
.verdict-item:hover {{ background: var(--bg-card-hover); }}
.verdict-item .vlabel {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    font-weight: 500;
    margin-bottom: 4px;
}}
.verdict-item .vvalue {{
    font-size: 18px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}}

/* === CONTENT === */
.content {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 28px 40px 48px;
}}

/* === SECTION === */
.section {{
    margin-bottom: 36px;
}}
.section-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
}}
.section-header h2 {{
    font-size: 15px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-secondary);
}}
.section-header .section-badge {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 4px;
    text-transform: uppercase;
}}

/* === GRID === */
.grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}}
.grid-3 {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
}}
.full-span {{ grid-column: 1 / -1; }}

/* === CARD === */
.card {{
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 20px 22px;
    border: 1px solid var(--border);
    transition: border-color 0.15s;
}}
.card:hover {{ border-color: var(--border-light); }}
.card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 14px;
}}
.card-header h3 {{
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-secondary);
}}
.card-header .card-tag {{
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 3px;
    font-weight: 500;
    letter-spacing: 0.3px;
}}
.card-desc {{
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 14px;
    line-height: 1.45;
}}
.chart {{
    width: 100%;
    height: 380px;
}}
.chart-tall {{
    width: 100%;
    height: 420px;
}}

/* === METRICS ROW === */
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px;
    margin-bottom: 16px;
}}
.metric-tile {{
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    border: 1px solid var(--border);
    transition: border-color 0.15s;
}}
.metric-tile:hover {{ border-color: var(--border-light); }}
.metric-tile .mlabel {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    font-weight: 500;
    margin-bottom: 4px;
}}
.metric-tile .mvalue {{
    font-size: 17px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}}
.metric-tile .mdetail {{
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
}}

/* === COLORS === */
.green {{ color: var(--accent-green); }}
.red {{ color: var(--accent-red); }}
.amber {{ color: var(--accent-amber); }}
.blue {{ color: var(--accent-blue); }}
.purple {{ color: var(--accent-purple); }}
.muted {{ color: var(--text-muted); }}

/* === TABLE === */
.info-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.info-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
}}
.info-table td:first-child {{
    color: var(--text-muted);
    font-weight: 500;
    width: 45%;
}}
.info-table td:last-child {{
    font-weight: 600;
    text-align: right;
    font-variant-numeric: tabular-nums;
}}

/* === FOOTER === */
.footer {{
    text-align: center;
    padding: 24px 40px;
    color: var(--text-muted);
    font-size: 11px;
    border-top: 1px solid var(--border);
    letter-spacing: 0.3px;
}}

/* === RESPONSIVE === */
@media (max-width: 960px) {{
    .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
    .header, .content {{ padding-left: 20px; padding-right: 20px; }}
    .metrics-grid {{ grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); }}
}}
</style>
</head>
<body>

<div class="header">
    <div class="header-inner">
        <h1>{title}</h1>
        <div class="subtitle" id="subtitle"></div>
        <div class="verdict-bar" id="verdict-bar"></div>
    </div>
</div>

<div class="content">

    <!-- CORE OVERFITTING DETECTION -->
    <div class="section">
        <div class="section-header">
            <h2>Overfitting Detection</h2>
            <span class="section-badge" id="core-badge" style="background:var(--border);color:var(--text-secondary)">analyzing</span>
        </div>
        <div class="grid-2">
            <div class="card">
                <div class="card-header">
                    <h3>Null Distribution</h3>
                    <span class="card-tag" style="background:rgba(99,102,241,0.15);color:var(--accent-indigo)">permutation</span>
                </div>
                <div class="card-desc">Histogram of best Sharpe ratios under permuted (noise) data. The red dashed line marks your strategy's best Sharpe (S*). If S* is far to the right of the distribution, the signal is likely real.</div>
                <div id="null-dist" class="chart"></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h3>Parameter Surface</h3>
                    <span class="card-tag" style="background:rgba(34,211,153,0.12);color:var(--accent-green)">topology</span>
                </div>
                <div class="card-desc">Sharpe ratio across the 2D parameter grid. A smooth, broad plateau indicates a robust strategy. A narrow spike at a single point suggests overfitting to noise.</div>
                <div id="heatmap" class="chart"></div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h3>P-Value Comparison</h3>
                    <span class="card-tag" style="background:rgba(248,113,113,0.12);color:var(--accent-red)">multiple testing</span>
                </div>
                <div class="card-desc">Solo p-values (testing each parameter set independently) vs unbiased p-values (corrected for multiple testing). The gap between them shows how many false discoveries are averted by the correction.</div>
                <div id="pvalues" class="chart"></div>
            </div>
            <div class="card" id="pbo-card" style="display:none">
                <div class="card-header">
                    <h3>PBO Distribution</h3>
                    <span class="card-tag" style="background:rgba(167,139,250,0.15);color:var(--accent-purple)">CSCV</span>
                </div>
                <div class="card-desc">Logit distribution from Combinatorially Symmetric Cross-Validation. Red bars (logit &lt; 0) indicate folds where the IS-best strategy underperformed the OOS median. PBO &gt; 0.5 = likely overfit.</div>
                <div id="pbo-dist" class="chart"></div>
            </div>
        </div>
    </div>

    <!-- CORE METRICS TABLE -->
    <div class="section">
        <div class="section-header">
            <h2>Core Statistics</h2>
        </div>
        <div class="grid-3">
            <div class="card">
                <table class="info-table" id="core-table-1"></table>
            </div>
            <div class="card">
                <table class="info-table" id="core-table-2"></table>
            </div>
            <div class="card">
                <table class="info-table" id="core-table-3"></table>
            </div>
        </div>
    </div>

    <!-- WALK-FORWARD VALIDATION -->
    <div class="section" id="wf-section" style="display:none">
        <div class="section-header">
            <h2>Walk-Forward Validation</h2>
            <span class="section-badge" id="wf-badge" style="background:var(--border);color:var(--text-secondary)">out-of-sample</span>
        </div>
        <div class="grid-2">
            <div class="card" id="wf-card" style="display:none">
                <div class="card-header">
                    <h3>IS vs OOS Degradation</h3>
                </div>
                <div class="card-desc">Each point is a walk-forward fold. Points on the diagonal generalize perfectly. Points well below the diagonal indicate IS performance doesn't translate to OOS — a sign of overfitting.</div>
                <div id="wf-scatter" class="chart-tall"></div>
            </div>
            <div class="card" id="acf-card" style="display:none">
                <div class="card-header">
                    <h3>Autocorrelation Check</h3>
                </div>
                <div class="card-desc">Autocorrelation function of the return series. Bars outside the confidence bands (dashed lines) indicate serial correlation, which affects the choice of shuffle method for permutation tests.</div>
                <div id="acf-chart" class="chart-tall"></div>
            </div>
        </div>
        <div class="metrics-grid" id="wf-metrics" style="margin-top:12px"></div>
    </div>

    <!-- ROBUSTNESS CHECKS -->
    <div class="section" id="robust-section" style="display:none">
        <div class="section-header">
            <h2>Robustness Checks</h2>
            <span class="section-badge" id="robust-badge" style="background:var(--border);color:var(--text-secondary)">supplementary</span>
        </div>
        <div class="metrics-grid" id="robustness-metrics"></div>
        <div class="grid-2">
            <div class="card" id="regime-card" style="display:none">
                <div class="card-header">
                    <h3>Regime-Conditional Performance</h3>
                </div>
                <div class="card-desc">Sharpe ratio broken down by volatility regime (low / medium / high). A robust strategy maintains positive Sharpe across all regimes. Failure in any regime suggests the edge is conditional.</div>
                <div id="regime-chart" class="chart"></div>
            </div>
            <div class="card" id="alpha-card" style="display:none">
                <div class="card-header">
                    <h3>Alpha-Beta Decomposition</h3>
                </div>
                <table class="info-table" id="alpha-table"></table>
            </div>
        </div>
    </div>

</div>

<div class="footer">
    Generated by AlgoSystemV2 Overfitting Detection Engine
</div>

<script>
const D = {data_json};

// Plotly theme
const baseLayout = {{
    paper_bgcolor: '#151922',
    plot_bgcolor: '#151922',
    font: {{ color: '#8892a4', size: 11, family: 'Inter, -apple-system, sans-serif' }},
    margin: {{ t: 24, b: 56, l: 60, r: 24 }},
    xaxis: {{
        gridcolor: '#232a38',
        zerolinecolor: '#2e3648',
        linecolor: '#232a38',
        tickfont: {{ size: 11 }},
        title: {{ font: {{ size: 12, color: '#8892a4' }}, standoff: 12 }},
    }},
    yaxis: {{
        gridcolor: '#232a38',
        zerolinecolor: '#2e3648',
        linecolor: '#232a38',
        tickfont: {{ size: 11 }},
        title: {{ font: {{ size: 12, color: '#8892a4' }}, standoff: 8 }},
    }},
    hoverlabel: {{ bgcolor: '#1c2231', bordercolor: '#2e3648', font: {{ color: '#e6eaf0', size: 12 }} }},
}};
const plotCfg = {{ responsive: true, displayModeBar: false }};

// Subtitle
document.getElementById('subtitle').textContent =
    D.n_params + ' parameter combinations  ·  ' + D.n_reps + ' permutations  ·  shuffle = ' + D.shuffle_method + '  ·  best params = ' + D.best_params;

// === VERDICT BAR ===
const vb = document.getElementById('verdict-bar');
function addVerdict(label, value, color) {{
    const el = document.createElement('div');
    el.className = 'verdict-item';
    el.style.borderTopColor = color;
    el.innerHTML = '<div class="vlabel">' + label + '</div><div class="vvalue" style="color:' + color + '">' + value + '</div>';
    vb.appendChild(el);
}}

const pColor = D.unbiased_pvalue < 0.05 ? '#34d399' : D.unbiased_pvalue < 0.10 ? '#fbbf24' : '#f87171';
addVerdict('Unbiased p-value', D.unbiased_pvalue.toFixed(4), pColor);
addVerdict('Best Sharpe', D.best_sharpe.toFixed(3), '#818cf8');
addVerdict('Deflated Sharpe', D.deflated_sharpe.toFixed(3), D.deflated_sharpe > 2 ? '#34d399' : D.deflated_sharpe > 0 ? '#fbbf24' : '#f87171');
addVerdict('Plateau Score', D.plateau_score.toFixed(3), D.plateau_score > 0.2 ? '#34d399' : D.plateau_score > 0.05 ? '#fbbf24' : '#f87171');
addVerdict('Prob Overfit', (D.prob_overfit * 100).toFixed(1) + '%', D.prob_overfit < 0.3 ? '#34d399' : D.prob_overfit < 0.5 ? '#fbbf24' : '#f87171');
if (D.pbo !== undefined) addVerdict('PBO', D.pbo.toFixed(4), D.pbo < 0.3 ? '#34d399' : D.pbo < 0.5 ? '#fbbf24' : '#f87171');
if (D.wfe !== undefined) addVerdict('WFE', D.wfe.toFixed(3), D.wfe > 0.5 ? '#34d399' : D.wfe > 0.3 ? '#fbbf24' : '#f87171');
if (D.adsr !== undefined) addVerdict('Analytical DSR', D.adsr.toFixed(4), D.adsr > 0.95 ? '#34d399' : D.adsr > 0.5 ? '#fbbf24' : '#f87171');
if (D.ci_lower !== undefined) addVerdict('Sharpe 95% CI', '[' + D.ci_lower.toFixed(2) + ', ' + D.ci_upper.toFixed(2) + ']', D.ci_includes_zero ? '#f87171' : '#34d399');

// Core badge color
const corePass = D.unbiased_pvalue < 0.05 && D.deflated_sharpe > 0;
const coreBadge = document.getElementById('core-badge');
if (corePass) {{
    coreBadge.textContent = 'signal detected';
    coreBadge.style.background = 'rgba(52,211,153,0.12)';
    coreBadge.style.color = '#34d399';
}} else {{
    coreBadge.textContent = D.unbiased_pvalue < 0.10 ? 'marginal' : 'no signal';
    coreBadge.style.background = D.unbiased_pvalue < 0.10 ? 'rgba(251,191,36,0.12)' : 'rgba(248,113,113,0.12)';
    coreBadge.style.color = D.unbiased_pvalue < 0.10 ? '#fbbf24' : '#f87171';
}}

// === CORE STATS TABLES ===
function addRow(tableId, label, value, cls) {{
    const tbl = document.getElementById(tableId);
    const tr = document.createElement('tr');
    tr.innerHTML = '<td>' + label + '</td><td class="' + (cls || '') + '">' + value + '</td>';
    tbl.appendChild(tr);
}}

// Table 1: Detection results
addRow('core-table-1', 'Best Sharpe (S*)', D.best_sharpe.toFixed(4), 'blue');
addRow('core-table-1', 'Deflated Sharpe', D.deflated_sharpe.toFixed(4), D.deflated_sharpe > 0 ? 'green' : 'red');
addRow('core-table-1', 'Unbiased p-value', D.unbiased_pvalue.toFixed(6), D.unbiased_pvalue < 0.05 ? 'green' : 'red');
addRow('core-table-1', 'Prob(Overfit)', (D.prob_overfit * 100).toFixed(2) + '%', D.prob_overfit < 0.3 ? 'green' : 'red');
addRow('core-table-1', 'Best Parameters', D.best_params);

// Table 2: Surface analysis
addRow('core-table-2', 'Plateau Score', D.plateau_score.toFixed(4), D.plateau_score > 0.2 ? 'green' : 'amber');
addRow('core-table-2', 'Robustness Ratio', D.robustness_ratio.toFixed(4));
addRow('core-table-2', 'Fraction Positive', (D.frac_positive * 100).toFixed(1) + '%');
addRow('core-table-2', 'Parameter Sets', D.n_params.toLocaleString());
addRow('core-table-2', 'Permutations', D.n_reps.toLocaleString());

// Table 3: Advanced metrics
addRow('core-table-3', 'Shuffle Method', D.shuffle_method);
if (D.adsr !== undefined) {{
    addRow('core-table-3', 'Analytical DSR', D.adsr.toFixed(6), D.adsr > 0.95 ? 'green' : 'amber');
    addRow('core-table-3', 'SR0 (Haircut)', D.sr0.toFixed(6));
    addRow('core-table-3', 'Min Track Record', Math.round(D.min_trl) + ' days');
}}
if (D.ci_lower !== undefined) {{
    addRow('core-table-3', 'Sharpe 95% CI', '[' + D.ci_lower.toFixed(3) + ', ' + D.ci_upper.toFixed(3) + ']', D.ci_includes_zero ? 'red' : 'green');
}}
if (D.pbo !== undefined) {{
    addRow('core-table-3', 'PBO', D.pbo.toFixed(6), D.pbo < 0.3 ? 'green' : 'red');
}}

// === 1. NULL DISTRIBUTION ===
Plotly.newPlot('null-dist', [{{
    x: D.null_sharpes,
    type: 'histogram',
    nbinsx: 50,
    marker: {{ color: 'rgba(129,140,248,0.55)', line: {{ color: 'rgba(129,140,248,0.8)', width: 0.5 }} }},
    name: 'Null distribution (permuted)',
    hovertemplate: 'Sharpe: %{{x:.3f}}<br>Count: %{{y}}<extra></extra>',
}}], {{
    ...baseLayout,
    shapes: [{{
        type: 'line', x0: D.best_sharpe, x1: D.best_sharpe, y0: 0, y1: 1, yref: 'paper',
        line: {{ color: '#f87171', width: 2.5, dash: 'dash' }}
    }}],
    annotations: [{{
        x: D.best_sharpe, y: 1.02, yref: 'paper',
        text: 'S* = ' + D.best_sharpe.toFixed(3),
        showarrow: false,
        font: {{ color: '#f87171', size: 12, family: 'Inter, sans-serif' }},
        yanchor: 'bottom'
    }}],
    xaxis: {{ ...baseLayout.xaxis, title: {{ text: 'Best Sharpe Ratio (permuted data)', standoff: 12 }} }},
    yaxis: {{ ...baseLayout.yaxis, title: {{ text: 'Frequency', standoff: 8 }} }},
}}, plotCfg);

// === 2. HEATMAP ===
if (D.heatmap) {{
    Plotly.newPlot('heatmap', [{{
        z: D.heatmap.z, x: D.heatmap.x, y: D.heatmap.y,
        type: 'heatmap',
        colorscale: [
            [0, '#991b1b'], [0.25, '#dc2626'], [0.4, '#f59e0b'],
            [0.5, '#1c2231'], [0.6, '#059669'], [0.75, '#10b981'], [1, '#065f46']
        ],
        zmid: 0,
        colorbar: {{ title: {{ text: 'Sharpe', font: {{ size: 11 }} }}, tickfont: {{ size: 10 }}, len: 0.85 }},
        hovertemplate: D.heatmap.xlabel + ': %{{x}}<br>' + D.heatmap.ylabel + ': %{{y}}<br>Sharpe: %{{z:.4f}}<extra></extra>',
    }}], {{
        ...baseLayout,
        xaxis: {{ ...baseLayout.xaxis, title: {{ text: D.heatmap.xlabel, standoff: 12 }} }},
        yaxis: {{ ...baseLayout.yaxis, title: {{ text: D.heatmap.ylabel, standoff: 8 }} }},
    }}, plotCfg);
}}

// === 3. P-VALUES ===
Plotly.newPlot('pvalues', [
    {{
        x: D.pvalue_ranks, y: D.solo_pvals, mode: 'markers',
        marker: {{ color: 'rgba(129,140,248,0.8)', size: 8, line: {{ color: '#818cf8', width: 1 }} }},
        name: 'Solo p-value',
        hovertemplate: 'Rank %{{x}}<br>Solo: %{{y:.4f}}<extra></extra>',
    }},
    {{
        x: D.pvalue_ranks, y: D.unbiased_pvals, mode: 'markers',
        marker: {{ color: 'rgba(248,113,113,0.8)', size: 8, symbol: 'diamond', line: {{ color: '#f87171', width: 1 }} }},
        name: 'Unbiased p-value',
        hovertemplate: 'Rank %{{x}}<br>Unbiased: %{{y:.4f}}<extra></extra>',
    }},
], {{
    ...baseLayout,
    xaxis: {{ ...baseLayout.xaxis, title: {{ text: 'Parameter Rank (by Sharpe)', standoff: 12 }} }},
    yaxis: {{ ...baseLayout.yaxis, title: {{ text: 'P-Value', standoff: 8 }}, range: [-0.03, 1.06] }},
    shapes: [{{
        type: 'line', x0: 0, x1: D.pvalue_ranks.length + 1, y0: 0.05, y1: 0.05,
        line: {{ color: '#34d399', width: 1, dash: 'dash' }}
    }}],
    annotations: [{{
        x: D.pvalue_ranks.length, y: 0.05, text: 'alpha = 0.05',
        showarrow: false, yanchor: 'bottom', yshift: 4,
        font: {{ color: '#34d399', size: 10 }}
    }}],
    showlegend: true,
    legend: {{ x: 0.01, y: 0.98, bgcolor: 'rgba(0,0,0,0)', font: {{ size: 11 }} }},
}}, plotCfg);

// === 4. PBO ===
if (D.pbo_logits) {{
    document.getElementById('pbo-card').style.display = '';
    const neg = D.pbo_logits.filter(v => v < 0);
    const pos = D.pbo_logits.filter(v => v >= 0);
    Plotly.newPlot('pbo-dist', [
        {{ x: neg, type: 'histogram', marker: {{ color: 'rgba(248,113,113,0.6)', line: {{ color: '#f87171', width: 0.5 }} }}, name: 'Overfit (logit < 0)' }},
        {{ x: pos, type: 'histogram', marker: {{ color: 'rgba(52,211,153,0.6)', line: {{ color: '#34d399', width: 0.5 }} }}, name: 'Genuine (logit >= 0)' }},
    ], {{
        ...baseLayout,
        barmode: 'stack',
        xaxis: {{ ...baseLayout.xaxis, title: {{ text: 'Logit(OOS Rank)', standoff: 12 }} }},
        yaxis: {{ ...baseLayout.yaxis, title: {{ text: 'Frequency', standoff: 8 }} }},
        shapes: [{{ type: 'line', x0: 0, x1: 0, y0: 0, y1: 1, yref: 'paper', line: {{ color: '#e6eaf0', width: 2 }} }}],
        showlegend: true,
        legend: {{ x: 0.01, y: 0.98, bgcolor: 'rgba(0,0,0,0)', font: {{ size: 11 }} }},
    }}, plotCfg);
}}

// === 5. WALK-FORWARD ===
if (D.wf_is) {{
    document.getElementById('wf-section').style.display = '';
    document.getElementById('wf-card').style.display = '';

    const allVals = D.wf_is.concat(D.wf_oos);
    const lo = Math.min(...allVals) - 0.8;
    const hi = Math.max(...allVals) + 0.8;

    Plotly.newPlot('wf-scatter', [
        {{
            x: D.wf_is, y: D.wf_oos,
            mode: 'markers+text',
            text: D.wf_is.map((_, i) => 'F' + (i + 1)),
            textposition: 'top right',
            textfont: {{ size: 10, color: '#8892a4' }},
            marker: {{ color: '#818cf8', size: 12, line: {{ color: '#e6eaf0', width: 1.5 }}, opacity: 0.9 }},
            name: 'Folds',
            hovertemplate: 'Fold %{{text}}<br>IS Sharpe: %{{x:.3f}}<br>OOS Sharpe: %{{y:.3f}}<extra></extra>',
        }},
        {{
            x: [lo, hi], y: [lo, hi], mode: 'lines',
            line: {{ color: '#5c6578', dash: 'dash', width: 1.5 }},
            name: 'Perfect (IS = OOS)',
            hoverinfo: 'skip',
        }},
        {{
            x: [lo, hi], y: [lo * 0.5, hi * 0.5], mode: 'lines',
            line: {{ color: '#f87171', dash: 'dash', width: 1 }},
            name: 'WFE = 0.5',
            hoverinfo: 'skip',
        }},
    ], {{
        ...baseLayout,
        margin: {{ t: 24, b: 60, l: 64, r: 24 }},
        xaxis: {{ ...baseLayout.xaxis, title: {{ text: 'In-Sample Sharpe Ratio', standoff: 14 }}, range: [lo, hi] }},
        yaxis: {{ ...baseLayout.yaxis, title: {{ text: 'Out-of-Sample Sharpe Ratio', standoff: 10 }}, range: [lo, hi] }},
        showlegend: true,
        legend: {{ x: 0.02, y: 0.98, bgcolor: 'rgba(0,0,0,0)', font: {{ size: 11 }} }},
    }}, plotCfg);

    // WF metrics
    const wm = document.getElementById('wf-metrics');
    function addWfMetric(label, value, cls) {{
        wm.innerHTML += '<div class="metric-tile"><div class="mlabel">' + label + '</div><div class="mvalue ' + cls + '">' + value + '</div></div>';
    }}
    addWfMetric('Walk-Forward Efficiency', D.wfe.toFixed(3), D.wfe > 0.5 ? 'green' : D.wfe > 0.3 ? 'amber' : 'red');
    addWfMetric('Folds', D.wf_is.length);
    addWfMetric('Vetoed', D.wf_vetoed ? 'YES' : 'NO', D.wf_vetoed ? 'red' : 'green');
    const meanIS = D.wf_is.reduce((a, b) => a + b, 0) / D.wf_is.length;
    const meanOOS = D.wf_oos.reduce((a, b) => a + b, 0) / D.wf_oos.length;
    addWfMetric('Mean IS Sharpe', meanIS.toFixed(3), 'blue');
    addWfMetric('Mean OOS Sharpe', meanOOS.toFixed(3), meanOOS > 0 ? 'green' : 'red');
    addWfMetric('Degradation', ((1 - meanOOS / meanIS) * 100).toFixed(1) + '%', (1 - meanOOS / meanIS) < 0.4 ? 'green' : 'amber');
}}

// === 6. ACF ===
if (D.acf_values) {{
    document.getElementById('acf-card').style.display = '';
    const lags = D.acf_values.map((_, i) => i + 1);
    const n = D.n_reps || 1000;
    const thr = 2 / Math.sqrt(n);
    const colors = D.acf_values.map(v => Math.abs(v) > thr ? '#f87171' : '#818cf8');

    Plotly.newPlot('acf-chart', [{{
        x: lags, y: D.acf_values, type: 'bar',
        marker: {{ color: colors, line: {{ color: colors.map(c => c === '#f87171' ? '#fca5a5' : '#a5b4fc'), width: 0.5 }} }},
        hovertemplate: 'Lag %{{x}}<br>ACF: %{{y:.4f}}<extra></extra>',
    }}], {{
        ...baseLayout,
        margin: {{ t: 24, b: 60, l: 64, r: 24 }},
        xaxis: {{ ...baseLayout.xaxis, title: {{ text: 'Lag', standoff: 14 }}, dtick: 1 }},
        yaxis: {{ ...baseLayout.yaxis, title: {{ text: 'Autocorrelation (ACF)', standoff: 10 }} }},
        shapes: [
            {{ type: 'line', x0: 0, x1: lags.length + 1, y0: thr, y1: thr, line: {{ color: '#5b8af5', dash: 'dash', width: 1 }} }},
            {{ type: 'line', x0: 0, x1: lags.length + 1, y0: -thr, y1: -thr, line: {{ color: '#5b8af5', dash: 'dash', width: 1 }} }},
        ],
        annotations: [
            {{ x: lags.length, y: thr, text: '95% CI', showarrow: false, yshift: 10, font: {{ color: '#5b8af5', size: 10 }} }},
        ],
    }}, plotCfg);

    // ACF metrics within wf-metrics
    const wm = document.getElementById('wf-metrics');
    if (wm) {{
        wm.innerHTML += '<div class="metric-tile"><div class="mlabel">Has Autocorrelation</div><div class="mvalue ' + (D.acf_has_ac ? 'amber' : 'green') + '">' + (D.acf_has_ac ? 'YES' : 'NO') + '</div></div>';
        wm.innerHTML += '<div class="metric-tile"><div class="mlabel">Recommended Shuffle</div><div class="mvalue blue">' + D.acf_recommended + '</div></div>';
        wm.innerHTML += '<div class="metric-tile"><div class="mlabel">Ljung-Box p-value</div><div class="mvalue">' + D.acf_lb_pvalue.toFixed(4) + '</div></div>';
    }}
}}

// WF badge
if (D.wfe !== undefined) {{
    const wb = document.getElementById('wf-badge');
    if (D.wfe > 0.5) {{
        wb.textContent = 'generalizes'; wb.style.background = 'rgba(52,211,153,0.12)'; wb.style.color = '#34d399';
    }} else if (D.wfe > 0.3) {{
        wb.textContent = 'marginal'; wb.style.background = 'rgba(251,191,36,0.12)'; wb.style.color = '#fbbf24';
    }} else {{
        wb.textContent = 'overfitting'; wb.style.background = 'rgba(248,113,113,0.12)'; wb.style.color = '#f87171';
    }}
}}

// === 7. ROBUSTNESS METRICS ===
const rm = document.getElementById('robustness-metrics');
let hasRobust = false;
function addRobustMetric(label, value, cls, detail) {{
    hasRobust = true;
    rm.innerHTML += '<div class="metric-tile"><div class="mlabel">' + label + '</div><div class="mvalue ' + (cls || '') + '">' + value + '</div>' + (detail ? '<div class="mdetail">' + detail + '</div>' : '') + '</div>';
}}

if (D.kelly_fraction !== undefined) {{
    addRobustMetric('Kelly Fraction', (D.kelly_fraction * 100).toFixed(1) + '%', D.kelly_has_edge ? 'green' : 'red', 'Optimal bet size');
    addRobustMetric('Win Rate', (D.kelly_win_rate * 100).toFixed(1) + '%', D.kelly_win_rate > 0.4 ? 'green' : 'amber', 'Fraction of positive days');
    addRobustMetric('Edge (EV/$)', D.kelly_edge.toFixed(6), D.kelly_edge > 0 ? 'green' : 'red', 'Expected value per dollar');
    addRobustMetric('Has Edge', D.kelly_has_edge ? 'YES' : 'NO', D.kelly_has_edge ? 'green' : 'red', 'Kelly > 0 and profitable');
}}
if (D.alpha_annual !== undefined) {{
    document.getElementById('alpha-card').style.display = '';
    addRow('alpha-table', 'Annual Alpha', (D.alpha_annual * 100).toFixed(2) + '%', D.is_just_beta ? 'red' : 'green');
    addRow('alpha-table', 'Beta', D.beta.toFixed(4));
    addRow('alpha-table', 'R-squared', D.r_squared.toFixed(4));
    addRow('alpha-table', 'Is Just Beta?', D.is_just_beta ? 'YES' : 'NO', D.is_just_beta ? 'red' : 'green');

    addRobustMetric('Annual Alpha', (D.alpha_annual * 100).toFixed(2) + '%', D.is_just_beta ? 'red' : 'green', 'Excess return vs benchmark');
    addRobustMetric('Beta', D.beta.toFixed(3), '', 'Market sensitivity');
    addRobustMetric('R-squared', D.r_squared.toFixed(3), '', 'Variance explained by market');
}}
if (D.regime_all !== undefined) {{
    addRobustMetric('All Regimes Pass', D.regime_all ? 'YES' : 'NO', D.regime_all ? 'green' : 'red', 'Positive Sharpe in all vol regimes');
}}
if (D.min_trl !== undefined) {{
    addRobustMetric('Min Track Record', Math.round(D.min_trl) + ' days', '', 'Days needed to confirm skill');
}}
if (D.sr0 !== undefined) {{
    addRobustMetric('SR0 (Haircut)', D.sr0.toFixed(4), '', 'Multiple-testing adjusted baseline');
}}

if (hasRobust) {{
    document.getElementById('robust-section').style.display = '';
    const rb = document.getElementById('robust-badge');
    rb.textContent = 'verified';
    rb.style.background = 'rgba(91,138,245,0.12)';
    rb.style.color = '#5b8af5';
}}

// === 8. REGIME CHART ===
if (D.regime_names) {{
    document.getElementById('regime-card').style.display = '';
    const rColors = D.regime_sharpes.map(v => v > 0 ? '#34d399' : '#f87171');
    Plotly.newPlot('regime-chart', [{{
        x: D.regime_names, y: D.regime_sharpes, type: 'bar',
        marker: {{
            color: rColors.map(c => c + '99'),
            line: {{ color: rColors, width: 1.5 }},
        }},
        hovertemplate: '%{{x}}<br>Sharpe: %{{y:.3f}}<extra></extra>',
    }}], {{
        ...baseLayout,
        xaxis: {{ ...baseLayout.xaxis, title: {{ text: 'Volatility Regime', standoff: 12 }} }},
        yaxis: {{ ...baseLayout.yaxis, title: {{ text: 'Sharpe Ratio', standoff: 8 }} }},
        shapes: [{{
            type: 'line', x0: -0.5, x1: D.regime_names.length - 0.5, y0: 0, y1: 0,
            line: {{ color: '#5c6578', width: 1 }}
        }}],
    }}, plotCfg);
}}
</script>
</body>
</html>'''
